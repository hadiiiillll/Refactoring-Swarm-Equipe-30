import subprocess
from pathlib import Path


def read_file(path: str) -> str:
    """
    Lecture sécurisée d'un fichier texte.
    """
    return Path(path).read_text(encoding="utf-8")


def run_pylint(file_path: str) -> str:
    """
    Exécute pylint sur un fichier Python et retourne le rapport texte.
    """
    result = subprocess.run(
        ["pylint", file_path, "--score=y"],
        capture_output=True,
        text=True
    )

    return result.stdout + result.stderr

# ============================================


def run_pylint_score(file_path: str) -> float:
    """
    Exécute pylint et retourne seulement le score numérique.
    
    Returns:
        float: Score entre 0.0 et 10.0
    """
    try:
        result = subprocess.run(
            ["pylint", file_path, "--score=y"],
            capture_output=True,
            text=True,
            timeout=30  # Timeout pour éviter les blocages
        )
        
        # Chercher le score dans la sortie
        # Ex: "Your code has been rated at 7.50/10"
        output = result.stdout + result.stderr
        match = re.search(r"rated at (\d+\.?\d*)/10", output)
        
        if match:
            return float(match.group(1))
        return 0.0  # Si pas trouvé
        
    except subprocess.TimeoutExpired:
        print(f"⚠️ Pylint timeout sur {Path(file_path).name}")
        return 0.0
    except Exception as e:
        print(f"⚠️ Erreur pylint sur {Path(file_path).name}: {e}")
        return 0.0


def run_pytest(test_file: str) -> dict:
    """
    Exécute pytest sur un fichier de test.
    
    Returns:
        dict: Résultats des tests
    """
    try:
        result = subprocess.run(
            ["pytest", test_file, "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=60  # Timeout plus long pour les tests
        )
        
        # Analyser la sortie
        output = result.stdout
        
        # Compter les tests passés/échoués
        passed = len(re.findall(r'PASSED|passed|✓', output))
        failed = len(re.findall(r'FAILED|failed|ERROR|✗', output))
        total = passed + failed
        
        return {
            "passed": passed,
            "failed": failed,
            "total": total,
            "success": failed == 0 and total > 0,  # Succès si 0 échec ET au moins 1 test
            "output": output[:1000]  # Limiter la taille
        }
        
    except subprocess.TimeoutExpired:
        return {
            "passed": 0,
            "failed": 1,
            "total": 1,
            "success": False,
            "output": "TIMEOUT: Tests trop longs"
        }
    except Exception as e:
        return {
            "passed": 0,
            "failed": 1,
            "total": 1,
            "success": False,
            "output": f"ERROR: {str(e)}"
        }


def create_test_if_missing(file_path: str) -> Path:
    """
    Crée un fichier de test basique si aucun n'existe.
    
    Returns:
        Path: Chemin vers le fichier de test
    """
    source = Path(file_path)
    
    # 1. Chercher d'abord un test existant
    possible_tests = [
        source.parent / f"test_{source.stem}.py",
        source.parent / f"{source.stem}_test.py",
        source.parent / "tests" / f"test_{source.stem}.py",
        source.parent / "test" / f"test_{source.stem}.py"
    ]
    
    for test_path in possible_tests:
        if test_path.exists():
            return test_path
    
    # 2. Créer un dossier tests/ si besoin
    test_dir = source.parent / "tests"
    test_dir.mkdir(exist_ok=True)
    
    # 3. Créer le fichier de test
    test_file = test_dir / f"test_{source.stem}.py"
    
    test_content = f'''"""
Tests générés automatiquement pour {source.name}
"""
import sys
import os

# Ajouter le chemin pour pouvoir importer
sys.path.insert(0, r"{source.parent}")

def test_import():
    """Test que le module peut être importé"""
    try:
        import {source.stem}
        assert True
    except Exception as e:
        print(f"Erreur import: {{e}}")
        assert False

def test_basic():
    """Test d'exécution basique"""
    try:
        import {source.stem}
        # Juste importer, sans exécuter de code spécifique
        assert True
    except Exception as e:
        print(f"Erreur exécution: {{e}}")
        assert False
'''
    
    test_file.write_text(test_content, encoding="utf-8")
    return test_file
