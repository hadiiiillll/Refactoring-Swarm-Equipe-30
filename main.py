import argparse
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from src.agents.auditor_agent import AuditorAgent
from src.agents.fixateur_agent import FixateurAgent
from src.utils.logger import log_experiment, ActionType

load_dotenv()

def main():
    parser = argparse.ArgumentParser(
        description="Refactoring Swarm - Analyse automatique de code Python"
    )
    parser.add_argument(
        "--target_dir",
        type=str,
        required=True,
        help="Dossier contenant les fichiers Python à analyser"
    )
    args = parser.parse_args()

    # Vérifier que le dossier existe
    if not os.path.exists(args.target_dir):
        print(f"Erreur: Dossier {args.target_dir} introuvable.")
        sys.exit(1)

    print(f"DEMARRAGE SUR : {args.target_dir}")
    log_experiment(
        agent_name="System",
        model_used="N/A",
        action=ActionType.ANALYSIS,
        details={
            "target_dir": args.target_dir,
            "input_prompt": f"Scan du dossier {args.target_dir}",
            "output_response": "Démarrage du système"
        },
        status="SUCCESS"
    )

    # Trouver tous les fichiers Python dans le dossier
    target_path = Path(args.target_dir)
    python_files = list(target_path.glob("*.py"))

    if not python_files:
        print(f"Aucun fichier Python trouvé dans {args.target_dir}")
        log_experiment(
            agent_name="System",
            model_used="N/A",
            action=ActionType.ANALYSIS,
            details={
                "target_dir": args.target_dir,
                "files_found": 0,
                "input_prompt": f"Recherche de fichiers Python dans {args.target_dir}",
                "output_response": "Aucun fichier trouvé"
            },
            status="FAILURE"
        )
        sys.exit(0)

    print(f"Fichiers Python trouvés : {len(python_files)}")
    log_experiment(
        agent_name="System",
        model_used="N/A",
        action=ActionType.ANALYSIS,
        details={
            "target_dir": args.target_dir,
            "files_found": len(python_files),
            "input_prompt": f"Recherche de fichiers Python dans {args.target_dir}",
            "output_response": f"{len(python_files)} fichiers trouvés"
        },
        status="SUCCESS"
    )

    # Création du dossier des rapports
    reports_dir = Path("audit_reports")
    reports_dir.mkdir(exist_ok=True)

    # Initialiser l'auditeur
    try:
        auditor = AuditorAgent()
        print(f"Auditor Agent initialisé : {auditor.model_name}")
    except Exception as e:
        print(f"Erreur lors de l'initialisation de l'Auditor : {e}")
        log_experiment(
            agent_name="System",
            model_used="N/A",
            action=ActionType.ANALYSIS,
            details={
                "input_prompt": "Initialisation de l'Auditor Agent",
                "output_response": f"Erreur: {str(e)}"
            },
            status="FAILURE"
        )
        sys.exit(1)

    # Analyser chaque fichier
    results = {}
    for file_path in python_files:
        print(f"\nAnalyse de : {file_path.name}")
        try:
            plan = auditor.audit(str(file_path))
            results[str(file_path)] = plan
            print(f"Analyse terminée : {file_path.name}")

            # Sauvegarde de l'audit (CORRIGÉ)
            report_file = reports_dir / f"{file_path.stem}_audit.txt"
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(str(plan))
        except Exception as e:
            error_msg = f"Erreur lors de l'analyse de {file_path.name}: {str(e)}"
            print(error_msg)
            results[str(file_path)] = error_msg

    # Afficher les résultats
    print("\n" + "=" * 70)
    print("RAPPORT D'AUDIT")
    print("=" * 70)

    for file_path, plan in results.items():
        print(f"\n{'=' * 70}")
        print(f"Fichier : {Path(file_path).name}")
        print('=' * 70)
        print(plan)
        print()

    # ========================================================================
    # AJOUT : PHASE CORRECTION AVEC FIXATEUR
    # ========================================================================
    print("\n" + "=" * 70)
    print("DEMARRAGE DE LA CORRECTION")
    print("=" * 70)

    # Initialiser le fixateur
    try:
        fixateur = FixateurAgent()
        print(f"Fixateur Agent initialisé : {fixateur.model_name}")
    except Exception as e:
        print(f"Erreur lors de l'initialisation du Fixateur : {e}")
        log_experiment(
            agent_name="System",
            model_used="N/A",
            action=ActionType.ANALYSIS,
            details={
                "input_prompt": "Initialisation du Fixateur Agent",
                "output_response": f"Erreur: {str(e)}"
            },
            status="FAILURE"
        )
        sys.exit(1)

    # Corriger chaque fichier
    fix_results = {}
    for file_path in python_files:
        print(f"\nCorrection de : {Path(file_path).name}")
        try:
            result = fixateur.fix(str(file_path))
            fix_results[str(file_path)] = result
            
            if result["status"] == "success":
                print(f"Correction réussie : {Path(file_path).name}")
            else:
                print(f"Correction échouée : {Path(file_path).name}")
                
        except Exception as e:
            error_msg = f"Erreur lors de la correction de {Path(file_path).name}: {str(e)}"
            print(error_msg)
            fix_results[str(file_path)] = {"status": "error", "message": error_msg}

    # Résumé final de la correction
    print("\n" + "=" * 70)
    print("RAPPORT DE CORRECTION")
    print("=" * 70)
    
    successful = sum(1 for r in fix_results.values() if r.get("status") == "success")
    failed = len(fix_results) - successful
    
    print(f"Fichiers corrigés avec succès : {successful}/{len(fix_results)}")
    print(f"Fichiers avec erreurs : {failed}/{len(fix_results)}")
    print()

    print("MISSION_COMPLETE")
    log_experiment(
        agent_name="System",
        model_used="N/A",
        action=ActionType.ANALYSIS,
        details={
            "files_analyzed": len(results),
            "files_fixed": successful,
            "files_failed": failed,
            "input_prompt": f"Analyse complète de {len(results)} fichiers",
            "output_response": "Mission terminée avec succès"
        },
        status="SUCCESS"
    )

if __name__ == "__main__":
    main()