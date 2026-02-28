"""
Ce module contient une fonction pour calculer la moyenne d'une liste de notes.
"""

def calculer_moyenne(notes):
    """
    Calcule la moyenne d'une liste de notes.

    Args:
        notes (list): Une liste de nombres représentant les notes.

    Returns:
        float: La moyenne des notes. Retourne 0 si la liste est vide.
    """
    total = 0
    if not notes:
        return 0
    for n in notes:
        total += n
    return total / len(notes)

print(calculer_moyenne([10, 12, 14]))