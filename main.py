import argparse
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

from src.agents.auditor_agent import AuditorAgent
from src.utils.logger import log_experiment, ActionType

load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="Refactoring Swarm - Analyse automatique de code Python")
    parser.add_argument("--target_dir", type=str, required=True, help="Dossier contenant les fichiers Python à analyser")
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
        except Exception as e:
            error_msg = f"Erreur lors de l'analyse de {file_path.name}: {str(e)}"
            print(error_msg)
            results[str(file_path)] = error_msg

    # Afficher les résultats
    print("\n" + "="*70)
    print("RAPPORT D'AUDIT")
    print("="*70)
    
    for file_path, plan in results.items():
        print(f"\n{'='*70}")
        print(f"Fichier : {Path(file_path).name}")
        print('='*70)
        print(plan)
        print()

    print("MISSION_COMPLETE")
    log_experiment(
        agent_name="System",
        model_used="N/A",
        action=ActionType.ANALYSIS,
        details={
            "files_analyzed": len(results),
            "input_prompt": f"Analyse complète de {len(results)} fichiers",
            "output_response": "Mission terminée avec succès"
        },
        status="SUCCESS"
    )

if __name__ == "__main__":
    main()