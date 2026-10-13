from pyspark.sql import SparkSession
from collections import Counter
import time
import csv

spark = SparkSession.builder \
    .master("local[2]") \
    .appName("TP2_WordCount") \
    .getOrCreate()

spark.sparkContext.setLogLevel("ERROR")
sc = spark.sparkContext

tailles = [100, 1000, 10000, 100000]
resultats = []

for n in tailles:
    fichier = f"mots_{n}.txt"

    # Python simple
    debut = time.perf_counter()

    with open(fichier, "r") as f:
        compteur = Counter(f.read().split())

    temps_python = time.perf_counter() - debut

    # PySpark
    debut = time.perf_counter()

    lignes = sc.textFile(fichier)
    mots = lignes.flatMap(lambda ligne: ligne.split())
    paires = mots.map(lambda mot: (mot, 1))
    comptage = dict(paires.reduceByKey(lambda a, b: a + b).collect())

    temps_spark = time.perf_counter() - debut

    assert compteur == comptage

    print(f"\n{n} lignes")
    print(f"Python : {temps_python:.4f} s")
    print(f"PySpark : {temps_spark:.4f} s")
    print(f"Vérification OK : {sum(comptage.values())} mots")

    resultats.append([n, temps_python, temps_spark])

with open("resultats_pyspark.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Lignes", "Python", "PySpark"])
    writer.writerows(resultats)

spark.stop()
print("\nTerminé !")
