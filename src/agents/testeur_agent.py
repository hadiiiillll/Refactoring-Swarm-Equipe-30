import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import os


class AgentTesteur:
    """
    L'Agent Testeur - Teste le code avec Gemini.
    
    Utilise le prompt système complet depuis prompts/testeur_system.txt
    
    Verdict :
    - "OK – exécution valide" → Pas de self-healing
    - "ERREUR BLOQUANTE – correction requise" → Self-healing activé
    """
    DEFAULT_MODEL = "gemma-3-27b-it"   
    
    def __init__(self, log_file: str = "test_logs.json", model_name: str = DEFAULT_MODEL):
        """
        Initialise l'Agent Testeur.
        
        Args:
            log_file: Nom du fichier de logs JSON
            model_name: Modèle Gemini à utiliser
        """
        self.log_file = Path(log_file)
        self.logs: List[Dict] = []
        self.error_log_file = Path("log_erreurs.json")
        self.model_name = model_name
        
        # Charger le prompt système (TOUT est dedans)
        self.system_prompt = self._load_system_prompt()
        
        # Configuration Gemini
        try:
            import google.generativeai as genai
            api_key = os.getenv("GOOGLE_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel(model_name=self.model_name)
                print(f"✓ Agent Testeur initialisé avec le modèle : {self.model_name}")
            else:
                print("⚠️  GOOGLE_API_KEY non définie - mode simulation")
                self.model = None
        except ImportError:
            print("⚠️  google.generativeai non installé - mode simulation")
            self.model = None
    
    def _load_system_prompt(self) -> str:
        """
        Charge le prompt système depuis prompts/testeur_system.txt
        
        Returns:
            Le contenu du prompt système COMPLET
        """
        prompt_file = Path("prompts/testeur_system.txt")
        
        if not prompt_file.exists():
            raise FileNotFoundError(f"Fichier prompt non trouvé : {prompt_file}")
        
        with open(prompt_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        print(f"✓ Prompt système chargé depuis {prompt_file}")
        return content
    
    def test_with_llm(self, code_file_path: str) -> Dict:
        """
        Teste le code avec Gemini en utilisant le prompt système.
        
        Args:
            code_file_path: Chemin du fichier Python à tester
            
        Returns:
            Dictionnaire avec résultats et verdict
        """
        print(f"\n🤖 [TESTEUR] Analyse du code: '{code_file_path}'")
        
        # 1. Lire le fichier de code
        try:
            with open(code_file_path, 'r', encoding='utf-8') as f:
                code_content = f.read()
            print(f"  ✓ Code lu ({len(code_content)} caractères)")
        except Exception as e:
            error_msg = f"Impossible de lire le fichier: {e}"
            return {
                "success": False,
                "error": error_msg,
                "verdict": "ERREUR BLOQUANTE – correction requise"
            }
        
        # 2. Construire le prompt COMPLET (système + code)
        full_prompt = f"""{self.system_prompt}

FICHIER À ANALYSER : {code_file_path}

CODE:
```python
{code_content}
```

Retourne UNIQUEMENT un JSON avec cette structure :
{{
    "file": "{code_file_path}",
    "timestamp": "{datetime.now().isoformat()}",
    "verdict": "OK – exécution valide" OU "ERREUR BLOQUANTE – correction requise",
    "blocking_errors": [
        {{
            "line": 10,
            "type": "SyntaxError",
            "description": "Description précise",
            "suggestion": "Action concrète"
        }}
    ],
    "non_blocking_improvements": [
        {{
            "type": "Style",
            "description": "Amélioration optionnelle",
            "suggestion": "Suggestion"
        }}
    ],
    "tests_generated": [
        {{
            "test_name": "test_function_name",
            "test_code": "def test_function_name():\\n    assert fonction(2) == 4"
        }}
    ]
}}
"""
        
        # 3. Appeler Gemini
        print("  📤 Envoi à Gemini...")
        gemini_response = self._call_gemini_api(full_prompt)
        
        if not gemini_response:
            return {
                "success": False,
                "error": "Erreur d'appel à Gemini API",
                "verdict": "ERREUR BLOQUANTE – correction requise"
            }
        
        print("  📥 Réponse reçue")
        
        # 4. Parser la réponse
        analysis = self._parse_gemini_response(gemini_response)
        
        # 5. Extraire le verdict
        verdict = analysis.get('verdict', 'ERREUR BLOQUANTE – correction requise')
        
        # 6. Déterminer succès
        success = "OK" in verdict and "exécution valide" in verdict
        
        # 7. Générer log_erreurs.json seulement si erreurs bloquantes
        error_log_generated = False
        if not success:
            error_log_generated = self._generate_error_log_file(analysis, code_file_path)
        
        # 8. Logger
        self._log_test_run(
            success=success,
            test_path=code_file_path,
            analysis=analysis,
            error_log_file=str(self.error_log_file) if error_log_generated else None,
            verdict=verdict
        )
        
        # 9. Retourner
        return {
            "success": success,
            "verdict": verdict,
            "analysis": analysis,
            "error_log_file": str(self.error_log_file) if error_log_generated else None,
            "blocking_errors": analysis.get('blocking_errors', []),
            "non_blocking_improvements": analysis.get('non_blocking_improvements', []),
            "tests_generated": analysis.get('tests_generated', [])
        }
    
    def _call_gemini_api(self, full_prompt: str) -> Optional[str]:
        """Appelle l'API Gemini avec le prompt complet."""
        try:
            if not self.model:
                print("  ⚠️  Mode simulation activé")
                return self._simulate_gemini_response()
            
            response = self.model.generate_content(
                full_prompt,
                generation_config={
                    "temperature": 0.2,
                    "max_output_tokens": 8192,
                    "top_p": 0.95,
                }
            )
            
            return response.text
            
        except Exception as e:
            print(f"  ⚠️  Erreur API Gemini: {e}, simulation...")
            return self._simulate_gemini_response()
    
    def _simulate_gemini_response(self) -> str:
        """Simule une réponse de Gemini pour démo/test."""
        return json.dumps({
            "file": "code.py",
            "timestamp": datetime.now().isoformat(),
            "verdict": "ERREUR BLOQUANTE – correction requise",
            "blocking_errors": [
                {
                    "line": 10,
                    "type": "SyntaxError",
                    "description": "Deux-points manquants",
                    "suggestion": "Ajouter ':' après 'def function(x, y)'"
                }
            ],
            "non_blocking_improvements": [
                {
                    "type": "Style",
                    "description": "Nommage non conforme PEP8",
                    "suggestion": "Renommer myVariable en my_variable"
                }
            ],
            "tests_generated": [
                {
                    "test_name": "test_function",
                    "test_code": "def test_function():\n    assert function(2, 3) == 5"
                }
            ]
        })
    
    def _parse_gemini_response(self, response: str) -> Dict:
        """Parse la réponse JSON de Gemini."""
        try:
            # Nettoyer la réponse
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            # Parser
            analysis = json.loads(cleaned)
            
            verdict = analysis.get('verdict', 'ERREUR BLOQUANTE – correction requise')
            blocking_count = len(analysis.get('blocking_errors', []))
            
            print(f"  ✓ Analyse parsée")
            print(f"  ✓ Verdict: {verdict}")
            print(f"  ✓ Erreurs bloquantes: {blocking_count}")
            
            return analysis
            
        except json.JSONDecodeError as e:
            print(f"  ❌ Erreur de parsing JSON: {e}")
            return {
                "file": "unknown",
                "verdict": "ERREUR BLOQUANTE – correction requise",
                "blocking_errors": [{
                    "line": 0,
                    "type": "ParseError",
                    "description": f"Impossible de parser la réponse Gemini: {e}",
                    "suggestion": "Vérifier le format de la réponse"
                }],
                "non_blocking_improvements": [],
                "tests_generated": []
            }
    
    def _generate_error_log_file(self, analysis: Dict, code_file: str) -> bool:
        """Génère log_erreurs.json pour le Fixateur."""
        try:
            error_log = {
                "timestamp": datetime.now().isoformat(),
                "agent": "Testeur",
                "code_file": code_file,
                "verdict": analysis.get('verdict', 'ERREUR BLOQUANTE – correction requise'),
                "blocking_errors": analysis.get('blocking_errors', []),
                "non_blocking_improvements": analysis.get('non_blocking_improvements', []),
                "tests_generated": analysis.get('tests_generated', [])
            }
            
            with open(self.error_log_file, 'w', encoding='utf-8') as f:
                json.dump(error_log, f, indent=2, ensure_ascii=False)
            
            print(f"  ✓ log_erreurs.json généré")
            return True
            
        except Exception as e:
            print(f"  ❌ Erreur génération log_erreurs.json: {e}")
            return False
    
    def _log_test_run(
        self,
        success: bool,
        test_path: str,
        analysis: Dict,
        error_log_file: Optional[str] = None,
        verdict: str = ""
    ):
        """Enregistre une exécution de test dans les logs."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": "Testeur",
            "success": success,
            "test_path": test_path,
            "verdict": verdict,
            "blocking_errors_count": len(analysis.get('blocking_errors', [])),
            "non_blocking_count": len(analysis.get('non_blocking_improvements', [])),
            "error_log_file": error_log_file
        }
        
        self.logs.append(log_entry)
        self._save_logs()
    
    def _save_logs(self):
        """Sauvegarde les logs dans le fichier JSON."""
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(self.logs, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"  ⚠️  Erreur sauvegarde logs: {e}")
    
    def validate_mission(self, results: Dict) -> Dict:
        """Valide si la mission est réussie ou nécessite retour au Fixateur."""
        verdict = results.get('verdict', 'ERREUR BLOQUANTE – correction requise')
        success = results.get('success', False)
        
        if success:
            print("\n✅ [TESTEUR] Verdict : OK – exécution valide")
            
            validation = {
                "status": "SUCCESS",
                "message": "Code validé - aucune erreur bloquante",
                "next_action": "TERMINATE",
                "verdict": verdict
            }
            
            self._log_validation(validation)
            return validation
        
        else:
            print("\n❌ [TESTEUR] Verdict : ERREUR BLOQUANTE – correction requise")
            
            validation = {
                "status": "FAILED",
                "message": "Erreurs bloquantes détectées",
                "next_action": "SEND_TO_FIXER",
                "verdict": verdict,
                "error_log_file": results.get("error_log_file", ""),
                "blocking_errors": results.get("blocking_errors", [])
            }
            
            self._log_validation(validation)
            return validation
    
    def _log_validation(self, validation: Dict):
        """Enregistre la validation dans les logs."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": "Testeur",
            "action": "Validation",
            "validation": validation
        }
        
        self.logs.append(log_entry)
        self._save_logs()
    
    def run_full_test_cycle(self, target_path: str) -> Dict:
        """
        Exécute un cycle complet de test.
        
        Args:
            target_path: Fichier .py à tester
            
        Returns:
            Résultat de la validation
        """
        print("\n" + "="*70)
        print("🧪 AGENT TESTEUR - Cycle de test")
        print("="*70)
        
        # Tester avec Gemini
        results = self.test_with_llm(target_path)
        
        # Valider
        validation = self.validate_mission(results)
        
        # Résumé
        self._print_summary(validation)
        
        return validation
    
    def _print_summary(self, validation: Dict):
        """Affiche un résumé de la validation."""
        print("\n" + "="*70)
        print("📊 RÉSUMÉ")
        print("="*70)
        print(f"Verdict: {validation['verdict']}")
        print(f"Action: {validation['next_action']}")
        
        if 'error_log_file' in validation and validation['error_log_file']:
            print(f"Fichier erreurs: {validation['error_log_file']}")
        if 'blocking_errors' in validation:
            print(f"Erreurs bloquantes: {len(validation['blocking_errors'])}")
        
        print("="*70)
    
    def get_logs(self) -> List[Dict]:
        """Retourne tous les logs."""
        return self.logs
    
    def clear_logs(self):
        """Efface tous les logs."""
        self.logs = []
        self._save_logs()