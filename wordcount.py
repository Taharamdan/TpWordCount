def compter_occurrences(fichier):
    with open(fichier, "r", encoding="utf-8") as f:
        mots = f.read().split()

    compteur = {}
    for mot in mots:
        compteur[mot] = compteur.get(mot, 0) + 1
    return compteur

resultats = compter_occurrences("mots.txt")

for mot, nb in sorted(resultats.items(), key=lambda x: x[1], reverse=True):
    print(f"{mot} : {nb}")
