"""
Graphe d'exécution LangGraph pour orchestrer les agents Refactoring Swarm.
Version simplifiée et fonctionnelle.
"""
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
import os
from pathlib import Path
import json
from datetime import datetime

from src.agents.auditor_agent import AuditorAgent
from src.agents.fixateur_agent import FixateurAgent
from src.agents.testeur_agent import AgentTesteur
from src.utils.logger import log_experiment, ActionType


class RefactoringState(TypedDict):
    """État du système de refactoring."""
    target_dir: str
    current_file: str
    file_list: List[str]
    current_index: int
    iteration_count: int
    audit_report: str
    fix_result: Dict[str, Any]
    test_result: Dict[str, Any]
    validation_status: str
    max_iterations: int
    stats: Dict[str, Any]


class Orchestrator:
    """Orchestrateur principal utilisant LangGraph."""
    
    def __init__(self, max_iterations: int = 5, delay_between_files: int = 10):
        """
        Initialise l'orchestrateur avec le graphe d'exécution.
        
        Args:
            max_iterations: Nombre maximum d'itérations de self-healing par fichier
            delay_between_files: Délai entre les fichiers (secondes)
        """
        self.max_iterations = max_iterations
        self.delay_between_files = delay_between_files
        
        # Initialiser les agents
        self.auditor = AuditorAgent()
        self.fixateur = FixateurAgent()
        self.testeur = AgentTesteur()
        
        # Construire le graphe (SANS checkpointer)
        self.graph = self._build_graph()
        
        print("✓ Orchestrateur LangGraph initialisé")
    
    def _build_graph(self):
        """Construit le graphe d'exécution LangGraph."""
        
        # Créer le graphe
        workflow = StateGraph(RefactoringState)
        
        # Ajouter les nœuds (étapes)
        workflow.add_node("initialize", self._initialize_system)
        workflow.add_node("get_next_file", self._get_next_file)
        workflow.add_node("audit_file", self._audit_file)
        workflow.add_node("fix_file", self._fix_file)
        workflow.add_node("test_file", self._test_file)
        workflow.add_node("validate_test", self._validate_test)
        workflow.add_node("handle_self_healing", self._handle_self_healing)
        workflow.add_node("update_stats", self._update_stats)
        workflow.add_node("final_report", self._final_report)
        
        # Définir le point d'entrée
        workflow.set_entry_point("initialize")
        
        # Ajouter les transitions
        workflow.add_edge("initialize", "get_next_file")
        
        # Transition conditionnelle pour les fichiers
        workflow.add_conditional_edges(
            "get_next_file",
            self._should_process_next_file,
            {
                "CONTINUE": "audit_file",
                "COMPLETE": "final_report"
            }
        )
        
        # Chaînage normal
        workflow.add_edge("audit_file", "fix_file")
        workflow.add_edge("fix_file", "test_file")
        workflow.add_edge("test_file", "validate_test")
        
        # Transition conditionnelle après test
        workflow.add_conditional_edges(
            "validate_test",
            self._should_self_heal,
            {
                "SUCCESS": "update_stats",
                "NEEDS_FIX": "handle_self_healing",
                "FAILURE": "update_stats"
            }
        )
        
        # Transition conditionnelle pour self-healing
        workflow.add_conditional_edges(
            "handle_self_healing",
            self._check_self_healing_status,
            {
                "RETRY_FIX": "fix_file",
                "MAX_ITERATIONS": "update_stats"
            }
        )
        
        workflow.add_edge("update_stats", "get_next_file")
        
        # Compiler SANS checkpointer
        return workflow.compile()
    
    # ====================================================================
    # MÉTHODES DES NŒUDS
    # ====================================================================
    
    def _initialize_system(self, state: RefactoringState) -> RefactoringState:
        """Initialise le système avec le dossier cible."""
        print(f"\n{'='*70}")
        print(f"INITIALISATION DU SYSTÈME")
        print(f"{'='*70}")
        
        target_dir = state["target_dir"]
        target_path = Path(target_dir)
        
        if not target_path.exists():
            raise FileNotFoundError(f"Dossier introuvable: {target_dir}")
        
        # Lister les fichiers Python
        python_files = list(target_path.glob("*.py"))
        file_list = [str(f) for f in python_files]
        
        if not file_list:
            print("Aucun fichier Python trouvé.")
        
        # Initialiser les statistiques
        stats = {
            "total_files": len(file_list),
            "processed_files": 0,
            "successful_files": 0,
            "failed_files": 0,
            "first_try_success": 0,
            "needed_self_healing": 0,
            "total_iterations": 0,
            "max_iterations_per_file": self.max_iterations
        }
        
        # Logger l'initialisation
        log_experiment(
            agent_name="Orchestrator",
            model_used="N/A",
            action=ActionType.ANALYSIS,
            details={
                "target_dir": target_dir,
                "files_found": len(file_list),
                "max_iterations": self.max_iterations,
                "delay_between_files": self.delay_between_files,
                "input_prompt": f"Initialisation système pour {target_dir}",
                "output_response": f"{len(file_list)} fichiers trouvés"
            },
            status="SUCCESS"
        )
        
        return {
            "target_dir": target_dir,
            "current_file": "",
            "file_list": file_list,
            "current_index": 0,
            "iteration_count": 0,
            "audit_report": "",
            "fix_result": {},
            "test_result": {},
            "validation_status": "",
            "max_iterations": self.max_iterations,
            "stats": stats
        }
    
    def _get_next_file(self, state: RefactoringState) -> RefactoringState:
        """Récupère le prochain fichier à traiter."""
        current_index = state["current_index"]
        file_list = state["file_list"]
        
        if current_index >= len(file_list):
            return state
        
        current_file = file_list[current_index]
        
        print(f"\n{'='*70}")
        print(f"FICHIER [{current_index + 1}/{len(file_list)}]: {Path(current_file).name}")
        print(f"{'='*70}")
        
        new_state = dict(state)
        new_state["current_file"] = current_file
        new_state["iteration_count"] = 0
        return new_state
    
    def _audit_file(self, state: RefactoringState) -> RefactoringState:
        """Exécute l'agent Auditeur sur le fichier courant."""
        current_file = state["current_file"]
        
        print(f"\n📋 PHASE 1: AUDIT")
        print("-" * 70)
        
        try:
            # Exécuter l'audit
            audit_report = self.auditor.audit(current_file)
            
            # Sauvegarder le rapport
            reports_dir = Path("audit_reports")
            reports_dir.mkdir(exist_ok=True)
            
            report_file = reports_dir / f"{Path(current_file).stem}_audit.txt"
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(audit_report)
            
            print(f"✓ Audit terminé - rapport sauvegardé: {report_file}")
            
            new_state = dict(state)
            new_state["audit_report"] = audit_report
            return new_state
            
        except Exception as e:
            print(f"✗ Erreur audit: {e}")
            raise
    
    def _fix_file(self, state: RefactoringState) -> RefactoringState:
        """Exécute l'agent Correcteur sur le fichier courant."""
        current_file = state["current_file"]
        iteration = state["iteration_count"]
        
        if iteration == 0:
            print(f"\n🔧 PHASE 2: CORRECTION INITIALE")
        else:
            print(f"\n🔧 PHASE 2.{iteration}: RE-CORRECTION")
        print("-" * 70)
        
        try:
            # Exécuter la correction
            fix_result = self.fixateur.fix(current_file)
            
            if fix_result.get("status") != "success":
                print(f"✗ Correction échouée")
                raise Exception(f"Échec correction: {fix_result.get('message')}")
            
            print(f"✓ Correction appliquée")
            
            new_state = dict(state)
            new_state["fix_result"] = fix_result
            new_state["iteration_count"] = state["iteration_count"] + 1
            return new_state
            
        except Exception as e:
            print(f"✗ Erreur correction: {e}")
            raise
    
    def _test_file(self, state: RefactoringState) -> RefactoringState:
        """Exécute l'agent Testeur sur le fichier courant."""
        current_file = state["current_file"]
        
        print(f"\n🧪 PHASE 3: TEST")
        print("-" * 70)
        
        try:
            # Exécuter le test
            test_result = self.testeur.run_full_test_cycle(current_file)
            
            new_state = dict(state)
            new_state["test_result"] = test_result
            return new_state
            
        except Exception as e:
            print(f"✗ Erreur test: {e}")
            raise
    
    def _validate_test(self, state: RefactoringState) -> RefactoringState:
        """Valide le résultat du test et décide de l'action suivante."""
        test_result = state["test_result"]
        
        # Vérifier le verdict
        if test_result.get("success", False):
            validation_status = "SUCCESS"
            print(f"\n✅ VERDICT: OK – exécution valide")
        else:
            validation_status = "NEEDS_FIX"
            print(f"\n⚠️ VERDICT: ERREUR BLOQUANTE – correction requise")
            
            # Mettre à jour l'audit pour le self-healing
            self._update_audit_from_test_result(state["current_file"])
        
        new_state = dict(state)
        new_state["validation_status"] = validation_status
        return new_state
    
    def _handle_self_healing(self, state: RefactoringState) -> RefactoringState:
        """Gère la logique de self-healing."""
        iteration = state["iteration_count"]
        max_iterations = self.max_iterations
        
        print(f"\n🔄 SELF-HEALING - Itération {iteration}/{max_iterations}")
        print("-" * 70)
        
        new_state = dict(state)
        
        # Vérifier si on a atteint le maximum d'itérations
        if iteration >= max_iterations:
            print(f"❌ Maximum d'itérations atteint ({max_iterations})")
            new_state["validation_status"] = "FAILURE"
        
        return new_state
    
    def _update_stats(self, state: RefactoringState) -> RefactoringState:
        """Met à jour les statistiques après traitement d'un fichier."""
        stats = dict(state["stats"])
        validation_status = state["validation_status"]
        iteration = state["iteration_count"]
        
        # Mettre à jour les statistiques
        stats["processed_files"] += 1
        stats["total_iterations"] += iteration
        
        if validation_status == "SUCCESS":
            stats["successful_files"] += 1
            if iteration <= 1:  # Première itération ou self-healing réussi
                stats["first_try_success"] += 1
            else:
                stats["needed_self_healing"] += 1
        elif validation_status == "FAILURE":
            stats["failed_files"] += 1
        
        # Mettre à jour l'index pour le prochain fichier
        current_index = state["current_index"] + 1
        
        # Logger les statistiques
        log_experiment(
            agent_name="Orchestrator",
            model_used="N/A",
            action=ActionType.ANALYSIS,
            details={
                "file_processed": state.get("current_file", ""),
                "validation_status": validation_status,
                "iterations_needed": iteration,
                "current_stats": stats,
                "input_prompt": f"Traitement de {Path(state.get('current_file', '')).name}",
                "output_response": f"Statut: {validation_status}, Itérations: {iteration}"
            },
            status="SUCCESS" if validation_status == "SUCCESS" else "PARTIAL_SUCCESS"
        )
        
        new_state = dict(state)
        new_state["stats"] = stats
        new_state["current_index"] = current_index
        return new_state
    
    def _final_report(self, state: RefactoringState) -> RefactoringState:
        """Génère le rapport final."""
        stats = state["stats"]
        
        print(f"\n{'='*70}")
        print(f"📊 RAPPORT FINAL")
        print(f"{'='*70}")
        print(f"Fichiers trouvés : {stats['total_files']}")
        print(f"Fichiers traités : {stats['processed_files']}")
        print(f"✅ Succès : {stats['successful_files']}")
        print(f"❌ Échecs : {stats['failed_files']}")
        print(f"⚡ Réussis du premier coup : {stats['first_try_success']}")
        print(f"🔄 Nécessitant self-healing : {stats['needed_self_healing']}")
        print(f"📈 Total itérations : {stats['total_iterations']}")
        
        if stats['processed_files'] > 0:
            avg_iterations = stats['total_iterations'] / stats['processed_files']
            print(f"📊 Moyenne itérations/fichier : {avg_iterations:.1f}")
        
        print(f"{'='*70}")
        
        # Logger le rapport final
        log_experiment(
            agent_name="Orchestrator",
            model_used="N/A",
            action=ActionType.ANALYSIS,
            details={
                "final_stats": stats,
                "input_prompt": "Génération rapport final",
                "output_response": f"Mission terminée: {stats['successful_files']}/{stats['total_files']} succès"
            },
            status="SUCCESS" if stats['failed_files'] == 0 else "PARTIAL_SUCCESS"
        )
        
        return state
    
    # ====================================================================
    # FONCTIONS DE DÉCISION (CONDITIONNEL)
    # ====================================================================
    
    def _should_process_next_file(self, state: RefactoringState) -> str:
        """Décide s'il faut traiter un autre fichier."""
        current_index = state["current_index"]
        file_list = state["file_list"]
        
        if current_index < len(file_list):
            return "CONTINUE"
        else:
            return "COMPLETE"
    
    def _should_self_heal(self, state: RefactoringState) -> str:
        """Décide si le self-healing est nécessaire."""
        validation_status = state["validation_status"]
        
        if validation_status == "SUCCESS":
            return "SUCCESS"
        elif validation_status == "NEEDS_FIX":
            return "NEEDS_FIX"
        else:
            return "FAILURE"
    
    def _check_self_healing_status(self, state: RefactoringState) -> str:
        """Décide de l'action suivante dans le self-healing."""
        iteration = state["iteration_count"]
        max_iterations = self.max_iterations
        
        if iteration >= max_iterations:
            return "MAX_ITERATIONS"
        else:
            return "RETRY_FIX"
    
    def _update_audit_from_test_result(self, code_file: str):
        """Met à jour le rapport d'audit depuis les résultats du test."""
        try:
            if Path("log_erreurs.json").exists():
                with open("log_erreurs.json", "r", encoding="utf-8") as f:
                    error_log = json.load(f)
                
                audit_dir = Path("audit_reports")
                audit_dir.mkdir(exist_ok=True)
                
                audit_file = audit_dir / f"{Path(code_file).stem}_audit.txt"
                verdict = error_log.get('verdict', 'ERREUR BLOQUANTE – correction requise')
                
                audit_content = f"""RAPPORT D'AUDIT MIS À JOUR PAR LE TESTEUR
Fichier: {code_file}
Date: {error_log.get('timestamp', datetime.now().isoformat())}
Agent: Testeur

VERDICT: {verdict}

ERREURS BLOQUANTES:
"""
                blocking_errors = error_log.get('blocking_errors', [])
                
                if blocking_errors:
                    for i, error in enumerate(blocking_errors, 1):
                        audit_content += f"""
Erreur #{i}:
  Ligne: {error.get('line', 'N/A')}
  Type: {error.get('type', 'Unknown')}
  Description: {error.get('description', '')}
  Suggestion: {error.get('suggestion', '')}
"""
                else:
                    audit_content += "\nAucune erreur bloquante.\n"
                
                with open(audit_file, "w", encoding="utf-8") as f:
                    f.write(audit_content)
                
                print(f"  ✓ Rapport d'audit mis à jour: {audit_file}")
                
        except Exception as e:
            print(f"  ⚠️ Erreur mise à jour audit: {e}")
    
    # ====================================================================
    # MÉTHODES PUBLIQUES
    # ====================================================================
    
    def run(self, target_dir: str, config: Dict[str, Any] = None):
        """
        Exécute le graphe d'exécution sur le dossier cible.
        
        Args:
            target_dir: Chemin vers le dossier contenant le code à refactorer
            config: Configuration supplémentaire (optionnel)
        """
        # État initial
        initial_state = {
            "target_dir": target_dir,
            "current_file": "",
            "file_list": [],
            "current_index": 0,
            "iteration_count": 0,
            "audit_report": "",
            "fix_result": {},
            "test_result": {},
            "validation_status": "",
            "max_iterations": self.max_iterations,
            "stats": {
                "total_files": 0,
                "processed_files": 0,
                "successful_files": 0,
                "failed_files": 0,
                "first_try_success": 0,
                "needed_self_healing": 0,
                "total_iterations": 0,
                "max_iterations_per_file": self.max_iterations
            }
        }
        
        # Exécuter le graphe
        print(f"\n🚀 DÉMARRAGE DU REFACTORING SWARM")
        print(f"📁 Dossier cible: {target_dir}")
        print(f"🔄 Max itérations par fichier: {self.max_iterations}")
        print(f"⏳ Délai entre fichiers: {self.delay_between_files}s")
        
        try:
            # Exécuter le graphe
            final_state = self.graph.invoke(initial_state)
            
            # Vérifier le résultat
            stats = final_state["stats"]
            
            if stats["failed_files"] == 0:
                print(f"\n✅ MISSION COMPLÈTE: Tous les fichiers validés!")
                return 0
            else:
                print(f"\n⚠️ MISSION PARTIELLE: {stats['failed_files']} fichier(s) en échec")
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