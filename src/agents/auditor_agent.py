import os
from groq import Groq
from dotenv import load_dotenv

from src.utils.tools import run_pylint, read_file
from src.utils.logger import log_experiment, ActionType

load_dotenv()

DEFAULT_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

class AuditorAgent:
    """
    Agent Auditeur :
    - Analyse statique avec Pylint
    - Analyse du code source pour détecter les bugs logiques
    - Génère un plan de refactoring priorisé
    - Ne modifie JAMAIS le code
    """

    def __init__(self, model_name: str = DEFAULT_MODEL):
        # Vérifie la clé API
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY manquante dans le fichier .env")

        # Configuration Groq client
        self.client = Groq(api_key=api_key)

        self.name = "Auditor"
        self.model_name = model_name
        self.system_prompt = read_file("prompts/auditor_system.txt")

    def audit(self, file_path: str) -> str:
        """
        Analyse un fichier Python et génère un plan de refactoring complet.
        
        Args:
            file_path: Chemin vers le fichier Python à analyser
            
        Returns:
            Plan de refactoring détaillé en Markdown
        """
        try:
            # 1. Lecture du code source
            code_content = read_file(file_path)
            
            # 2. Analyse statique du fichier Python
            pylint_report = run_pylint(file_path)

            # 3. Prépare le contenu utilisateur (code + rapport Pylint)
            user_content = (
                f"Fichier analysé : {file_path}\n\n"
                f"--- CODE SOURCE ---\n"
                f"```python\n{code_content}\n```\n\n"
                f"--- RAPPORT PYLINT ---\n"
                f"{pylint_report}\n\n"
                "Génère un plan de refactoring détaillé basé sur :\n"
                "1. Les problèmes identifiés par Pylint\n"
                "2. Les bugs logiques potentiels que tu détectes dans le code\n"
                "3. Les problèmes de sécurité (division par zéro, fichiers non fermés, etc.)\n"
                "4. Les violations des bonnes pratiques Python"
            )

            # 4. Appel au modèle Groq (chat completions)
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.3,  # Low for more deterministic refactoring plans
                max_tokens=3072,  # Augmenté pour les analyses plus détaillées
            )

            refactoring_plan = response.choices[0].message.content.strip()

            # 5. Logging strict
            log_experiment(
                agent_name=self.name,
                model_used=self.model_name,
                action=ActionType.ANALYSIS,
                status="SUCCESS",
                details={
                    "file_path": file_path,
                    "code_length": len(code_content),
                    "pylint_report": pylint_report,
                    "input_prompt": user_content,
                    "output_response": refactoring_plan
                }
            )

            return refactoring_plan

        except Exception as error:
            # Logging même en cas d'échec
            log_experiment(
                agent_name=self.name,
                model_used=self.model_name,
                action=ActionType.ANALYSIS,
                status="FAILURE",
                details={
                    "input_prompt": "AUDIT FAILED BEFORE PROMPT COMPLETION",
                    "output_response": str(error),
                    "file_path": file_path,
                    "error_type": type(error).__name__
                }
            )
            return f"Erreur Auditeur : {error}"