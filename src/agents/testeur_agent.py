"""
Agent Testeur (The Judge) - Refactoring Swarm
Exécute les tests unitaires et valide le code refactorisé.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class AgentTesteur:
    """
    L'Agent Testeur exécute les tests unitaires avec pytest et génère des logs JSON.
    
    Responsabilités:
    - Exécuter les tests unitaires (pytest)
    - Générer des logs au format JSON
    - Renvoyer le code au Correcteur si échec (Self-Healing)
    - Valider la fin de mission si succès
    """
    
    def __init__(self, log_file: str = "test_logs.json"):
        """
        Initialise l'Agent Testeur.
        
        Args:
            log_file: Nom du fichier de logs JSON
        """
        self.log_file = Path(log_file)
        self.logs: List[Dict] = []
        
    def execute_tests(self, test_path: str = "tests/") -> Dict:
        """
        Exécute les tests unitaires avec pytest.
        
        Args:
            test_path: Chemin vers le dossier ou fichier de tests
            
        Returns:
            Dictionnaire contenant les résultats des tests
        """
        print(f"\n🧪 [AGENT TESTEUR] Exécution des tests dans '{test_path}'...")
        
        # Vérifier que pytest est installé
        try:
            subprocess.run(
                ["pytest", "--version"],
                check=True,
                capture_output=True,
                text=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            error_msg = "pytest n'est pas installé. Installez-le avec: pip install pytest"
            self._log_test_run(
                success=False,
                test_path=test_path,
                error=error_msg
            )
            return {
                "success": False,
                "error": error_msg,
                "output": ""
            }
        
        # Exécuter pytest avec options JSON
        try:
            result = subprocess.run(
                [
                    "pytest",
                    test_path,
                    "-v",  # Verbose
                    "--tb=short",  # Traceback court
                    "--color=yes"
                ],
                capture_output=True,
                text=True,
                timeout=60  # Timeout de 60 secondes
            )
            
            success = result.returncode == 0
            output = result.stdout + result.stderr
            
            # Logger les résultats
            test_results = self._parse_pytest_output(output)
            self._log_test_run(
                success=success,
                test_path=test_path,
                output=output,
                test_results=test_results
            )
            
            return {
                "success": success,
                "output": output,
                "test_results": test_results,
                "return_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            error_msg = "Les tests ont dépassé le timeout de 60 secondes"
            self._log_test_run(
                success=False,
                test_path=test_path,
                error=error_msg
            )
            return {
                "success": False,
                "error": error_msg,
                "output": ""
            }
        except Exception as e:
            error_msg = f"Erreur lors de l'exécution des tests: {str(e)}"
            self._log_test_run(
                success=False,
                test_path=test_path,
                error=error_msg
            )
            return {
                "success": False,
                "error": error_msg,
                "output": ""
            }
    
    def _parse_pytest_output(self, output: str) -> Dict:
        """
        Parse la sortie de pytest pour extraire les statistiques.
        
        Args:
            output: Sortie brute de pytest
            
        Returns:
            Dictionnaire avec les statistiques des tests
        """
        results = {
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "skipped": 0,
            "total": 0
        }
        
        # Parser les lignes de résultats
        for line in output.split('\n'):
            if 'passed' in line.lower():
                # Exemple: "5 passed in 0.03s"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part.lower() == 'passed' and i > 0:
                        try:
                            results['passed'] = int(parts[i-1])
                        except ValueError:
                            pass
            
            if 'failed' in line.lower():
                parts = line.split()
                for i, part in enumerate(parts):
                    if part.lower() == 'failed' and i > 0:
                        try:
                            results['failed'] = int(parts[i-1])
                        except ValueError:
                            pass
            
            if 'error' in line.lower():
                parts = line.split()
                for i, part in enumerate(parts):
                    if 'error' in part.lower() and i > 0:
                        try:
                            results['errors'] = int(parts[i-1])
                        except ValueError:
                            pass
        
        results['total'] = results['passed'] + results['failed'] + results['errors'] + results['skipped']
        
        return results
    
    def _log_test_run(
        self,
        success: bool,
        test_path: str,
        output: str = "",
        test_results: Optional[Dict] = None,
        error: Optional[str] = None
    ):
        """
        Enregistre une exécution de test dans les logs JSON.
        
        Args:
            success: Succès ou échec des tests
            test_path: Chemin des tests exécutés
            output: Sortie complète des tests
            test_results: Statistiques des tests
            error: Message d'erreur éventuel
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": "Testeur",
            "success": success,
            "test_path": test_path,
            "test_results": test_results or {},
            "output": output[:1000] if output else "",  # Limiter la taille
            "error": error
        }
        
        self.logs.append(log_entry)
        self._save_logs()
    
    def _save_logs(self):
        """Sauvegarde les logs dans le fichier JSON."""
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(self.logs, f, indent=2, ensure_ascii=False)
            print(f"📝 Logs sauvegardés dans '{self.log_file}'")
        except Exception as e:
            print(f"⚠️  Erreur lors de la sauvegarde des logs: {e}")
    
    def validate_mission(self, results: Dict) -> Dict:
        """
        Valide si la mission est réussie ou nécessite un retour au Correcteur.
        
        Args:
            results: Résultats de l'exécution des tests
            
        Returns:
            Dictionnaire avec le statut de validation et les actions à prendre
        """
        if results.get("success", False):
            print("\n✅ [AGENT TESTEUR] Tous les tests sont passés - Mission validée!")
            
            validation = {
                "status": "SUCCESS",
                "message": "Tous les tests unitaires sont passés avec succès",
                "next_action": "TERMINATE",
                "test_results": results.get("test_results", {})
            }
            
            self._log_validation(validation)
            return validation
        
        else:
            print("\n❌ [AGENT TESTEUR] Tests échoués - Retour au Correcteur (Self-Healing)")
            
            validation = {
                "status": "FAILED",
                "message": "Des tests ont échoué",
                "next_action": "SEND_TO_FIXER",
                "error_logs": results.get("output", ""),
                "test_results": results.get("test_results", {})
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
    
    def run_full_test_cycle(self, test_path: str = "tests/") -> Dict:
        """
        Exécute un cycle complet: tests + validation.
        
        Args:
            test_path: Chemin vers les tests
            
        Returns:
            Résultat de la validation
        """
        print("\n" + "="*60)
        print("🧪 AGENT TESTEUR - Cycle de test complet")
        print("="*60)
        
        # Exécuter les tests
        results = self.execute_tests(test_path)
        
        # Valider les résultats
        validation = self.validate_mission(results)
        
        # Afficher un résumé
        self._print_summary(validation)
        
        return validation
    
    def _print_summary(self, validation: Dict):
        """Affiche un résumé de la validation."""
        print("\n" + "="*60)
        print("📊 RÉSUMÉ DE LA VALIDATION")
        print("="*60)
        print(f"Statut: {validation['status']}")
        print(f"Message: {validation['message']}")
        print(f"Action suivante: {validation['next_action']}")
        
        if 'test_results' in validation and validation['test_results']:
            results = validation['test_results']
            print(f"\nTests passés: {results.get('passed', 0)}")
            print(f"Tests échoués: {results.get('failed', 0)}")
            print(f"Erreurs: {results.get('errors', 0)}")
            print(f"Total: {results.get('total', 0)}")
        
        print("="*60)
    
    def get_logs(self) -> List[Dict]:
        """Retourne tous les logs."""
        return self.logs
    
    def clear_logs(self):
        """Efface tous les logs."""
        self.logs = []
        self._save_logs()
        print("🗑️  Logs effacés")

