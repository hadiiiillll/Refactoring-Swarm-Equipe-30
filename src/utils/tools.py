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
