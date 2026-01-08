# Refactoring-Swarm-Equipe-30

## Installation
```bash
# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate

# Installer les dépendances
pip install -r requirements.txt

# Configurer les variables d'environnement
cp .env.example .env
# Ajouter la clé GOOGLE_API_KEY dans le fichier .env

## Utilisation

### Auditor Agent

Agent d'audit automatique de code Python utilisant Pylint et l'analyse de bugs logiques avec Google Gemini.

#### Option 1 : Délai par défaut (10 secondes)
python main.py --target_dir sandbox

#### Option 2 : Délai personnalisé
# Attendre 5 secondes entre chaque fichier
python main.py --target_dir sandbox --delay 5

# Attendre 15 secondes (pour être très prudent)
python main.py --target_dir sandbox --delay 15

# Pas de délai (risqué - peut déclencher les limites de quota API !)
python main.py --target_dir sandbox --delay 0

> **Note :** Le délai entre les fichiers permet de respecter les limites de quota de l'API Gemini. Un délai de 10 secondes est recommandé pour éviter les erreurs de rate limiting.

### Résultat attendu

Le système va :
1. Scanner tous les fichiers `.py` dans le dossier spécifié
2. Analyser chaque fichier avec Pylint
3. Détecter les bugs logiques et problèmes de sécurité
4. Générer un plan de refactoring priorisé pour chaque fichier
5. Afficher un rapport consolidé
6. Respecter les limites API avec des pauses entre les analyses

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
- Temps de délai entre les requêtes

## Configuration

### Variables d'environnement

Créer un fichier .env à la racine du projet :
env
GOOGLE_API_KEY=cle_api_google_gemini