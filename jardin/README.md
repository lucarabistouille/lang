# Ma liste — format de `dictionnaire.json`

Le fichier se remplit à la main. Il alimente deux pages générées en HTML complet (rien n'est lu en JSON par le navigateur) : `index.html` (la liste en arborescence) et `apprentissage.html` (colonnes allemand | français, avec masquage d'une colonne pour se tester, recherche, curseur de police). Après modification, lancer à la racine du projet :

```
python build_jardin.py        # régénère seulement cette page
python build_all.py           # ou tout le site
```

## Structure

```json
{
  "meta": { "titre": "…", "auteur": "…", "intro": "…", "tri": true },
  "entrees": [ { … }, { … } ]
}
```

`tri: true` classe les entrées de premier niveau par ordre alphabétique (l'article est ignoré). Les entrées sont rangées par lettre.

## Une entrée (un « nœud »)

Tous les champs sont facultatifs, sauf `de` ou `fr`.

| Champ | Sens |
|---|---|
| `de` | le mot ou l'expression en allemand, **orthographe actuelle** |
| `fr` | la traduction ou la note en français |
| `type` | `mot` (défaut : en gras, peut recevoir des liens), `derive` (en italique), `expr` / `prov` (expression ou proverbe, étiquette « Prov. »), `fam` (familier, étiquette « Fam. »), `note` (texte libre) |
| `article` | `der`, `die` ou `das` |
| `pluriel` | `die Aale` (ou juste `Aale`), vide si pas de pluriel |
| `formes` | verbes forts : `isst, aß, gegessen` |
| `regime` | construction : `+D`, `+A`… |
| `etym` | l'étymologie (étiquette « Étym. ») |
| `id` | ancre personnalisée (par défaut : le mot sans article, en minuscules et sans accents) |
| `enfants` | liste de nœuds du même format : dérivés, expressions, sous-familles… sur autant de niveaux que voulu |

## Liens entre entrées

Dans `de`, `fr` ou `etym` :

- `[[glatt]]` : lien vers l'entrée `glatt` ;
- `[[Feier|feier]]` : texte affiché `Feier`, cible `feier`. Pour un composé : `aal[[glatt]]`.

Le script signale à la construction les liens dont la cible n'existe pas.

## Exemple

```json
{
  "de": "Aal", "article": "der", "pluriel": "die Aale", "fr": "l'anguille",
  "etym": "cf. lat. anguilla",
  "enfants": [
    { "de": "aalen", "type": "mot", "fr": "se prélasser" },
    { "de": "aal[[glatt]]", "type": "derive", "fr": "glissant comme une anguille",
      "enfants": [ { "type": "prov", "de": "sich winden wie ein Aal", "fr": "se faufiler" } ] }
  ]
}
```

Les quatre entrées présentes sont des exemples : remplacez-les par les vôtres.

## Polices

Le curseur de la page change la police des mots allemands : Antiqua, Kurrent, Fraktur, Sütterlin. Les polices sont dans `fonts/` (reprises de l'ancien projet).
