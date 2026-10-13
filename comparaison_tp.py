import csv
import getpass
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
HADOOP_HOME = Path(os.environ.get("HADOOP_HOME", str(Path.home() / "hadoop")))
HADOOP = HADOOP_HOME / "bin" / "hadoop"
HDFS = HADOOP_HOME / "bin" / "hdfs"
JAR = HADOOP_HOME / "share" / "hadoop" / "mapreduce" / "hadoop-mapreduce-examples-3.4.3.jar"
RACINE_HDFS = f"/user/{getpass.getuser()}/wordcount/comparaison"
FACTEURS = [1, 10, 100, 1000]


def lancer(commande, **options):
    return subprocess.run(commande, check=True, text=True, **options)


def lire_python(sortie):
    resultat = {}
    for ligne in sortie.splitlines():
        if " : " in ligne:
            mot, nombre = ligne.split(" : ", 1)
            resultat[mot.strip()] = int(nombre.strip())
    return resultat


def lire_hadoop(sortie):
    resultat = {}
    for ligne in sortie.splitlines():
        if "\t" in ligne:
            mot, nombre = ligne.split("\t", 1)
            resultat[mot] = int(nombre.strip())
    return resultat


def main():
    if not (HADOOP.exists() and HDFS.exists() and JAR.exists()):
        raise SystemExit(f"Hadoop introuvable dans {HADOOP_HOME}. Verifie HADOOP_HOME.")
    for programme in ("wordcount.py", "mapreduce_wordcount.py"):
        if not (DOSSIER / programme).exists():
            raise SystemExit(f"Fichier manquant : {programme}")

    # Les fichiers doivent respecter une ligne = un mot.
    for m in FACTEURS:
        fichier = DOSSIER / f"mots_{100 * m}.txt"
        if not fichier.exists():
            raise SystemExit(f"Fichier manquant : {fichier.name}. Execute python3 generation_fichiers.py")

    env = os.environ.copy()
    env.setdefault("JAVA_HOME", "/usr/lib/jvm/java-11-openjdk-amd64")
    lancer([str(HDFS), "dfs", "-mkdir", "-p", RACINE_HDFS + "/input"], env=env)
    (DOSSIER / "logs").mkdir(exist_ok=True)
    resultats = []

    for m in FACTEURS:
        n = 100 * m
        fichier = DOSSIER / f"mots_{n}.txt"
        print(f"\n{n} lignes (m={m})", flush=True)
        ligne_resultat = {"lignes": n, "m": m, "octets": fichier.stat().st_size}

        # Les scripts d'origine utilisent 'mots.txt'. On les lance
        # sans les modifier dans un dossier temporaire.
        with tempfile.TemporaryDirectory() as temporaire:
            shutil.copyfile(fichier, Path(temporaire) / "mots.txt")
            sorties = []
            for nom, colonne in [
                ("wordcount.py", "python_s"),
                ("mapreduce_wordcount.py", "pseudo_mapreduce_s"),
            ]:
                debut = time.perf_counter()
                execution = lancer(
                    [sys.executable, str(DOSSIER / nom)],
                    cwd=temporaire,
                    capture_output=True,
                    env=env,
                )
                duree = time.perf_counter() - debut
                ligne_resultat[colonne] = round(duree, 4)
                sorties.append(lire_python(execution.stdout))
                print(f"{nom} : {duree:.4f} s", flush=True)

        entree = f"{RACINE_HDFS}/input/{fichier.name}"
        sortie = f"{RACINE_HDFS}/output_{n}"
        lancer([str(HDFS), "dfs", "-put", "-f", str(fichier), entree], env=env)
        subprocess.run([str(HDFS), "dfs", "-rm", "-r", "-f", sortie],
                       env=env, capture_output=True, text=True)

        print("Hadoop : lancement du job ", flush=True)
        log = DOSSIER / "logs" / f"hadoop_{n}.log"
        debut = time.perf_counter()
        with log.open("w", encoding="utf-8") as journal:
            execution = subprocess.run(
                [str(HADOOP), "jar", str(JAR), "wordcount", entree, sortie],
                env=env, stdout=journal, stderr=subprocess.STDOUT, text=True,
            )
        duree = time.perf_counter() - debut
        if execution.returncode != 0:
            print("Le job Hadoop a echoue. Voici la fin du journal :")
            print("\n".join(log.read_text(errors="replace").splitlines()[-30:]))
            raise SystemExit(f"Erreur Hadoop pour {n} lignes (journal : {log})")

        ligne_resultat["hadoop_s"] = round(duree, 4)
        print(f"Hadoop : {duree:.4f} s", flush=True)
        texte_hadoop = lancer(
            [str(HDFS), "dfs", "-cat", sortie + "/part-r-00000"],
            env=env, capture_output=True,
        ).stdout
        comptage_hadoop = lire_hadoop(texte_hadoop)
        if not (sorties[0] == sorties[1] == comptage_hadoop):
            raise SystemExit(f"ERREUR : les comptages sont differents pour {n} lignes !")
        if sum(comptage_hadoop.values()) != n:
            raise SystemExit(f"ERREUR : le total de mots ne vaut pas {n} !")
        ligne_resultat["identiques"] = "oui"
        resultats.append(ligne_resultat)
        print(f"Verification OK : {len(comptage_hadoop)} mots differents, {n} mots comptes.")

        # Sauvegarde apres chaque jeu de donnees.
        with (DOSSIER / "resultats_comparaison.csv").open("w", newline="", encoding="utf-8") as f:
            ecrivain = csv.DictWriter(f, fieldnames=list(resultats[0]))
            ecrivain.writeheader()
            ecrivain.writerows(resultats)

    print("\nOK")


if __name__ == "__main__":
    main()
