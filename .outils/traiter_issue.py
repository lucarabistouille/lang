#!/usr/bin/env python3
"""Traite une demande GitHub (formulaire « Ajouter un mot » ou « Corriger ou supprimer un mot ») dans mots.txt.

Lancé par le workflow .github/workflows/traiter-demande.yml (événement « issues: opened »). N'agit que si la demande a été
créée par le propriétaire du dépôt : les demandes d'inconnus sont ignorées. Le contenu de la demande n'est jamais passé
à un shell : il est lu ici dans le fichier d'événement.

Usage local (tests) : python traiter_issue.py --event evenement.json --mots jardin/mots.txt --reponse reponse.md
Sorties (GITHUB_OUTPUT) : etat = ok | ko | ignore ; modifie = true | false
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from formulaires import AJOUT, CORRECTION, lignes_depuis_ajout, lit_corps, reconnait, une_ligne  # noqa: E402
from jardin_texte import ErreurListe, ajoute_texte, remplace_mot, supprime_mot  # noqa: E402


def sortie(cle, valeur):
    f = os.environ.get("GITHUB_OUTPUT")
    if f:
        with open(f, "a", encoding="utf-8") as h:
            h.write(f"{cle}={valeur}\n")
    print(f"{cle}={valeur}")


def applique(texte, formulaire, v):
    """-> (nouveau texte, résumé en Markdown). Lève ErreurListe."""
    if formulaire is AJOUT:
        lignes, sous, force = lignes_depuis_ajout(v)
        nouveau = ajoute_texte(texte, lignes, sous or None, force)
        ou = f" sous **{sous}**" if sous else ""
        return nouveau, "✔ Ajouté" + ou + " :\n\n```\n" + "\n".join(lignes) + "\n```"
    mot = une_ligne(v["mot"])
    if v["action"].startswith("Supprimer"):
        return supprime_mot(texte, mot), f"✔ Supprimé : **{mot}** (et ses dérivés)."
    ligne = v["ligne"].strip()
    return remplace_mot(texte, mot, ligne), f"✔ Ligne de **{mot}** remplacée :\n\n```\n{ligne}\n```"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--event", default=os.environ.get("GITHUB_EVENT_PATH"))
    ap.add_argument("--mots", default="jardin/mots.txt")
    ap.add_argument("--reponse", default="reponse.md")
    ap.add_argument("--proprietaire", default=os.environ.get("GITHUB_REPOSITORY_OWNER", ""))
    a = ap.parse_args()
    issue = json.loads(Path(a.event).read_text(encoding="utf-8"))["issue"]

    # Sécurité : seule une demande ouverte par le propriétaire du dépôt est exécutée.
    if not a.proprietaire or issue["user"]["login"] != a.proprietaire or issue.get("author_association") != "OWNER":
        print("Demande d'un autre compte : ignorée.")
        sortie("etat", "ignore")
        sortie("modifie", "false")
        return
    f = reconnait(issue.get("body") or "")
    if f is None:
        print("Demande sans rapport avec la liste : ignorée.")
        sortie("etat", "ignore")
        sortie("modifie", "false")
        return

    mots = Path(a.mots)
    texte = mots.read_text(encoding="utf-8")
    try:
        nouveau, resume = applique(texte, f, lit_corps(issue["body"], f))
        mots.write_text(nouveau, encoding="utf-8")
        reponse = resume + "\n\nLes pages seront mises à jour dans une minute environ."
        etat = "ok"
    except ErreurListe as e:
        reponse, etat = f"✘ Rien n'a été modifié : {e}\n\nVous pouvez refaire la demande depuis le site.", "ko"
    Path(a.reponse).write_text(reponse + "\n", encoding="utf-8")
    sortie("etat", etat)
    sortie("modifie", "true" if etat == "ok" else "false")


if __name__ == "__main__":
    main()
