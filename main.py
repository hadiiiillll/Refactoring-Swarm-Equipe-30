import argparse
from importlib.metadata import files
import sys
import os
import time
from pathlib import Path
from dotenv import load_dotenv
import json
from datetime import datetime

from src.agents.auditor_agent import AuditorAgent
from src.agents.fixateur_agent import FixateurAgent
from src.agents.testeur_agent import AgentTesteur
from src.utils.logger import log_experiment, ActionType

load_dotenv()

# Configuration
DELAY_BETWEEN_REQUESTS = 10
MAX_ITERATIONS = 5


def create_audit_from_error_log(code_file: str):
    """Met à jour le rapport d'audit depuis log_erreurs.json."""
    try:
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
        
        if not blocking_errors:
            audit_content += "\nAucune erreur bloquante.\n"
        else:
            for i, error in enumerate(blocking_errors, 1):
                audit_content += f"""
Erreur #{i}:
  Ligne: {error.get('line', 'N/A')}
  Type: {error.get('type', 'Unknown')}
  Description: {error.get('description', '')}
  Suggestion: {error.get('suggestion', '')}
"""
        
        with open(audit_file, "w", encoding="utf-8") as f:
            f.write(audit_content)
        
        print(f"  ✓ Rapport d'audit mis à jour: {audit_file}")
        return True
        
    except Exception as e:
        print(f"  ⚠️  Erreur mise à jour audit: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Refactoring Swarm - Analyse automatique de code Python"
    )
    parser.add_argument("--target_dir", type=str, required=True)
    parser.add_argument("--delay", type=int, default=DELAY_BETWEEN_REQUESTS)
    parser.add_argument("--max-iterations", type=int, default=MAX_ITERATIONS)
    args = parser.parse_args()

    if not os.path.exists(args.target_dir):
        print(f"Erreur: Dossier {args.target_dir} introuvable.")
        sys.exit(1)

    print(f"DEMARRAGE SUR : {args.target_dir}")
    print(f"Délai entre fichiers : {args.delay} secondes")
    print(f"Itérations self-healing max : {args.max_iterations}\n")

    log_experiment(
        agent_name="System",
        model_used="N/A",
        action=ActionType.ANALYSIS,
        details={
            "target_dir": args.target_dir,
            "delay_seconds": args.delay,
            "max_iterations": args.max_iterations,
            "input_prompt": f"Scan du dossier {args.target_dir}",
            "output_response": "Démarrage du système"
        },
        status="SUCCESS"
    )

    target_path = Path(args.target_dir)
    python_files = list(target_path.glob("*.py"))

    if not python_files:
        print(f"Aucun fichier Python trouvé dans {args.target_dir}")
        sys.exit(0)

    print(f"Fichiers Python trouvés : {len(python_files)}\n")

    reports_dir = Path("audit_reports")
    reports_dir.mkdir(exist_ok=True)

    # Initialisation agents
    try:
        auditor = AuditorAgent()
        print(f"Auditor Agent initialisé : {auditor.model_name}\n")
    except Exception as e:
        print(f"Erreur initialisation Auditor : {e}")
        sys.exit(1)

    try:
        fixateur = FixateurAgent()
        print(f"Fixateur Agent initialisé : {fixateur.model_name}\n")
    except Exception as e:
        print(f"Erreur initialisation Fixateur : {e}")
        sys.exit(1)

    try:
        testeur = AgentTesteur()
        print(f"Testeur Agent initialisé : {testeur.model_name}\n")
    except Exception as e:
        print(f"Erreur initialisation Testeur : {e}")
        sys.exit(1)

    # Statistiques
    total_files = len(python_files)
    stats = {
        "total": total_files,
        "validated": 0,
        "failed": 0,
        "total_iterations": 0,
        "first_try": 0,
        "needed_selfhealing": 0
    }

    # ====================================================================
    # TRAITEMENT DE CHAQUE FICHIER
    # ====================================================================
    results = {}
    
    for index, file_path in enumerate(python_files, start=1):
        print("\n" + "=" * 70)
        print(f"FICHIER [{index}/{total_files}] : {file_path.name}")
        print("=" * 70)

        # ================================================================
        # PHASE 1: AUDIT
        # ================================================================
        print(f"\n📋 PHASE 1: AUDIT")
        print("-" * 70)
        
        try:
            plan = auditor.audit(str(file_path))
            results[str(file_path)] = plan
            print(f"✓ Audit terminé")

            report_file = reports_dir / f"{file_path.stem}_audit.txt"
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(str(plan))

        except Exception as e:
            print(f"✗ Erreur audit: {e}")
            stats["failed"] += 1
            if index < total_files:
                time.sleep(args.delay)
            continue

        # ================================================================
        # PHASE 2: CORRECTION INITIALE
        # ================================================================
        print(f"\n🔧 PHASE 2: CORRECTION")
        print("-" * 70)
        
        try:
            result = fixateur.fix(str(file_path))
            
            if result.get("status") != "success":
                print(f"✗ Correction échouée")
                stats["failed"] += 1
                if index < total_files:
                    time.sleep(args.delay)
                continue
            
            print(f"✓ Correction appliquée")

        except Exception as e:
            print(f"✗ Erreur correction: {e}")
            stats["failed"] += 1
            if index < total_files:
                time.sleep(args.delay)
            continue

        # ================================================================
        # PHASE 3: TEST INITIAL
        # ================================================================
        print(f"\n🧪 PHASE 3: TEST")
        print("-" * 70)
        
        try:
            validation = testeur.run_full_test_cycle(str(file_path))
            stats["total_iterations"] += 1
            
            # ============================================================
            # DÉCISION: SUCCESS ou SELF-HEALING ?
            # ============================================================
            
            if validation['status'] == 'SUCCESS':
                # ✅ SUCCÈS DU PREMIER COUP - PAS DE SELF-HEALING
                print(f"\n✅ OK – exécution valide (du premier coup)")
                stats["validated"] += 1
                stats["first_try"] += 1
                
                # Pas de self-healing nécessaire, passer au fichier suivant
                if index < total_files:
                    print(f"\n⏳ Attente {args.delay}s...")
                    time.sleep(args.delay)
                continue
            
            else:
                # ❌ ÉCHEC - ENTRER DANS LA BOUCLE SELF-HEALING
                print(f"\n⚠️  ERREUR BLOQUANTE détectée")
                print(f"🔄 Activation du SELF-HEALING...")
                
                stats["needed_selfhealing"] += 1
                
                # Mettre à jour le rapport d'audit
                if Path("log_erreurs.json").exists():
                    create_audit_from_error_log(str(file_path))
                
                # ========================================================
                # BOUCLE SELF-HEALING
                # ========================================================
                validated = False
                
                for iteration in range(1, args.max_iterations + 1):
                    print(f"\n{'='*70}")
                    print(f"🔄 SELF-HEALING - ITÉRATION {iteration}/{args.max_iterations}")
                    print(f"{'='*70}")
                    
                    stats["total_iterations"] += 1
                    
                    # RE-CORRECTION
                    print(f"\n🔧 RE-CORRECTION")
                    print("-" * 70)
                    
                    try:
                        fix_result = fixateur.fix(str(file_path))
                        
                        if fix_result.get("status") != "success":
                            print(f"✗ Re-correction échouée")
                            break
                        
                        print(f"✓ Re-correction appliquée")
                        
                    except Exception as e:
                        print(f"✗ Erreur re-correction: {e}")
                        break
                    
                    # RE-TEST
                    print(f"\n🧪 RE-TEST")
                    print("-" * 70)
                    
                    try:
                        validation = testeur.run_full_test_cycle(str(file_path))
                        
                        if validation['status'] == 'SUCCESS':
                            print(f"\n✅ OK – exécution valide")
                            print(f"   Self-healing réussi en {iteration + 1} itération(s) totale(s)")
                            validated = True
                            stats["validated"] += 1
                            break  # SORTIR de la boucle self-healing
                        
                        else:
                            print(f"\n⚠️  Erreurs persistent (itération {iteration})")
                            
                            # Mettre à jour l'audit pour la prochaine itération
                            if Path("log_erreurs.json").exists():
                                create_audit_from_error_log(str(file_path))
                            
                            if iteration >= args.max_iterations:
                                print(f"\n❌ Échec après {args.max_iterations} itérations")
                                break
                        
                    except Exception as e:
                        print(f"✗ Erreur test: {e}")
                        break
                
                # Si toujours pas validé après self-healing
                if not validated:
                    stats["failed"] += 1
        
        except Exception as e:
            print(f"✗ Erreur test initial: {e}")
            stats["failed"] += 1
        
        # Délai avant fichier suivant
        if index < total_files:
            print(f"\n⏳ Attente {args.delay}s...")
            time.sleep(args.delay)

    # ====================================================================
    # RAPPORT FINAL
    # ====================================================================
    print("\n" + "=" * 70)
    print("📊 RAPPORT FINAL")
    print("=" * 70)
    print(f"Fichiers traités : {stats['total']}")
    print(f"✅ Validés : {stats['validated']}")
    print(f"❌ Échecs : {stats['failed']}")
    print(f"⚡ Réussis du premier coup : {stats['first_try']}")
    print(f"🔄 Nécessitant self-healing : {stats['needed_selfhealing']}")
    print(f"📈 Total itérations : {stats['total_iterations']}")
    print(f"📊 Moyenne itérations/fichier : {stats['total_iterations']/stats['total']:.1f}")
    print("=" * 70)

    log_experiment(
        agent_name="System",
        model_used="N/A",
        action=ActionType.ANALYSIS,
        details={
            "files_analyzed": total_files,
            "files_validated": stats["validated"],
            "files_failed": stats["failed"],
            "files_first_try": stats["first_try"],
            "files_needed_selfhealing": stats["needed_selfhealing"],
            "total_iterations": stats["total_iterations"],
            "avg_iterations": stats["total_iterations"] / stats["total"],
            "input_prompt": f"Analyse complète de {total_files} fichiers",
            "output_response": "Mission terminée"
        },
        status="SUCCESS" if stats["failed"] == 0 else "PARTIAL_SUCCESS"
    )

    print("\nMISSION_COMPLETE")
    sys.exit(0 if stats["failed"] == 0 else 1)


if __name__ == "__main__":
    main()