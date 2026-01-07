from src.agents.auditor_agent import AuditorAgent
import os

def print_separator(title):
    """Affiche un séparateur visuel."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('='*70)

def test_single_file(auditor, file_path):
    """Teste l'audit d'un seul fichier."""
    if not os.path.exists(file_path):
        print(f" Fichier introuvable : {file_path}")
        return
    
    print_separator(f"Analyse de : {file_path}")
    
    result = auditor.audit(file_path)
    print(result)
    
    print("\n Analyse terminée\n")

def test_all_files(auditor):
    """Teste l'audit de tous les fichiers buggy."""
    test_files = [
        "sandbox/buggy_code.py",
        "sandbox/buggy_calculator.py",
        "sandbox/buggy_file_handler.py",
        "sandbox/buggy_string_utils.py",
        "sandbox/buggy_security.py",
    ]
    
    existing_files = [f for f in test_files if os.path.exists(f)]
    
    if not existing_files:
        print(" Aucun fichier de test trouvé dans sandbox/")
        return
    
    print(f"\n🔍 {len(existing_files)} fichier(s) à analyser\n")
    
    for file_path in existing_files:
        test_single_file(auditor, file_path)

if __name__ == "__main__":
    print_separator("AUDITOR AGENT - TESTS AVANCÉS")
    
    # Initialisation de l'auditeur
    print("\n Initialisation de l'Auditor Agent...")
    auditor = AuditorAgent()
    print(f" Modèle chargé : {auditor.model_name}\n")
    
    # Option 1 : Tester un seul fichier
    # test_single_file(auditor, "sandbox/buggy_calculator.py")
    
    # Option 2 : Tester tous les fichiers
    test_all_files(auditor)
    
    print_separator("TESTS TERMINÉS")
    print("\nVérifiez les logs dans : logs/experiment_data.json\n")