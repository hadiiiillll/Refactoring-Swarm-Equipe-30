"""
Graphe d'exécution LangGraph - Version avec passage correct au fichier suivant
"""
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from pathlib import Path
import time
import json

from src.agents.auditor_agent import AuditorAgent
from src.agents.fixateur_agent import FixateurAgent
from src.agents.testeur_agent import AgentTesteur
from src.utils.logger import log_experiment, ActionType


class RefactoringState(TypedDict):
    """État du système."""
    target_dir: str
    current_file: str
    file_list: List[str]
    current_index: int
    iteration_count: int
    max_iterations: int
    stats: Dict[str, Any]
    test_passed: bool


class Orchestrator:
    """Orchestrateur avec détection correcte du verdict OK."""
    
    def __init__(self, max_iterations: int = 5, delay_between_files: int = 10):
        self.max_iterations = max_iterations
        self.delay_between_files = delay_between_files
        
        # Initialiser les agents
        self.auditor = AuditorAgent()
        self.fixateur = FixateurAgent()
        self.testeur = AgentTesteur()
        
        # Construire le graphe
        self.graph = self._build_graph()
        
        print("✓ Orchestrateur LangGraph initialisé")
    
    def _build_graph(self):
        """Construit le graphe d'exécution."""
        workflow = StateGraph(RefactoringState)
        
        # Ajouter les nœuds
        workflow.add_node("initialize", self._initialize)
        workflow.add_node("get_next_file", self._get_next_file)
        workflow.add_node("audit", self._audit)
        workflow.add_node("fix", self._fix)
        workflow.add_node("test", self._test)
        workflow.add_node("check_result", self._check_result)
        workflow.add_node("finalize", self._finalize)
        
        # Définir le flux
        workflow.set_entry_point("initialize")
        workflow.add_edge("initialize", "get_next_file")
        workflow.add_edge("get_next_file", "audit")
        workflow.add_edge("audit", "fix")
        workflow.add_edge("fix", "test")
        workflow.add_edge("test", "check_result")
        
        # Décisions basées sur le résultat
        workflow.add_conditional_edges(
            "check_result",
            self._decide_next,
            {
                "NEXT_FILE": "get_next_file",  # Nouveau fichier
                "RETRY": "fix",                  # Même fichier
                "DONE": "finalize"               # Fin
            }
        )
        
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    def _initialize(self, state: RefactoringState) -> RefactoringState:
        """Initialise le système."""
        print(f"\n{'='*70}")
        print("🚀 INITIALISATION")
        print(f"{'='*70}")
        
        target_path = Path(state["target_dir"])
        python_files = list(target_path.glob("*.py"))
        file_list = [str(f) for f in python_files]
        
        print(f"📁 {len(file_list)} fichier(s) trouvé(s)")
        
        stats = {
            "total": len(file_list),
            "processed": 0,
            "success": 0,
            "failed": 0,
            "total_iterations": 0
        }
        
        return {
            "target_dir": state["target_dir"],
            "current_file": "",
            "file_list": file_list,
            "current_index": 0,
            "iteration_count": 1,
            "max_iterations": self.max_iterations,
            "stats": stats,
            "test_passed": False
        }
    
    def _get_next_file(self, state: RefactoringState) -> RefactoringState:
        """Récupère le prochain fichier à traiter."""
        current_index = state["current_index"]
        file_list = state["file_list"]
        
        if current_index >= len(file_list):
            return state
        
        current_file = file_list[current_index]
        
        print(f"\n{'='*70}")
        print(f"📁 FICHIER [{current_index + 1}/{len(file_list)}]: {Path(current_file).name}")
        print(f"{'='*70}")
        
        return {
            **state,
            "current_file": current_file,
            "iteration_count": 1,
            "test_passed": False
        }
    
    def _audit(self, state: RefactoringState) -> RefactoringState:
        """Exécute l'audit sur le fichier courant."""
        current_file = state["current_file"]
        iteration = state["iteration_count"]
        
        print(f"\n📋 PHASE 1: AUDIT (Tentative {iteration}/{state['max_iterations']})")
        print("-" * 70)
        
        try:
            audit_report = self.auditor.audit(current_file)
            
            # Sauvegarder le rapport
            reports_dir = Path("audit_reports")
            reports_dir.mkdir(exist_ok=True)
            
            report_file = reports_dir / f"{Path(current_file).stem}_audit.txt"
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(audit_report)
            
            print(f"✓ Audit terminé - rapport sauvegardé: {report_file.name}")
            
            return state
            
        except Exception as e:
            print(f"✗ Erreur audit: {e}")
            return state
    
    def _fix(self, state: RefactoringState) -> RefactoringState:
        """Exécute la correction."""
        current_file = state["current_file"]
        iteration = state["iteration_count"]
        
        if iteration == 1:
            print(f"\n🔧 PHASE 2: CORRECTION INITIALE")
        else:
            print(f"\n🔧 PHASE 2: RE-CORRECTION (Tentative {iteration})")
        print("-" * 70)
        
        try:
            result = self.fixateur.fix(current_file)
            
            if result.get("status") == "success":
                print(f"✓ Correction appliquée")
            else:
                print(f"✗ Correction échouée")
            
            return state
            
        except Exception as e:
            print(f"✗ Erreur correction: {e}")
            return state
    
    def _test(self, state: RefactoringState) -> RefactoringState:
        """Exécute le test avec détection du verdict OK."""
        current_file = state["current_file"]
        iteration = state["iteration_count"]
        
        print(f"\n🧪 PHASE 3: TEST")
        print("-" * 70)
        
        try:
            # Exécuter le test
            test_result = self.testeur.run_full_test_cycle(current_file)
            
            # Récupérer le verdict
            verdict = test_result.get("verdict", "")
            test_passed = False
            
            # Détection du verdict OK
            if verdict and "OK" in verdict:
                test_passed = True
                print(f"  ✅ Verdict OK détecté: {verdict}")
            
            # Afficher le résultat
            if test_passed:
                print(f"  ✅ Test réussi à l'itération {iteration}")
            else:
                print(f"  ❌ Test échoué à l'itération {iteration} (verdict: {verdict})")
            
            return {
                **state,
                "test_passed": test_passed
            }
            
        except Exception as e:
            print(f"✗ Erreur test: {e}")
            return {
                **state,
                "test_passed": False
            }
    
    def _check_result(self, state: RefactoringState) -> RefactoringState:
        """Vérifie le résultat et met à jour les stats."""
        
        if state["test_passed"]:
            # Mettre à jour les stats pour un succès
            stats = state["stats"].copy()
            stats["processed"] += 1
            stats["success"] += 1
            stats["total_iterations"] += state["iteration_count"]
            print(f"\n✅ Succès enregistré après {state['iteration_count']} tentative(s)")
            
            return {
                **state,
                "stats": stats,
                "test_passed": True  # Garder pour la décision
            }
        else:
            # Incrémenter le compteur d'itérations pour le même fichier
            next_iteration = state["iteration_count"] + 1
            print(f"\n❌ Échec, prochaine tentative: {next_iteration}")
            
            # Vérifier si on a dépassé le max d'itérations
            if next_iteration > state["max_iterations"]:
                print(f"\n❌ Maximum d'itérations atteint pour ce fichier")
                stats = state["stats"].copy()
                stats["processed"] += 1
                stats["failed"] += 1
                stats["total_iterations"] += state["max_iterations"]
                
                return {
                    **state,
                    "stats": stats,
                    "test_passed": False,
                    "iteration_count": next_iteration
                }
            
            return {
                **state,
                "iteration_count": next_iteration,
                "test_passed": False
            }
    
    def _decide_next(self, state: RefactoringState) -> str:
        """Décide de la prochaine action."""
        
        # Si le test a réussi
        if state["test_passed"]:
            # Incrémenter l'index pour passer au fichier suivant
            next_index = state["current_index"] + 1
            
            # Vérifier s'il reste des fichiers
            if next_index >= len(state["file_list"]):
                print(f"\n📌 Plus de fichiers à traiter")
                return "DONE"
            else:
                # Mettre à jour l'index dans l'état
                print(f"\n⏳ Passage au fichier suivant après {self.delay_between_files}s...")
                time.sleep(self.delay_between_files)
                # On met à jour l'index ici
                state["current_index"] = next_index
                return "NEXT_FILE"
        
        # Si l'itération courante a échoué mais pas dépassé le max, on réessaie
        if state["iteration_count"] <= state["max_iterations"]:
            print(f"\n🔄 Nouvelle tentative sur le même fichier...")
            return "RETRY"
        
        # Sinon, échec définitif, passer au suivant
        print(f"\n❌ Échec définitif, passage au fichier suivant...")
        next_index = state["current_index"] + 1
        if next_index >= len(state["file_list"]):
            return "DONE"
        
        time.sleep(self.delay_between_files)
        state["current_index"] = next_index
        return "NEXT_FILE"
    
    def _finalize(self, state: RefactoringState) -> RefactoringState:
        """Génère le rapport final."""
        stats = state["stats"]
        
        print(f"\n{'='*70}")
        print("📊 RAPPORT FINAL")
        print(f"{'='*70}")
        print(f"Fichiers trouvés : {stats['total']}")
        print(f"Fichiers traités : {stats['processed']}")
        print(f"✅ Succès : {stats['success']}")
        print(f"❌ Échecs : {stats['failed']}")
        print(f"📈 Total itérations : {stats['total_iterations']}")
        
        if stats['processed'] > 0:
            avg = stats['total_iterations'] / stats['processed']
            print(f"📊 Moyenne itérations/fichier : {avg:.1f}")
        
        print(f"{'='*70}")
        
        # Logger le rapport final
        log_experiment(
            agent_name="Orchestrator",
            model_used="N/A",
            action=ActionType.ANALYSIS,
            details={
                "final_stats": stats,
                "input_prompt": "Génération rapport final",
                "output_response": f"Mission terminée: {stats['success']}/{stats['total']} succès"
            },
            status="SUCCESS" if stats['failed'] == 0 else "PARTIAL_SUCCESS"
        )
        
        return state
    
    def run(self, target_dir: str):
        """Exécute l'orchestrateur."""
        initial_state = {
            "target_dir": target_dir,
            "current_file": "",
            "file_list": [],
            "current_index": 0,
            "iteration_count": 1,
            "max_iterations": self.max_iterations,
            "stats": {
                "total": 0,
                "processed": 0,
                "success": 0,
                "failed": 0,
                "total_iterations": 0
            },
            "test_passed": False
        }
        
        try:
            final_state = self.graph.invoke(initial_state, {"recursion_limit": 200})
            stats = final_state["stats"]
            
            if stats["failed"] == 0:
                print(f"\n✅ MISSION COMPLÈTE: Tous les fichiers validés!")
                return 0
            else:
                print(f"\n⚠️ MISSION PARTIELLE: {stats['failed']} fichier(s) en échec")
                return 1
                
        except Exception as e:
            print(f"\n❌ ERREUR: {e}")
            log_experiment(
                agent_name="Orchestrator",
                model_used="N/A",
                action=ActionType.ANALYSIS,
                details={
                    "error": str(e),
                    "input_prompt": f"Exécution sur {target_dir}",
                    "output_response": f"Échec système: {e}"
                },
                status="FAILURE"
            )
            return 1
        