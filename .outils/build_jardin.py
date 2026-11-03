#!/usr/bin/env python3
"""Génère les pages de la liste maison à partir de mots.txt.

Usage : python build_jardin.py [dossier_jardin]      (défaut : site/jardin)
Lit  DOSSIER/mots.txt : un mot par ligne, l'indentation exprime la parenté (voir DOSSIER/README.md).
     À défaut de mots.txt, lit DOSSIER/dictionnaire.json (ancien format).
Écrit DOSSIER/index.html (liste), DOSSIER/apprentissage.html (colonnes allemand | français), style.css, jardin.js,
theme.js, et DOSSIER/dictionnaire.json (export généré à partir de mots.txt : ne pas l'éditer).
Tout le HTML est généré : aucun JSON n'est lu par le navigateur.
"""
import hashlib
import html
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))  # permet « python -I build_jardin.py »
from theme_js import THEME_JS  # même bascule clair/sombre que le projet Eichhoff
from jardin_texte import parse
from quiz_js import CSS_QUIZ, JS_QUIZ

ROOT = Path(__file__).parent
DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "site" / "jardin"
TXT = DIR / "mots.txt"
SRC = DIR / "dictionnaire.json"
e = html.escape

LIEN = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
ARTICLES = ("der", "die", "das")
TYPES = {"mot", "derive", "expr", "prov", "fam", "note"}
avertissements = []


def sans_article(s):
    return re.sub(r"^(der|die|das)\s+", "", s.strip(), flags=re.I)


def plain(s):
    return LIEN.sub(lambda m: m.group(1), s)


def slug(s):
    s = plain(sans_article(s)).lower()
    for a, b in (("ß", "ss"), ("ä", "ae"), ("ö", "oe"), ("ü", "ue")):
        s = s.replace(a, b)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "x"


def lettre(s):
    return (slug(s)[:1] or "#").upper()


def txt(s, cibles):
    """Texte avec liens [[mot]] ou [[texte|id]] -> <a href="#id">."""
    out, pos = [], 0
    for m in LIEN.finditer(s):
        out.append(e(s[pos:m.start()]))
        cible = slug(m.group(2) or m.group(1))
        cibles.append((cible, m.group(0)))
        out.append(f'<a class="lien" href="#{cible}">{e(m.group(1))}</a>')
        pos = m.end()
    out.append(e(s[pos:]))
    return "".join(out)


def pluriel_aff(p):
    p = (p or "").strip()
    if not p or p in ("-", "–"):
        return ""
    if p[0] in "-¨=":  # terminaison seule : « -er », « ¨e »
        return p
    return p if p.split(" ")[0].lower() in ARTICLES else f"die {p}"


def forme_allemande(n, cibles):
    """Mot allemand avec article."""
    de = txt(n.get("de", ""), cibles)
    art = n.get("article", "").strip()
    return f"{e(art)} {de}" if art else de


def extras(n):
    """(pluriel) (formes irrégulières) +régime."""
    parts = []
    pl = pluriel_aff(n.get("pluriel"))
    if pl:
        parts.append(f"({e(pl)})")
    if n.get("info"):
        parts.append(f"({e(n['info'])})")
    if n.get("formes"):
        parts.append(f"({e(n['formes'])})")
    if n.get("regime"):
        parts.append(f'<span class="regime">{e(n["regime"])}</span>')
    return (" <span class=\"ext\">" + " ".join(parts) + "</span>") if parts else ""


def attribue_id(n, ids):
    """Identifiant d'ancre : seulement pour les mots (type « mot ») ou si « id » est donné."""
    t = n.get("type", "mot")
    if t == "mot" and (n.get("de") or n.get("id")):
        i = n.get("id") or slug(n["de"])
        base, k = i, 2
        while i in ids:
            i, k = f"{base}-{k}", k + 1
        ids.add(i)
        return i
    if n.get("id"):
        ids.add(n["id"])
        return n["id"]
    return ""


def type_valide(n, chemin):
    t = n.get("type", "mot")
    if t not in TYPES:
        avertissements.append(f"{chemin} : type inconnu « {t} »")
        return "mot"
    return t


def render(n, ids, cibles, chemin):
    """Un noeud -> <li>…</li> (page « liste »)."""
    t = type_valide(n, chemin)
    de, fr = n.get("de", ""), n.get("fr", "")
    cls = ' class="german"'
    fr_html = f", {txt(fr, cibles)}" if fr and (de or n.get("article")) else (txt(fr, cibles) if fr else "")
    i = attribue_id(n, ids)
    ident = f' id="{i}"' if i else ""

    if t == "mot":
        tete = f'<span{ident}{cls}><strong>{forme_allemande(n, cibles)}</strong></span>{extras(n)}{fr_html}'
    elif t == "derive":
        tete = f'<em><span{ident}{cls}>{forme_allemande(n, cibles)}</span></em>{extras(n)}{fr_html}'
    elif t in ("expr", "prov", "fam"):
        classe = "prov" if t in ("expr", "prov") else "fam"
        allemand = f'<em{cls}>{forme_allemande(n, cibles)}</em>' if de else ""
        tete = f'<span class="{classe}">{allemand}{fr_html}</span>'
    else:  # note : texte libre en français
        tete = txt(fr or de, cibles)

    enfants = []
    if n.get("etym"):
        enfants.append(f'<li><span class="etym">{txt(n["etym"], cibles)}</span></li>')
    for c in n.get("enfants", []):
        enfants.append(render(c, ids, cibles, f"{chemin} > {c.get('de') or c.get('fr', '?')}"))
    sous = f"<ul>{''.join(enfants)}</ul>" if enfants else ""
    return f"<li>{tete}{sous}</li>"


def lignes(n, ids, cibles, profondeur, chemin):
    """Un noeud (et ses enfants) -> lignes <tr> allemand | français (page « apprentissage »)."""
    t = type_valide(n, chemin)
    de, fr = n.get("de", ""), n.get("fr", "")
    i = attribue_id(n, ids)
    ident = f' id="{i}"' if i else ""
    d = f"d{min(profondeur, 5)}"
    fleche = '<span class="fl">↳</span> ' if profondeur else ""
    if t == "note":
        out = f'<tr class="note {d}"{ident}><td colspan="2">{txt(fr or de, cibles)}</td></tr>'
    else:
        corps = forme_allemande(n, cibles)
        corps = f"<strong>{corps}</strong>" if t == "mot" else f"<em>{corps}</em>"
        tag = {"expr": "Prov.", "prov": "Prov.", "fam": "Fam."}.get(t)
        etiquette = f'<span class="tag {"t-fam" if t == "fam" else "t-prov"}">{tag}</span> ' if tag else ""
        allemand = f'<span class="german">{corps}</span>{extras(n)}' if (de or n.get("article")) else ""
        out = (f'<tr class="r-{t} {d}"{ident}><td class="de">{fleche}{etiquette}{allemand}</td>'
               f'<td class="fr">{txt(fr, cibles) if fr else ""}</td></tr>')
    if n.get("etym"):
        out += f'<tr class="etymrow {d}"><td colspan="2"><span class="etym">{txt(n["etym"], cibles)}</span></td></tr>'
    for c in n.get("enfants", []):
        out += lignes(c, ids, cibles, profondeur + 1, f"{chemin} > {c.get('de') or c.get('fr', '?')}")
    return out


CSS = """
:root{color-scheme:light;--bg:#fbf8f1;--fg:#231f1a;--mut:#7a6f60;--acc:#8a2b1d;--line:#e2d9c6;--card:#fffdf8;--de:#1d4e6b;--etym:#4a90e2;--prov:#e24a4a;--fam:#b07a1a;--de-font:Georgia,'Times New Roman',serif}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){color-scheme:dark;--bg:#171512;--fg:#ebe4d6;--mut:#a39a89;--acc:#e08a74;--line:#34302a;--card:#1f1c18;--de:#8cc3e2}}
:root[data-theme=dark]{color-scheme:dark;--bg:#171512;--fg:#ebe4d6;--mut:#a39a89;--acc:#e08a74;--line:#34302a;--card:#1f1c18;--de:#8cc3e2}
@font-face{font-family:'WiegelKurrent';src:url('fonts/WiegelKurrentMedium-MW6e.ttf') format('truetype')}
@font-face{font-family:'UnifrakturMaguntia';src:url('fonts/UnifrakturMaguntia.ttf') format('truetype')}
@font-face{font-family:'GlSuetterlin';src:url('fonts/GlSuetterlin-j710.otf') format('opentype')}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:18px/1.55 Georgia,'Times New Roman',serif}
header,main,footer{max-width:60rem;margin:0 auto;padding:0 16px}
header{padding-top:28px}
h1{font-size:1.6rem;margin:0 0 .2rem}
.sub{color:var(--mut);margin:0 0 .8rem}
.intro{max-width:44rem}
.btn,nav.top a{border:1px solid var(--line);background:var(--card);color:var(--fg);padding:.3rem .75rem;border-radius:999px;text-decoration:none;font:14px system-ui,sans-serif;cursor:pointer}
.btn.on,nav.top a.on{background:var(--acc);color:#fff;border-color:var(--acc)}
nav.top{display:flex;gap:.5rem;flex-wrap:wrap;margin:.8rem 0 1rem}
nav.top #theme{margin-left:auto}
nav.top.sub2{margin-top:-.4rem}
nav.top.sub2 a{font-size:13px;padding:.2rem .65rem;border-style:dashed}
nav.top.sub2 a.on{border-style:solid}
.toc{position:sticky;top:0;z-index:5;background:var(--bg);padding:.5rem 0;border-bottom:1px solid var(--line)}
.toc.cache .lettres,.toc.cache .controls{display:none}
.lettres{display:flex;flex-wrap:wrap;gap:.1rem .35rem;font:15px system-ui,sans-serif;margin-bottom:.4rem}
.lettres a{color:var(--acc);text-decoration:none;padding:0 .25rem}
.lettres a.vide{color:var(--mut);opacity:.4;pointer-events:none}
.controls{display:flex;gap:.7rem;flex-wrap:wrap;align-items:center;font:14px system-ui,sans-serif}
.controls input[type=search]{flex:1 1 11rem;padding:.35rem .7rem;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--fg);font:15px system-ui,sans-serif}
.controls input[type=range]{width:120px}
.font-label{color:var(--mut);font-style:italic}
h2.lettre{text-align:center;font-size:2.6rem;color:var(--acc);margin:1.5rem 0 .4rem}
ul{list-style:none;padding-left:0;margin:0}
section.lettre>ul{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:.5rem 1rem;margin-bottom:1.5rem;font-size:1.15rem}
section.lettre>ul>li{padding:.25rem 0;border-top:1px solid var(--line)}
section.lettre>ul>li:first-child{border-top:none}
ul ul{padding-left:1.4rem;border-left:2px solid var(--line);margin:.15rem 0 .2rem .2rem;font-size:.95em}
li{margin:.1rem 0}
.german{font-family:var(--de-font);color:var(--de);transition:font-family .3s}
a.lien{color:var(--acc);text-decoration:none;border-bottom:1px dotted var(--acc)}
.ext,.regime{color:var(--mut);font-size:.85em}
.regime{font-weight:600}
.etym,.prov,.fam{position:relative;display:inline-block;padding-left:3em}
.etym{font-style:italic;color:var(--mut);font-size:.85em}
.etym::before,.prov::before,.fam::before{position:absolute;left:0;top:.15em;font-style:normal;font-size:.7em;color:var(--mut);border-radius:6px;padding:0 .3em}
.etym::before{content:'Étym.';border-bottom:1px solid var(--etym)}
.prov::before{content:'Prov.';border-bottom:1px solid var(--prov)}
.fam::before{content:'Fam.';border-bottom:1px solid var(--fam)}
/* apprentissage : colonnes distinctes */
table.pairs{width:100%;border-collapse:collapse;margin:0 0 1.5rem;background:var(--card);border:1px solid var(--line);border-radius:10px}
table.pairs td{padding:.3rem .6rem;border-top:1px solid var(--line);vertical-align:top;width:50%}
table.pairs td[colspan]{width:auto}
tbody.ent>tr:first-child td{border-top:2px solid var(--line)}
tr.d1 td.de{padding-left:2rem}tr.d2 td.de{padding-left:3.4rem}tr.d3 td.de{padding-left:4.8rem}tr.d4 td.de{padding-left:6.2rem}tr.d5 td.de{padding-left:7.6rem}
tr.note td,tr.etymrow td{color:var(--mut);font-size:.9em;padding-top:.1rem;padding-bottom:.1rem;border-top:none}
tr.d1.note td,tr.d1.etymrow td{padding-left:2rem}tr.d2.note td,tr.d2.etymrow td{padding-left:3.4rem}tr.d3.note td,tr.d3.etymrow td{padding-left:4.8rem}
.fl{color:var(--mut)}
.tag{font:11px system-ui,sans-serif;color:var(--mut);border-bottom:1px solid var(--prov);margin-right:.3rem}
.tag.t-fam{border-color:var(--fam)}
body.m-de td.de,body.m-fr td.fr{filter:blur(7px);cursor:pointer;user-select:none}
body td.rev{filter:none!important}
.vide{padding:1rem;color:var(--mut)}
.masque{display:none}
footer{padding:2rem 16px;color:var(--mut);font:13px system-ui,sans-serif}
@media print{nav.top,.toc{display:none}body{background:#fff;color:#000}}
"""

JS = r"""(function(){
var FONTS=[['Antiqua',"Georgia,'Times New Roman',serif"],['Kurrent',"'WiegelKurrent',serif"],['Fraktur',"'UnifrakturMaguntia',serif"],['Sütterlin',"'GlSuetterlin',serif"]];
function lire(k){try{return localStorage.getItem(k);}catch(e){return null;}}
function ecrire(k,v){try{localStorage.setItem(k,v);}catch(e){}}
function police(i){i=Math.max(0,Math.min(FONTS.length-1,parseInt(i,10)||0));
 document.documentElement.style.setProperty('--de-font',FONTS[i][1]);
 var n=document.getElementById('fontName');if(n)n.textContent=FONTS[i][0];
 var s=document.getElementById('fontSlider');if(s)s.value=i;ecrire('jardinFont',i);}
document.addEventListener('DOMContentLoaded',function(){
 var b=document.body,$=function(i){return document.getElementById(i);};
 police(lire('jardinFont')||0);
 var s=$('fontSlider');if(s)s.addEventListener('input',function(){police(s.value);});
 var toc=document.querySelector('.toc'),tb=$('toggleToc');
 if(tb)tb.addEventListener('click',function(){toc.classList.toggle('cache');tb.textContent=toc.classList.contains('cache')?'⬇':'⬆';});
 // masquage des colonnes (page d'apprentissage)
 var bd=$('b-de'),bf=$('b-fr');
 function revele(){[].forEach.call(document.querySelectorAll('td.rev'),function(t){t.classList.remove('rev');});}
 function maj(){if(bd)bd.classList.toggle('on',b.classList.contains('m-de'));if(bf)bf.classList.toggle('on',b.classList.contains('m-fr'));}
 if(bd)bd.addEventListener('click',function(){revele();b.classList.remove('m-fr');b.classList.toggle('m-de');maj();});
 if(bf)bf.addEventListener('click',function(){revele();b.classList.remove('m-de');b.classList.toggle('m-fr');maj();});
 b.addEventListener('click',function(ev){var t=ev.target.closest&&ev.target.closest('td');
  if(t&&((t.classList.contains('de')&&b.classList.contains('m-de'))||(t.classList.contains('fr')&&b.classList.contains('m-fr'))))t.classList.toggle('rev');});
 // recherche (liste : <li> de premier niveau ; apprentissage : <tbody class="ent">)
 var q=$('q');
 function norm(x){return x.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'');}
 var tq;
 if(q)q.addEventListener('input',function(){clearTimeout(tq);tq=setTimeout(function(){var v=norm(q.value.trim());
  document.querySelectorAll('section.lettre').forEach(function(sec){var vis=0;
   sec.querySelectorAll(':scope>ul>li, tbody.ent').forEach(function(el){var ok=!v||norm(el.textContent).indexOf(v)>=0;el.classList.toggle('masque',!ok);if(ok)vis++;});
   sec.classList.toggle('masque',!vis);});},150);});
});})();
"""


# Dépôt GitHub du site : les formulaires « Ajouter » / « Corriger » y créent une demande, traitée par un workflow
DEPOT = "lucarabistouille/lang"

# empreinte des fichiers statiques : change dès que le CSS/JS change, ce qui évite qu'un navigateur garde l'ancienne feuille en cache
VERSION = hashlib.md5((CSS + CSS_QUIZ + JS + JS_QUIZ + THEME_JS).encode("utf-8")).hexdigest()[:8]

SOUS_PAGES = (("index.html", "Liste", "liste"), ("apprentissage.html", "Apprentissage", "appr"), ("quiz.html", "Quiz", "quiz"),
              (f"https://github.com/{DEPOT}/issues/new?template=ajout.yml", "＋ Ajouter", "ajout"))


def collecte_cartes(entrees):
    """Une carte par mot / dérivé / expression ayant un mot allemand ET une traduction (les notes sont ignorées)."""
    cartes, vus = [], {}

    def rec(n, racine):
        t = n.get("type", "mot")
        if t in ("mot", "derive", "expr", "prov", "fam") and n.get("de") and n.get("fr"):
            de = plain(n["de"]).strip()
            base = slug(de)
            vus[base] = vus.get(base, 0) + 1
            ident = base if vus[base] == 1 else f"{base}-{vus[base]}"
            parts = []
            pl = pluriel_aff(n.get("pluriel"))
            if pl:
                parts.append(f"({pl})")
            if n.get("info"):
                parts.append(f"({n['info']})")
            if n.get("formes"):
                parts.append(f"[{n['formes']}]")
            if n.get("regime"):
                parts.append(n["regime"])
            c = {"id": ident, "de": de, "art": n.get("article", ""), "ext": " ".join(parts),
                 "fr": plain(n["fr"]).strip(), "t": t, "l": lettre(de)}
            if n.get("etym"):
                c["etym"] = plain(n["etym"])
            if racine is not n and racine.get("de"):
                c["fam"] = (racine.get("article", "") + " " + plain(racine["de"])).strip()
            cartes.append(c)
        for enfant in n.get("enfants", []):
            rec(enfant, racine)

    for n in entrees:
        rec(n, n)
    return cartes


def page_quiz(meta, nb, cartes):
    """Page du quiz (répétition espacée) : les cartes sont embarquées dans la page, la progression reste dans le navigateur."""
    titre = meta.get("titre", "Liste de mots")
    auteur = f' · {e(meta["auteur"])}' if meta.get("auteur") else ""
    sub = "".join(f'<a href="{h}"{" class=on" if k == "quiz" else ""}>{t}</a>' for h, t, k in SOUS_PAGES)
    blob = json.dumps(cartes, ensure_ascii=False).replace("</", "<" + chr(92) + "/")
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(titre)} — quiz</title><script src="theme.js?v={VERSION}"></script><link rel="stylesheet" href="style.css?v={VERSION}"></head><body>
<header><h1>{e(titre)}</h1><p class="sub">Quiz · {len(cartes)} carte{'s' if len(cartes) > 1 else ''}{auteur}</p>
<nav class="top"><a href="../index.html" title="Accueil du site">⌂</a><button class="btn" id="theme" type="button" aria-label="Basculer entre thème clair et sombre">◐</button></nav>
<nav class="top sub2">{sub}</nav></header>
<main>
<div class="controls"><span><input type="range" id="fontSlider" min="0" max="3" step="1" value="0"> <span id="fontName" class="font-label">Antiqua</span></span></div>
<div class="qstats" id="qstats"></div>
<div class="qcard" id="qcard" data-depot="{DEPOT}"><noscript>Le quiz a besoin de JavaScript.</noscript></div>
<div class="qdonnees"><button class="btn" id="qannuler" type="button" disabled>↶ Annuler la dernière note</button></div>
<details class="qopts"><summary>Réglages et progression</summary>
<div class="qgrille">
<label>Sens<select id="qdir"><option value="both">Les deux sens</option><option value="dm">Allemand → Français</option><option value="md">Français → Allemand</option></select></label>
<label>Nouvelles cartes par jour<input type="number" id="qnouv" min="0" max="500"></label>
<label>Lettre<select id="qlettre"></select></label>
<label class="inline"><input type="checkbox" id="qsaisiecase"> Saisir la réponse (français → allemand)</label>
<label class="inline"><input type="checkbox" id="qart"> Montrer l'article dans la question (allemand → français)</label>
<label class="inline"><input type="checkbox" id="qt-mot"> Mots</label>
<label class="inline"><input type="checkbox" id="qt-derive"> Dérivés</label>
<label class="inline"><input type="checkbox" id="qt-expr"> Expressions et proverbes</label>
</div>
<div class="qdonnees"><button class="btn" id="qexport" type="button">Exporter la progression</button>
<label class="btn">Importer…<input type="file" id="qimport" accept="application/json" hidden></label>
<button class="btn" id="qreset" type="button">Tout effacer</button></div>
<p class="sub">La progression est enregistrée dans ce navigateur : exportez-la pour la sauvegarder ou la reprendre ailleurs. Raccourcis : espace = afficher la réponse, 1 à 4 = noter.</p>
</details>
<script id="cartes" type="application/json">{blob}</script>
</main>
<footer><p>Quiz à répétition espacée (principe d'Anki). Les cartes viennent de <code>mots.txt</code> : seuls les mots ayant une traduction sont interrogés.</p></footer>
<script src="jardin.js?v={VERSION}"></script><script src="quiz.js?v={VERSION}"></script></body></html>"""


def squelette(meta, nb, corps, vue_, sous_nav):
    """Page complète : en-tête, barre de lettres, contrôles, contenu, pied."""
    titre = meta.get("titre", "Liste de mots")
    toutes = [chr(c) for c in range(ord("A"), ord("Z") + 1)]
    presentes = set(re.findall(r'id="lettre-([a-z])"', corps))
    lettres_html = "".join(
        f'<a href="#lettre-{l.lower()}">{l}</a>' if l.lower() in presentes else f'<a class="vide">{l}</a>' for l in toutes)
    intro = f'<p class="intro">{e(meta["intro"])}</p>' if meta.get("intro") else ""
    auteur = f' · {e(meta["auteur"])}' if meta.get("auteur") else ""
    masques = ('<button class="btn" id="b-de" type="button">Masquer l\'allemand</button>'
               '<button class="btn" id="b-fr" type="button">Masquer le français</button>') if vue_ == "appr" else ""
    aide = ('<p class="sub">Astuce : masquez une colonne pour vous tester, puis cliquez sur une cellule floue pour la révéler.</p>'
            if vue_ == "appr" else "")
    sub = "".join(f'<a href="{h}"{" class=on" if k == vue_ else ""}>{t}</a>'
                  for h, t, k in SOUS_PAGES)
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(titre)}{' — apprentissage' if vue_ == 'appr' else ''}</title><script src="theme.js?v={VERSION}"></script><link rel="stylesheet" href="style.css?v={VERSION}"></head><body>
<header><h1>{e(titre)}</h1><p class="sub">{nb} entrée{'s' if nb > 1 else ''}{auteur}</p>{intro}
<nav class="top"><a href="../index.html" title="Accueil du site">⌂</a><button class="btn" id="theme" type="button" aria-label="Basculer entre thème clair et sombre">◐</button></nav>
<nav class="top sub2">{sub}</nav></header>
<main>
<div class="toc"><div class="lettres">{lettres_html}</div>
<div class="controls"><input id="q" type="search" placeholder="Rechercher…">{masques}
<span><input type="range" id="fontSlider" min="0" max="3" step="1" value="0"> <span id="fontName" class="font-label">Antiqua</span></span>
<button class="btn" id="toggleToc" type="button" title="Replier la barre">⬆</button></div></div>
{aide}{corps}
</main>
<footer><p>Liste personnelle. Orthographe actuelle. Les liens entre mots s'écrivent <code>[[mot]]</code> dans <code>mots.txt</code>.</p>
<p><a href="https://github.com/{DEPOT}/issues/new?template=ajout.yml">＋ Ajouter un mot</a> · <a href="https://github.com/{DEPOT}/issues/new?template=correction.yml">Corriger ou supprimer un mot</a> · <a href="https://github.com/{DEPOT}/edit/main/jardin/mots.txt">Modifier le fichier</a></p></footer>
<script src="jardin.js?v={VERSION}"></script></body></html>"""


def main():
    if TXT.exists():
        meta, entrees, avert = parse(TXT.read_text(encoding="utf-8"))
        avertissements.extend(avert)
        # export JSON généré (pour réutiliser les données ailleurs) : mots.txt reste la seule source à éditer
        SRC.write_text(json.dumps({"meta": meta, "entrees": entrees}, ensure_ascii=False, indent=2), encoding="utf-8")
    elif SRC.exists():
        data = json.loads(SRC.read_text(encoding="utf-8"))
        meta, entrees = data.get("meta", {}), data.get("entrees", [])
        avertissements.append("mots.txt absent : lecture de dictionnaire.json (ancien format)")
    else:
        sys.exit(f"{TXT} introuvable")
    if meta.get("tri", True):
        entrees = sorted(entrees, key=lambda n: slug(n.get("de", "") or n.get("id", "")))
    ids, cibles = set(), []
    liste, appr = {}, {}
    for n in entrees:
        nom = n.get("de", "") or n.get("id", "?")
        l = lettre(nom)
        liste.setdefault(l, []).append(render(n, ids, cibles, nom))
        appr.setdefault(l, []).append(f'<tbody class="ent">{lignes(n, set(), [], 0, nom)}</tbody>')
    for cible, brut in cibles:
        if cible not in ids:
            avertissements.append(f"lien {brut} : aucune entrée « {cible} »")

    vide = '<p class="vide">Le dictionnaire est vide : ajoutez des mots dans <code>mots.txt</code>.</p>'
    c_liste = "".join(
        f'<section class="lettre" id="lettre-{l.lower()}"><h2 class="lettre"><span class="german">{l}</span></h2><ul>{"".join(liste[l])}</ul></section>'
        for l in sorted(liste)) or vide
    c_appr = "".join(
        f'<section class="lettre" id="lettre-{l.lower()}"><h2 class="lettre"><span class="german">{l}</span></h2>'
        f'<table class="pairs"><thead><tr><th>Allemand</th><th>Français</th></tr></thead>{"".join(appr[l])}</table></section>'
        for l in sorted(appr)) or vide
    nb = len(entrees)
    DIR.mkdir(parents=True, exist_ok=True)
    (DIR / "index.html").write_text(squelette(meta, nb, c_liste, "liste", True), encoding="utf-8")
    (DIR / "apprentissage.html").write_text(squelette(meta, nb, c_appr, "appr", True), encoding="utf-8")
    cartes = collecte_cartes(entrees)
    (DIR / "quiz.html").write_text(page_quiz(meta, nb, cartes), encoding="utf-8")
    (DIR / "quiz.js").write_text(JS_QUIZ, encoding="utf-8")
    for ancien in ("editer.html", "editeur.js"):  # ancienne page d'édition à jeton, supprimée
        (DIR / ancien).unlink(missing_ok=True)
    (DIR / "style.css").write_text(CSS + CSS_QUIZ, encoding="utf-8")
    (DIR / "jardin.js").write_text(JS, encoding="utf-8")
    (DIR / "theme.js").write_text(THEME_JS, encoding="utf-8")
    manque = [f for f in ("WiegelKurrentMedium-MW6e.ttf", "UnifrakturMaguntia.ttf", "GlSuetterlin-j710.otf") if not (DIR / "fonts" / f).exists()]
    if manque:
        avertissements.append("polices absentes de fonts/ : " + ", ".join(manque))
    print(f"jardin : {nb} entrées -> {DIR / 'index.html'} et {DIR / 'apprentissage.html'}")
    for a in avertissements:
        print("  !", a)


if __name__ == "__main__":
    main()
