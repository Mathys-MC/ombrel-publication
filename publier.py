"""Publication des lots organiques depuis GitHub Actions (accord du fondateur 2026-10-06 : remplace la tâche
launchd du Mac, dont la connexion — partage iPhone — coupait les envois).

Lancé par .github/workflows/publier.yml aux heures des créneaux (TZ=Europe/Paris).
Ne publie QUE les lots "valide_par_fondateur": true, et seulement les éléments arrivés à l'heure.
Les médias sont des adresses publiques (Fichiers Shopify, hébergés à l'avance par
04-scripts-python/organique_heberger_medias.py) : aucun envoi de fichier ici.
Garde-fous : 3 publications au plus par passage ; un élément en retard de plus de 90 minutes
(GitHub peut décaler un passage) passe en « en_retard » pour être revu, jamais en rafale.
Journal : lots/journal-publication.log (réécrit dans le dépôt après chaque passage).
"""
import datetime
import glob
import json
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
LOTS = os.path.join(ICI, "lots")
JOURNAL = os.path.join(LOTS, "journal-publication.log")
PAUSE = os.path.join(LOTS, "PAUSE")
MAX_RETARD, MAX_ENVOIS = 90, 3
ECHECS_AVANT_PAUSE = 4  # frein : 4 éléments en erreur d'affilée → le robot se met en pause (fichier lots/PAUSE)


def journal(msg):
    with open(JOURNAL, "a") as f:
        f.write(f"{datetime.datetime.now().isoformat(timespec='seconds')} {msg}\n")


def main():
    os.chdir(ICI)
    if os.path.exists(PAUSE):
        return  # en pause : supprimer lots/PAUSE pour reprendre, après avoir réglé le problème
    from social_api import lot_publish_due
    for p in sorted(glob.glob(os.path.join(LOTS, "2026-S*.json"))):
        with open(p) as f:
            if not json.load(f).get("valide_par_fondateur"):
                continue
        try:
            r = lot_publish_due(p, confirm=True, max_retard=MAX_RETARD, max_envois=MAX_ENVOIS)
        except Exception as e:  # jamais d'arrêt silencieux : on note et on retente au passage suivant
            journal(f"{os.path.basename(p)} ERREUR {type(e).__name__} : {str(e)[:300]}")
            continue
        for e in r["envois"]:
            if "resultats" in e:
                etat = {k: ("erreur : " + v["erreur"][:200]) if "erreur" in v else (v.get("permalink") or "ok")
                        for k, v in e["resultats"].items()}
                journal(f"{os.path.basename(p)} {e['id']} {'RETENTE (réseau) ' if e.get('retente') else ''}{etat}")
            else:
                journal(f"{os.path.basename(p)} {e['id']} {e.get('statut')} {e.get('problemes') or e.get('prevu', '')}")
    frein()


def frein():
    traites = []
    for p in glob.glob(os.path.join(LOTS, "2026-S*.json")):
        traites += [i for i in json.load(open(p))["items"] if i.get("publie_le")]
    derniers = sorted(traites, key=lambda i: i["publie_le"])[-ECHECS_AVANT_PAUSE:]
    if len(derniers) == ECHECS_AVANT_PAUSE and all(i.get("statut") == "erreur" for i in derniers):
        with open(PAUSE, "w") as f:
            f.write(f"Pause automatique : {ECHECS_AVANT_PAUSE} erreurs d'affilée ({', '.join(i['id'] for i in derniers)})\n")
        journal(f"PAUSE AUTOMATIQUE : {ECHECS_AVANT_PAUSE} erreurs d'affilée, plus rien n'est publié")


if __name__ == "__main__":
    main()
