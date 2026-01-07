# Refactoring-Swarm-Equipe-30

## Installation

# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt

# Configurer les variables d'environnement
cp .env.example .env
# Ajouter la clé GROQ_API_KEY dans le fichier .env
## Utilisation

# Auditor Agent
Agent d'audit automatique de code Python utilisant Pylint et l'analyse de bugs logiques,pour l'utiliser pour les codes qui qont dans sandbox il faut faire:
python main.py --target_dir sandbox

### Résultat attendu

Le système va :
1. Scanner tous les fichiers `.py` dans le dossier spécifié
2. Analyser chaque fichier avec Pylint
3. Détecter les bugs logiques et problèmes de sécurité
4. Générer un plan de refactoring priorisé pour chaque fichier
5. Afficher un rapport consolidé


## Exemples de fichiers analysés

Le dossier `sandbox/` contient des exemples de code avec différents types de problèmes :
- Bugs logiques (division par zéro, etc.)
- Violations PEP8
- Problèmes de sécurité
- Code non idiomatique

## Logs

Toutes les analyses sont enregistrées dans `logs/experiment_data.json` avec :
- Timestamp de chaque opération
- Prompts envoyés au modèle
- Réponses générées
- Statut (SUCCESS/FAILURE)