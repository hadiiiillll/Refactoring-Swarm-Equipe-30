threshold = 10
# Variable mal nommée, pas de docstring, logique inutile
def f(value):
    """
    Vérifie si une valeur est comprise entre 0 et 100.

    Args:
        value: La valeur à vérifier.

    Returns:
        True si la valeur est comprise entre 0 et 100, False sinon.
    """
    return value > 0 and value < 100