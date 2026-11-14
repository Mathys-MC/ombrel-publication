"""Boucle de publication continue (2026-11-14) : GitHub déclenchait les passages planifiés avec 3 à 5 h de retard.
Chaque exécution du robot tourne ~5 h 45 et vérifie toutes les 60 s s'il y a quelque chose à publier ; les
exécutions s'enchaînent (une en cours + une en attente, déclenchées toutes les heures), donc un post part
moins d'une minute après son heure, même si GitHub lance l'exécution en retard.
Dépôt public (accord du fondateur, option A) : minutes GitHub Actions illimitées. Les clés restent en secrets.
"""
import datetime
import subprocess
import time

import publier

DUREE_MAX = 5 * 3600 + 45 * 60
PAUSE = 60


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True)


def enregistrer():
    git("add", "lots")
    if git("diff", "--cached", "--quiet").returncode == 0:
        return
    git("commit", "-q", "-m", f"Publication {datetime.datetime.now():%Y-%m-%d %H:%M}")
    for _ in range(5):
        if git("pull", "-q", "--rebase", "origin", "main").returncode == 0 and git("push", "-q", "origin", "main").returncode == 0:
            return
        git("rebase", "--abort")
        time.sleep(10)


def main():
    debut = time.time()
    while time.time() - debut < DUREE_MAX:
        git("pull", "-q", "--rebase", "--autostash", "origin", "main")  # état le plus récent (planning envoyé depuis le Mac)
        try:
            publier.main()
        except Exception as e:  # jamais d'arrêt de la boucle : on note et on continue
            publier.journal(f"BOUCLE ERREUR {type(e).__name__} : {str(e)[:300]}")
        enregistrer()
        time.sleep(PAUSE)


if __name__ == "__main__":
    main()
