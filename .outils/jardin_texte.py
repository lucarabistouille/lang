#!/usr/bin/env python3
"""Format texte de la liste maison (mots.txt) <-> structure d'entrées utilisée par build_jardin.py.

Une ligne = un mot ; l'indentation (espaces ou tabulation) exprime la parenté (dérivés, expressions…).

    @titre Nouveau jardin des Racines Allemandes
    der Aal (die Aale) : l'anguille
      etym: cf. lat. anguilla
      aalen : se prélasser
      ~ aal[[glatt]] : glissant comme une anguille
        prov: sich winden wie ein Aal : se faufiler
    essen [isst, aß, gegessen] +A : manger

Voir site/jardin/README.md pour la syntaxe complète.
"""
import re

import unicodedata

KINDS = {"etym", "prov", "expr", "fam", "note"}
ARTICLES = ("der", "die", "das")
RE_REGIME = re.compile(r"(?<!\w)\+\s*([A-Za-zÄÖÜ/]+)")
RE_FORMES = re.compile(r"(?<!\[)\[([^\[\]]+)\](?!\])")
RE_PAREN = re.compile(r"\(([^()]*)\)")


ALIAS = {"etym": "etym", "étym": "etym", "etymologie": "etym", "étymologie": "etym",
         "prov": "prov", "proverbe": "prov", "expr": "expr", "expression": "expr",
         "fam": "fam", "familier": "fam", "note": "note", "remarque": "note", "rem": "note"}
RE_KIND = re.compile(r"^(" + "|".join(sorted(ALIAS, key=len, reverse=True)) + r")\s*:\s*(.*)$", re.I)


def parse_ligne(contenu):
    """Une ligne (sans indentation) -> dict de nœud, ou {"_etym": texte} pour une ligne « etym: … ».
    Un mot-clé (note:, etym:, prov:…) est reconnu même précédé de « ~ » ou d'une puce « - »."""
    contenu = re.sub(r"^[-*•]\s+", "", contenu.strip())  # puces
    derive = False
    if contenu.startswith("~"):
        derive, contenu = True, contenu[1:].strip()
    type_ = "derive" if derive else "mot"
    m = RE_KIND.match(contenu)
    if m:
        kind, reste = ALIAS[m.group(1).lower()], m.group(2)
        if kind == "etym":
            return {"_etym": reste.strip()}
        if kind == "note":
            return {"type": "note", "fr": reste.strip()}
        type_ = kind
    else:
        reste = contenu
        # une phrase sans « : » n'est pas un mot : c'est une note
        if ":" not in reste and len(reste.split()) > 3:
            return {"type": "note", "fr": reste.strip(), "_auto": True}
    de_part, sep, fr = reste.partition(":")
    if type_ == "fam" and not sep:  # « fam: salaud » : seulement le français
        return {"type": "fam", "fr": reste.strip()}
    if not sep:
        fr = ""
    node = {"type": type_}

    regime = RE_REGIME.search(de_part)
    if regime:
        node["regime"] = "+" + regime.group(1)
        de_part = de_part[:regime.start()] + de_part[regime.end():]
    formes = RE_FORMES.search(de_part)
    if formes:
        node["formes"] = formes.group(1).strip()
        de_part = de_part[:formes.start()] + de_part[formes.end():]
    de_part = de_part.strip()
    a = re.match(r"^(der|die|das)\s+(.*)$", de_part, re.I)
    if a:
        node["article"] = a.group(1).lower()
        de_part = a.group(2)
    paren = RE_PAREN.search(de_part)
    if paren:
        contenu_p = paren.group(1).strip()
        premier = contenu_p.split(" ")[0].lower() if contenu_p else ""
        if "article" in node or premier in ARTICLES:
            node["pluriel"] = contenu_p
        else:
            node["info"] = contenu_p  # « (adv.) », « (pl.) »…
        de_part = (de_part[:paren.start()] + de_part[paren.end():]).strip()
    de_part = re.sub(r"\s+", " ", de_part)
    if de_part:
        node["de"] = de_part
    if fr.strip():
        node["fr"] = fr.strip()
    if type_ == "mot":
        node.pop("type")  # défaut
    return node


def parse(texte):
    """Texte -> (meta, entrees, avertissements)."""
    meta, avert = {"tri": True}, []
    racine = {"enfants": []}
    pile = [(-1, racine)]
    for num, brut in enumerate(texte.expandtabs(2).splitlines(), 1):
        if not brut.strip() or brut.lstrip().startswith("#"):
            continue
        if brut.startswith("@"):
            cle, _, val = brut[1:].partition(" ")
            if cle.strip().lower() == "tri":
                meta["tri"] = val.strip().lower() not in ("non", "false", "0")
            elif cle.strip():
                meta[cle.strip().lower()] = val.strip()
            continue
        indent = len(brut) - len(brut.lstrip(" "))
        node = parse_ligne(brut.strip())
        while pile and pile[-1][0] >= indent:
            pile.pop()
        parent = pile[-1][1] if pile else racine
        if "_etym" in node:
            if parent is racine:
                avert.append(f"ligne {num} : « etym: » sans mot parent (ignorée)")
            elif parent.get("etym"):
                parent["etym"] += " ; " + node["_etym"]
            else:
                parent["etym"] = node["_etym"]
            continue
        if node.pop("_auto", False):
            avert.append(f"ligne {num} : lue comme une note (plus de 3 mots, pas de « : ») — écrivez « note: » pour l'assumer")
        if parent is racine and not node.get("de"):
            avert.append(f"ligne {num} : « {brut.strip()[:40]} » n'est rangée sous aucun mot (ignorée) — mettez-la en retrait sous un mot")
            continue
        if not node.get("de") and node.get("type", "mot") in ("mot", "derive"):
            avert.append(f"ligne {num} : mot allemand vide ({brut.strip()[:40]!r})")
        parent.setdefault("enfants", []).append(node)
        pile.append((indent, node))
    return meta, racine["enfants"], avert


def ligne(n):
    """Nœud -> une ligne de texte."""
    t = n.get("type", "mot")
    if t == "note":
        return "note: " + n.get("fr", n.get("de", ""))
    if t == "fam" and not n.get("de"):
        return "fam: " + n.get("fr", "")
    s = ((n["article"] + " ") if n.get("article") else "") + n.get("de", "")
    if n.get("pluriel"):
        s += f" ({n['pluriel']})"
    if n.get("info"):
        s += f" ({n['info']})"
    if n.get("formes"):
        s += f" [{n['formes']}]"
    if n.get("regime"):
        s += " " + (n["regime"] if n["regime"].startswith("+") else "+" + n["regime"])
    prefixe = {"mot": "", "derive": "~ ", "prov": "prov: ", "expr": "expr: ", "fam": "fam: "}.get(t, "")
    s = prefixe + s
    if n.get("fr"):
        s += " : " + n["fr"]
    return s


def en_texte(meta, entrees):
    """(meta, entrées) -> texte mots.txt."""
    out = []
    for cle in ("titre", "auteur", "intro"):
        if meta.get(cle):
            out.append(f"@{cle} {meta[cle]}")
    if meta.get("tri") is False:
        out.append("@tri non")
    out.append("")

    def rec(n, prof):
        pad = "  " * prof
        out.append(pad + ligne(n))
        if n.get("etym"):
            out.append(pad + "  etym: " + n["etym"])
        for c in n.get("enfants", []):
            rec(c, prof + 1)

    for n in entrees:
        rec(n, 0)
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def cle(s):
    """Clé de comparaison d'un mot : sans article, sans accents, en minuscules (Äpfel == aepfel == apfel)."""
    s = re.sub(r"^(der|die|das)\s+", "", s.strip(), flags=re.I).lower()
    for a, b in (("ß", "ss"), ("ä", "ae"), ("ö", "oe"), ("ü", "ue")):
        s = s.replace(a, b)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


# ---------------------------------------------------------------------------------------------------------------------
# Opérations sur le texte de mots.txt (partagées par ajouter.py en ligne de commande et par le traitement des formulaires
# GitHub, traiter_issue.py). Fonctions pures : texte en entrée, texte en sortie ; ErreurListe = message lisible.
# ---------------------------------------------------------------------------------------------------------------------
class ErreurListe(ValueError):
    """Opération impossible sur la liste (le message est destiné à l'utilisateur)."""


def _indent(l):
    return len(l) - len(l.lstrip(" "))


def _contenu(l):
    return bool(l.strip()) and not l.lstrip().startswith(("#", "@"))


def trouve(lignes, nom):
    """Indice de la première ligne dont le mot allemand correspond à `nom` (article et accents ignorés), ou None."""
    k = cle(nom)
    for i, l in enumerate(lignes):
        if _contenu(l) and cle(parse_ligne(l.strip()).get("de", "")) == k:
            return i
    return None


def premier_niveau(lignes):
    """{clé du mot: numéro de ligne (1-based)} pour les mots de premier niveau."""
    res = {}
    for i, l in enumerate(lignes, 1):
        if l.strip() and not l.startswith((" ", "#", "@")):
            n = parse_ligne(l.strip())
            if n.get("de"):
                res.setdefault(cle(n["de"]), i)
    return res


def fin_bloc(lignes, i):
    """Indice de la première ligne après le bloc (mot + descendants) qui commence à la ligne i."""
    base = _indent(lignes[i])
    fin = i + 1
    while fin < len(lignes) and (not lignes[fin].strip() or _indent(lignes[fin]) > base):
        if not lignes[fin].strip() and (fin + 1 >= len(lignes) or _indent(lignes[fin + 1]) <= base):
            break
        fin += 1
    return fin


def _vers_texte(lignes):
    return "\n".join(lignes).rstrip() + "\n"


def ajoute_texte(texte, nouvelles, sous=None, force=False):
    """Ajoute des lignes (un mot par ligne, lignes en retrait = sous le mot précédent), éventuellement sous le mot `sous`."""
    nouvelles = [l for l in nouvelles if l.strip()]
    if not nouvelles:
        raise ErreurListe("Aucune ligne à ajouter.")
    lignes = texte.splitlines()
    if sous and sous.strip():
        i = trouve(lignes, sous)
        if i is None:
            raise ErreurListe(f"Mot parent « {sous.strip()} » introuvable dans la liste.")
        pad = " " * (_indent(lignes[i]) + 2)
        bloc = [pad + l.strip() if not l.startswith(" ") else pad + l.rstrip() for l in nouvelles]
        fin = fin_bloc(lignes, i)
        lignes[fin:fin] = bloc
    else:
        exist = premier_niveau(lignes)
        for l in nouvelles:
            if l.startswith(" "):
                continue
            n = parse_ligne(l.strip())
            k = cle(n["de"]) if n.get("de") else None
            if k and k in exist and not force:
                raise ErreurListe(f"« {n['de']} » existe déjà (ligne {exist[k]}) : rangez-le sous un mot, "
                                  f"ou autorisez le doublon s'il s'agit d'un homographe.")
        if lignes and lignes[-1].strip():
            lignes.append("")
        lignes += [l.rstrip() for l in nouvelles]
    return _vers_texte(lignes)


def remplace_mot(texte, nom, nouvelle_ligne):
    """Remplace la ligne du mot `nom` (ses dérivés en retrait sont conservés)."""
    if not nouvelle_ligne.strip() or "\n" in nouvelle_ligne.strip():
        raise ErreurListe("La nouvelle ligne doit tenir sur une seule ligne non vide.")
    lignes = texte.splitlines()
    i = trouve(lignes, nom)
    if i is None:
        raise ErreurListe(f"Mot « {nom.strip()} » introuvable dans la liste.")
    lignes[i] = " " * _indent(lignes[i]) + nouvelle_ligne.strip()
    return _vers_texte(lignes)


def supprime_mot(texte, nom):
    """Supprime le mot `nom` et tous ses descendants."""
    lignes = texte.splitlines()
    i = trouve(lignes, nom)
    if i is None:
        raise ErreurListe(f"Mot « {nom.strip()} » introuvable dans la liste.")
    del lignes[i:fin_bloc(lignes, i)]
    sortie = []
    for l in lignes:  # pas de lignes vides en double après la suppression
        if not (not l.strip() and sortie and not sortie[-1].strip()):
            sortie.append(l)
    return _vers_texte(sortie)
