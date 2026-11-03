"""Formulaires GitHub (« issue forms ») pour ajouter / corriger des mots de la liste depuis un téléphone.

Une seule description (AJOUT, CORRECTION) sert à générer les fichiers .github/ISSUE_TEMPLATE/*.yml et à relire le contenu
des demandes reçues (traiter_issue.py), de sorte que les intitulés ne puissent pas diverger.
"""
import json
import re

from jardin_texte import ErreurListe, parse_ligne

AUCUN = "(aucun)"
SORTES = {"Mot": "", "Dérivé": "~ ", "Expression": "expr: ", "Proverbe": "prov: ", "Familier": "fam: "}

AJOUT = {
    "fichier": "ajout.yml",
    "name": "Ajouter un mot",
    "description": "Ajouter un mot à la liste",
    "title": "Ajout : ",
    "intro": "Remplissez au moins le mot et sa traduction. La demande est traitée automatiquement (une minute environ).",
    "champs": [
        {"id": "mot", "type": "input", "label": "Mot allemand", "description": "Sans l'article.", "placeholder": "Aal", "requis": True},
        {"id": "traduction", "type": "input", "label": "Traduction", "placeholder": "l'anguille", "requis": True},
        {"id": "article", "type": "dropdown", "label": "Article", "options": [AUCUN, "der", "die", "das"]},
        {"id": "pluriel", "type": "input", "label": "Pluriel", "placeholder": "die Aale"},
        {"id": "formes", "type": "input", "label": "Formes irrégulières (verbes forts)", "placeholder": "isst, aß, gegessen"},
        {"id": "regime", "type": "input", "label": "Construction", "placeholder": "+A"},
        {"id": "sorte", "type": "dropdown", "label": "Sorte", "options": list(SORTES)},
        {"id": "sous", "type": "input", "label": "Ranger sous le mot",
         "description": "Facultatif : un mot déjà dans la liste (sa famille).", "placeholder": "Aal"},
        {"id": "etym", "type": "input", "label": "Étymologie", "placeholder": "cf. lat. anguilla"},
        {"id": "note", "type": "textarea", "label": "Note"},
        {"id": "doublon", "type": "checkboxes", "label": "Doublon", "options": ["Autoriser un doublon (homographe)"]},
    ],
}

CORRECTION = {
    "fichier": "correction.yml",
    "name": "Corriger ou supprimer un mot",
    "description": "Corriger la ligne d'un mot, ou le supprimer",
    "title": "Correction : ",
    "intro": "Indiquez le mot, puis la nouvelle ligne (syntaxe de mots.txt) ou choisissez de le supprimer.",
    "champs": [
        {"id": "action", "type": "dropdown", "label": "Action", "options": ["Remplacer la ligne du mot", "Supprimer le mot et ses dérivés"]},
        {"id": "mot", "type": "input", "label": "Mot concerné", "placeholder": "Aal", "requis": True},
        {"id": "ligne", "type": "textarea", "label": "Nouvelle ligne",
         "description": "Pour « Remplacer » : la ligne complète, par exemple « der Aal (die Aale) : l'anguille ».",
         "placeholder": "der Aal (die Aale) : l'anguille"},
    ],
}
FORMULAIRES = (AJOUT, CORRECTION)


def _q(s):
    """Chaîne YAML entre guillemets (un littéral JSON est un scalaire YAML valide)."""
    return json.dumps(s, ensure_ascii=False)


def yaml_formulaire(f):
    """Texte du fichier .github/ISSUE_TEMPLATE/<fichier>."""
    out = [f"name: {_q(f['name'])}", f"description: {_q(f['description'])}", f"title: {_q(f['title'])}", "body:",
           "  - type: markdown", "    attributes:", f"      value: {_q(f['intro'])}"]
    for c in f["champs"]:
        out += [f"  - type: {c['type']}", f"    id: {c['id']}", "    attributes:", f"      label: {_q(c['label'])}"]
        if c.get("description"):
            out.append(f"      description: {_q(c['description'])}")
        if c["type"] in ("input", "textarea") and c.get("placeholder"):
            out.append(f"      placeholder: {_q(c['placeholder'])}")
        if c["type"] == "dropdown":
            out.append("      options:")
            out += [f"        - {_q(o)}" for o in c["options"]]
            out.append("      default: 0")
        if c["type"] == "checkboxes":
            out.append("      options:")
            out += [f"        - label: {_q(o)}" for o in c["options"]]
        if c.get("requis"):
            out += ["    validations:", "      required: true"]
    return "\n".join(out) + "\n"


CONFIG = "blank_issues_enabled: false\n"


# ------------------------------------------------------------------ lecture du contenu d'une demande
def lit_corps(corps, f):
    """Corps d'une demande créée par le formulaire f -> {id: valeur}. « _No response_ » devient une chaîne vide."""
    par_label = {c["label"]: c for c in f["champs"]}
    blocs, cur = {}, None
    for ligne in corps.replace("\r\n", "\n").split("\n"):
        m = re.match(r"^###\s+(.*?)\s*$", ligne)
        if m:
            cur = m.group(1)
            blocs[cur] = []
        elif cur is not None:
            blocs[cur].append(ligne)
    valeurs = {}
    for label, c in par_label.items():
        brut = "\n".join(blocs.get(label, [])).strip()
        if brut == "_No response_":
            brut = ""
        if c["type"] == "checkboxes":
            valeurs[c["id"]] = bool(re.search(r"^- \[[xX]\]", brut, re.M))
        else:
            valeurs[c["id"]] = brut
    return valeurs


def reconnait(corps):
    """Formulaire correspondant à ce corps de demande, ou None (autre demande : ignorée)."""
    for f in FORMULAIRES:
        premier = f["champs"][0]["label"] if f is AJOUT else "Action"
        if re.search(rf"^###\s+{re.escape(premier)}\s*$", corps, re.M) and \
           all(re.search(rf"^###\s+{re.escape(c['label'])}\s*$", corps, re.M) for c in f["champs"] if c.get("requis")):
            return f
    return None


def une_ligne(s):
    return re.sub(r"\s+", " ", s or "").strip()


def lignes_depuis_ajout(v):
    """Valeurs du formulaire d'ajout -> (lignes, sous, force). Lève ErreurListe si la saisie est inutilisable."""
    mot, trad = une_ligne(v["mot"]), une_ligne(v["traduction"])
    if not mot or not trad:
        raise ErreurListe("Le mot allemand et la traduction sont obligatoires.")
    if ":" in mot:
        raise ErreurListe("Le mot allemand ne doit pas contenir « : » (c'est le séparateur avec la traduction).")
    art = v["article"] if v["article"] in ("der", "die", "das") else ""
    pre = SORTES.get(v["sorte"] or "Mot")
    if pre is None:
        raise ErreurListe(f"Sorte inconnue : « {v['sorte']} ».")
    s = pre + (art + " " if art else "") + mot
    if une_ligne(v["pluriel"]):
        s += f" ({une_ligne(v['pluriel'])})"
    if une_ligne(v["formes"]):
        s += f" [{une_ligne(v['formes'])}]"
    if une_ligne(v["regime"]):
        s += " +" + une_ligne(v["regime"]).lstrip("+ ")
    s += f" : {trad}"
    n = parse_ligne(s)
    if n.get("de") != mot or n.get("fr") != trad or "_etym" in n:  # ex. un mot qui ressemble à un mot-clé (« Note »)
        raise ErreurListe(f"La ligne « {s} » serait mal comprise (le mot ressemble à un mot-clé : écrivez-le avec son article).")
    lignes = [s]
    if une_ligne(v["etym"]):
        lignes.append("  etym: " + une_ligne(v["etym"]))
    if une_ligne(v["note"]):
        lignes.append("  note: " + une_ligne(v["note"]))
    return lignes, une_ligne(v["sous"]), bool(v["doublon"])
