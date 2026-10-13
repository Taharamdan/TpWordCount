import random
from pathlib import Path

# Partir des mots du TP deja realise
mots = Path("mots.txt").read_text(encoding="utf-8").split()
if not mots:
    raise ValueError("mots.txt est vide")

# Creer une base de 100 lignes (un mot par ligne)
random.seed(42)
base = mots[:]
while len(base) < 100:
    base.append(random.choice(mots))
base = base[:100]
random.shuffle(base)

# Repeter les memes 100 lignes avec differentes valeurs de m
for m in [1, 10, 100, 1000]:
    fichier = Path(f"mots_{100 * m}.txt")
    with fichier.open("w", encoding="utf-8") as f:
        for _ in range(m):
            f.write("\n".join(base) + "\n")
    print(f"{fichier.name} : {100 * m} lignes, {fichier.stat().st_size} octets (m={m})")
