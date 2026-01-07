import os
from groq import Groq
from dotenv import load_dotenv

from src.utils.tools import run_pylint, read_file
from src.utils.logger import log_experiment, ActionType

load_dotenv()

# Recommended Groq model (fast, strong for code reasoning & tool use)
DEFAULT_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"  # Or "llama3-70b-8192", "mixtral-8x7b-32768", etc.

class AuditorAgent:
    """
    Agent Auditeur :
    - Analyse statique avec Pylint
    - Génère un plan de refactoring
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
        try:
            # 1. Analyse statique du fichier Python
            pylint_report = run_pylint(file_path)

            # 2. Prépare le contenu utilisateur (détails + rapport)
            user_content = (
                f"Fichier analysé : {file_path}\n\n"
                f"Rapport Pylint :\n{pylint_report}\n\n"
                "Génère un plan de refactoring détaillé basé sur les problèmes identifiés."
            )

            # 3. Appel au modèle Groq (chat completions)
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.3,  # Low for more deterministic refactoring plans
                max_tokens=2048,  # Adjust based on your needs (Groq limits are generous)
            )

            refactoring_plan = response.choices[0].message.content.strip()

            # 4. Logging strict
            log_experiment(
                agent_name=self.name,
                model_used=self.model_name,
                action=ActionType.ANALYSIS,
                status="SUCCESS",
                details={
                    "file_path": file_path,
                    "pylint_report": pylint_report,
                    "input_prompt": user_content,  # Log only user part (system is static)
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
                    "file_path": file_path
                }
            )
            return f"Erreur Auditeur : {error}"