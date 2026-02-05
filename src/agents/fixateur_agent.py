import os
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv
from src.utils.logger import log_experiment, ActionType

load_dotenv()


class FixateurAgent:
    """
    Agent responsable de corriger les fichiers Python bugués
    en utilisant les rapports d'audit générés par l'AuditorAgent.
    """
    
    def __init__(self, model_name: str =  "gemma-3-27b-it" ):
        """
        Initialise le Fixateur Agent.
        
        Args:
            model_name: Le modèle Groq à utiliser
        """
        self.model_name = model_name
        api_key = os.getenv("GOOGLE_API_KEY")
        
        if not api_key:
            raise ValueError("GOOGLE_API_KEY n'est pas définie dans les variables d'environnement")
        
        genai.configure(api_key=api_key)
        
        # Charger le prompt système
        self.system_prompt = self._load_system_prompt()
        
        print(f"✓ Fixateur Agent initialisé avec le modèle : {self.model_name}")
    
    def _load_system_prompt(self) -> str:
        """
        Charge le prompt système depuis le fichier fixateur_system.txt
        
        Returns:
            Le contenu du prompt système
        """
        prompt_file = Path("prompts/fixateur_system.txt")
        
        if not prompt_file.exists():
            raise FileNotFoundError(f"Fichier prompt non trouvé : {prompt_file}")
        
        with open(prompt_file, "r", encoding="utf-8") as f:
            return f.read()
    
    def fix(self, file_path: str) -> dict:
        """
        Corrige un fichier Python bugué en utilisant son rapport d'audit.
        
        Args:
            file_path: Chemin vers le fichier Python à corriger
            
        Returns:
            dict contenant les informations sur la correction
        """
        print(f"\n{'='*70}")
        print(f"🔧 CORRECTION DE : {Path(file_path).name}")
        print(f"{'='*70}")
        
        # 1. Lire le code bugué
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                buggy_code = f.read()
            print(f"✓ Code bugué chargé ({len(buggy_code)} caractères)")
        except Exception as e:
            error_msg = f"Erreur lors de la lecture du fichier : {str(e)}"
            print(f"✗ {error_msg}")
            log_experiment(
                agent_name="FixateurAgent",
                model_used=self.model_name,
                action=ActionType.ANALYSIS,
                details={
                    "file_path": file_path,
                    "input_prompt": "Lecture du fichier bugué",
                    "output_response": error_msg
                },
                status="FAILURE"
            )
            return {"status": "error", "message": error_msg}
        
        # 2. Lire le rapport d'audit correspondant
        audit_file = Path("audit_reports") / f"{Path(file_path).stem}_audit.txt"
        
        if not audit_file.exists():
            error_msg = f"Rapport d'audit non trouvé : {audit_file}"
            print(f"✗ {error_msg}")
            log_experiment(
                agent_name="FixateurAgent",
                model_used=self.model_name,
                action=ActionType.ANALYSIS,
                details={
                    "file_path": file_path,
                    "audit_file": str(audit_file),
                    "input_prompt": "Lecture du rapport d'audit",
                    "output_response": error_msg
                },
                status="FAILURE"
            )
            return {"status": "error", "message": error_msg}
        
        try:
            with open(audit_file, "r", encoding="utf-8") as f:
                audit_report = f.read()
            print(f"✓ Rapport d'audit chargé ({len(audit_report)} caractères)")
        except Exception as e:
            error_msg = f"Erreur lors de la lecture du rapport d'audit : {str(e)}"
            print(f"✗ {error_msg}")
            log_experiment(
                agent_name="FixateurAgent",
                model_used=self.model_name,
                action=ActionType.ANALYSIS,
                details={
                    "file_path": file_path,
                    "audit_file": str(audit_file),
                    "input_prompt": "Lecture du rapport d'audit",
                    "output_response": error_msg
                },
                status="FAILURE"
            )
            return {"status": "error", "message": error_msg}
        
        # 3. Construire le prompt utilisateur
        user_prompt = f"""
FICHIER À CORRIGER : {Path(file_path).name}

CODE BUGUÉ :
```python
{buggy_code}
```

RAPPORT D'AUDIT :
{audit_report}

Corrige ce code en suivant les recommandations du rapport d'audit.
Retourne UNIQUEMENT le code Python corrigé, sans explications supplémentaires.
"""
        
        print(f"✓ Prompt construit")
        print(f"📤 Envoi de la requête à Groq {self.model_name}...")
        
        # 4. Appeler Groq pour obtenir le code corrigé
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": self.system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                temperature=0.3,
                max_tokens=8000
            )
            
            fixed_code = response.choices[0].message.content
            print(f"✓ Code corrigé reçu ({len(fixed_code)} caractères)")
            
            # Nettoyer le code (enlever les balises markdown si présentes)
            if "```python" in fixed_code:
                fixed_code = fixed_code.split("```python")[1].split("```")[0].strip()
            elif "```" in fixed_code:
                fixed_code = fixed_code.split("```")[1].split("```")[0].strip()
            
            print(f"✓ Code nettoyé")
            
        except Exception as e:
            error_msg = f"Erreur lors de l'appel à Groq : {str(e)}"
            print(f"✗ {error_msg}")
            log_experiment(
                agent_name="FixateurAgent",
                model_used=self.model_name,
                action=ActionType.ANALYSIS,
                details={
                    "file_path": file_path,
                    "input_prompt": user_prompt[:500] + "...",
                    "output_response": error_msg
                },
                status="FAILURE"
            )
            return {"status": "error", "message": error_msg}
        
        # 5. Écraser l'ancien fichier avec le code corrigé
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(fixed_code)
            print(f"✓ Fichier écrasé avec le code corrigé : {file_path}")
            
            log_experiment(
                agent_name="FixateurAgent",
                model_used=self.model_name,
                action=ActionType.ANALYSIS,
                details={
                    "file_path": file_path,
                    "audit_file": str(audit_file),
                    "input_prompt": user_prompt[:500] + "...",
                    "output_response": f"Code corrigé avec succès ({len(fixed_code)} caractères)",
                    "code_length_before": len(buggy_code),
                    "code_length_after": len(fixed_code)
                },
                status="SUCCESS"
            )
            
            return {
                "status": "success",
                "file_path": file_path,
                "audit_file": str(audit_file),
                "fixed_code": fixed_code,
                "message": "Correction réussie"
            }
            
        except Exception as e:
            error_msg = f"Erreur lors de l'écriture du fichier corrigé : {str(e)}"
            print(f"✗ {error_msg}")
            log_experiment(
                agent_name="FixateurAgent",
                model_used=self.model_name,
                action=ActionType.ANALYSIS,
                details={
                    "file_path": file_path,
                    "input_prompt": user_prompt[:500] + "...",
                    "output_response": error_msg
                },
                status="FAILURE"
            )
            return {"status": "error", "message": error_msg}