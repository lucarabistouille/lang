# Ma liste — ajouter des mots

Les mots s'écrivent dans **`mots.txt`**, un mot par ligne. L'indentation dit qui dépend de qui. Pas de guillemets, pas de virgules, pas d'accolades.

## Ajouter un mot : trois façons

**1. Directement dans `mots.txt`**, puis `python build_jardin.py` (ou `python build_all.py` pour tout le site).

**2. En ligne de commande**, sans ouvrir le fichier (à la racine du projet) :

```
python ajouter.py "der Aal (die Aale) : l'anguille"
python ajouter.py --sous Aal "aalen : se prélasser"
python ajouter.py "essen [isst, aß, gegessen] +A : manger" --build
```

`--sous MOT` range le nouveau mot en retrait sous `MOT`. Un mot déjà présent est refusé (`--force` pour passer outre). `--build` reconstruit la page tout de suite.

**3. En mode interactif** : `python ajouter.py` sans rien, puis tapez un mot par ligne (une ligne vide pour finir). La page est reconstruite à la fin. Les lignes en retrait se rangent sous le mot précédent, donc on peut saisir toute une famille d'un coup.

## La syntaxe d'une ligne

```
der Aal (die Aale) : l'anguille
```

| Élément | Écriture | Exemple |
|---|---|---|
| article | `der`, `die` ou `das` en début de ligne | `der Aal` |
| pluriel | entre parenthèses, après le mot | `(die Aale)` ou `(-e)` |
| formes irrégulières d'un verbe | entre crochets | `[isst, aß, gegessen]` |
| construction | `+D`, `+A`, `+G`… | `+A` |
| précision | autre parenthèse, sans article | `(adv.)` |
| traduction | après `:` | `: l'anguille` |

Tout est facultatif sauf le mot : `Haus` seul est une ligne valide.

## Les liens de parenté

L'indentation (deux espaces) range un mot sous le précédent :

```
der Aal (die Aale) : l'anguille
  etym: cf. lat. anguilla
  aalen : se prélasser
  ~ aal[[glatt]] : glissant comme une anguille
    prov: sich winden wie ein Aal : se faufiler
```

| Début de ligne | Sens |
|---|---|
| *(rien)* | un mot, en gras (on peut y faire un lien) |
| `~` | un dérivé ou un composé, en italique |
| `etym:` | l'étymologie du mot au-dessus |
| `prov:` ou `expr:` | un proverbe ou une expression |
| `fam:` | un sens ou un emploi familier (`fam: salaud`) |
| `note:` | une remarque libre |

## Liens entre entrées

- `[[glatt]]` : lien vers l'entrée `glatt`.
- `[[Feier|feier]]` : texte affiché `Feier`, cible `feier`. Pour un composé : `aal[[glatt]]`.

Le script signale à la construction les liens dont la cible n'existe pas, et les lignes qu'il n'a pas comprises.

## En-tête du fichier

```
@titre Nouveau jardin des Racines Allemandes
@auteur Luc Absil
@intro Une phrase de présentation…
```

`@tri non` désactive le classement alphabétique automatique (par défaut, les mots de premier niveau sont classés par ordre alphabétique, en ignorant l'article ; l'ordre dans le fichier n'a donc pas d'importance). Une ligne qui commence par `#` est un commentaire.

## Fichiers générés (ne pas modifier à la main)

`index.html` (la liste), `apprentissage.html` (colonnes allemand | français, avec masquage pour se tester), `dictionnaire.json` (export des données, régénéré à chaque construction), `style.css`, `jardin.js`, `theme.js`.

Le curseur de la page change la police des mots allemands : Antiqua, Kurrent, Fraktur, Sütterlin (polices dans `fonts/`).
