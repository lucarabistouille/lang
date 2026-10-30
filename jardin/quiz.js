(function (root) {
'use strict';
/* ---------- Planificateur (pur, testable sous Node) ---------- */
var MIN = 60000, DAY = 86400000;
var STEPS = [1, 10];      // minutes : étapes d'apprentissage d'une carte nouvelle
var RELEARN = [10];       // minutes : réapprentissage après un oubli

function debutJour(t) { var d = new Date(t); d.setHours(0, 0, 0, 0); return d.getTime(); }
function nouvelleCarte() { return { s: 0, step: 0, ease: 2.5, ivl: 0, due: 0, reps: 0, lapses: 0 }; }

/* s : 0 nouvelle, 1 apprentissage, 2 révision, 3 réapprentissage. g : 1 Encore, 2 Difficile, 3 Bien, 4 Facile. */
function noter(c, g, now) {
  var n = JSON.parse(JSON.stringify(c)), jour = debutJour(now);
  n.reps++;
  if (n.s === 0 || n.s === 1) {
    n.s = 1;
    if (g === 1) { n.step = 0; n.due = now + STEPS[0] * MIN; }
    else if (g === 2) { n.due = now + (n.step === 0 ? (STEPS[0] + STEPS[1]) / 2 : STEPS[n.step]) * MIN; }
    else if (g === 3) {
      if (n.step < STEPS.length - 1) { n.step++; n.due = now + STEPS[n.step] * MIN; }
      else { n.s = 2; n.ivl = 1; n.due = jour + DAY; }
    } else { n.s = 2; n.ivl = 4; n.due = jour + 4 * DAY; }
  } else if (n.s === 2) {
    if (g === 1) {
      n.lapses++; n.ease = Math.max(1.3, n.ease - 0.2);
      n.ivl = Math.max(1, Math.round(n.ivl * 0.2));
      n.s = 3; n.step = 0; n.due = now + RELEARN[0] * MIN;
    } else {
      var ivl;
      if (g === 2) { ivl = Math.max(n.ivl + 1, Math.round(n.ivl * 1.2)); n.ease = Math.max(1.3, n.ease - 0.15); }
      else if (g === 3) { ivl = Math.max(n.ivl + 1, Math.round(n.ivl * n.ease)); }
      else { ivl = Math.max(n.ivl + 1, Math.round(n.ivl * n.ease * 1.3)); n.ease += 0.15; }
      n.ivl = ivl; n.due = jour + ivl * DAY;
    }
  } else {
    if (g === 1 || g === 2) { n.step = 0; n.due = now + RELEARN[0] * MIN; }
    else { n.s = 2; n.ivl = Math.max(1, n.ivl) + (g === 4 ? 1 : 0); n.due = jour + n.ivl * DAY; }
  }
  return n;
}

function libelleJours(d) {
  if (d < 30) return d + ' j';
  if (d < 365) return (d / 30).toFixed(1).replace('.', ',') + ' mois';
  return (d / 365).toFixed(1).replace('.', ',') + ' an';
}
function libelleDelai(ms) {
  var m = ms / MIN;
  if (m < 1) return '<1 min';
  if (m < 60) return Math.round(m) + ' min';
  if (m < 1440) return Math.round(m / 60) + ' h';
  return libelleJours(Math.round(ms / DAY));
}
/* Libellé de l'intervalle qui suivrait une note g (pour les boutons). */
function apercu(c, g, now) {
  var n = noter(c, g, now);
  return n.s === 2 ? libelleJours(n.ivl) : libelleDelai(n.due - now);
}

function melange(a) {
  for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)), t = a[i]; a[i] = a[j]; a[j] = t; }
  return a;
}

/* cartes : [{k, id, ...}], etats : {k: état}, p : {nouvellesRestantes, derniere (id à éviter)} */
function constituerFile(cartes, etats, p, now) {
  var fin = debutJour(now) + DAY - 1, appr = [], rev = [], nouv = [], futur = [];
  cartes.forEach(function (c) {
    var e = etats[c.k];
    if (!e || e.s === 0) { nouv.push(c); return; }
    if (e.s === 1 || e.s === 3) { (e.due <= now ? appr : futur).push({ due: e.due, c: c }); }
    else if (e.s === 2 && e.due <= fin) rev.push(c);
  });
  appr.sort(function (a, b) { return a.due - b.due; });
  futur.sort(function (a, b) { return a.due - b.due; });
  var nouvJour = melange(nouv).slice(0, Math.max(0, p.nouvellesRestantes));
  var res = {
    nNouv: nouvJour.length, nAppr: appr.length, nRev: rev.length,
    apprentissage: appr.map(function (x) { return x.c; }), revisions: melange(rev), nouvelles: nouvJour, prochain: null
  };
  // on évite de montrer deux fois de suite les deux faces d'une même note
  function premier(liste) {
    for (var i = 0; i < liste.length; i++) if (liste[i].id !== p.derniere) return liste[i];
    return liste[0] || null;
  }
  res.suivante = premier(res.apprentissage) || premier(res.revisions) || premier(res.nouvelles);
  if (!res.suivante && futur.length) {
    res.prochain = futur[0].due;
    if (futur[0].due - now <= 20 * MIN) res.suivante = futur[0].c; // apprentissage « en avance » (20 min)
  }
  return res;
}

var Plan = { noter: noter, nouvelleCarte: nouvelleCarte, constituerFile: constituerFile, apercu: apercu,
             libelleDelai: libelleDelai, debutJour: debutJour, DAY: DAY, MIN: MIN };
if (typeof module !== 'undefined' && module.exports) module.exports = Plan;
if (typeof document === 'undefined') return;

/* ---------- Interface ---------- */
var CLE = 'jardinQuizV1';
function $(i) { return document.getElementById(i); }
function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
function norm(s) {
  return String(s).toLowerCase().replace(/ß/g, 'ss').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, ' ').trim();
}
function lire() {
  try { var v = JSON.parse(localStorage.getItem(CLE) || 'null'); if (v && v.cards) return v; } catch (e) {}
  return { cards: {}, daily: { jour: '', nouvelles: 0, revues: 0 },
           reglages: { dir: 'both', nouveaux: 10, saisie: false, article: false, mot: true, derive: true, expr: true, lettre: '' } };
}
var store = lire();
function ecrire() { try { localStorage.setItem(CLE, JSON.stringify(store)); } catch (e) {} }
function jourCle(now) { var d = new Date(now); return d.getFullYear() + '-' + (d.getMonth() + 1) + '-' + d.getDate(); }
function compteurs(now) {
  if (store.daily.jour !== jourCle(now)) store.daily = { jour: jourCle(now), nouvelles: 0, revues: 0 };
  return store.daily;
}

var DATA = JSON.parse($('cartes').textContent);
var courante = null, revelee = false, derniere = null, avant = null;

function cartesActives() {
  var r = store.reglages, dirs = r.dir === 'both' ? ['dm', 'md'] : [r.dir], out = [];
  DATA.forEach(function (c) {
    var t = c.t === 'mot' ? 'mot' : (c.t === 'derive' ? 'derive' : 'expr');
    if (!r[t]) return;
    if (r.lettre && c.l !== r.lettre) return;
    dirs.forEach(function (d) { out.push({ k: c.id + '|' + d, id: c.id, dir: d, c: c }); });
  });
  return out;
}

function allemandComplet(c) {
  return (c.art ? c.art + ' ' : '') + c.de + (c.ext ? ' ' + c.ext : '');
}

function face(carte) {
  var c = carte.c, r = store.reglages;
  if (carte.dir === 'dm') {
    var q = (r.article && c.art ? c.art + ' ' : '') + c.de;
    return '<div class="q-face"><span class="german q-de">' + esc(q) + '</span></div>';
  }
  return '<div class="q-face"><span class="q-fr">' + esc(c.fr) + '</span></div>';
}
function dos(carte) {
  var c = carte.c, h = '<div class="q-dos">';
  h += '<div class="q-rep"><span class="german q-de">' + esc(allemandComplet(c)) + '</span></div>';
  h += '<div class="q-rep q-fr">' + esc(c.fr) + '</div>';
  if (c.etym) h += '<div class="q-meta"><span class="q-tag">Étym.</span> ' + esc(c.etym) + '</div>';
  if (c.fam) h += '<div class="q-meta"><span class="q-tag">Famille</span> <span class="german">' + esc(c.fam) + '</span></div>';
  return h + '</div>';
}

function verifie(carte, saisie) {
  var c = carte.c, attendu = norm(c.de), s = norm(saisie);
  if (!s) return '';
  var sansArt = norm(saisie.replace(/^(der|die|das)\s+/i, ''));
  if (c.art && s === norm(c.art + ' ' + c.de)) return '<span class="ok">✔ Correct</span>';
  if (sansArt === attendu) return c.art ? '<span class="mi">≈ Mot juste, article : ' + esc(c.art) + '</span>' : '<span class="ok">✔ Correct</span>';
  return '<span class="ko">✘ Réponse attendue : ' + esc(allemandComplet(c)) + '</span>';
}

function rendre() {
  var now = Date.now(), r = store.reglages, cpt = compteurs(now);
  var actives = cartesActives();
  var f = constituerFile(actives, store.cards, { nouvellesRestantes: r.nouveaux - cpt.nouvelles, derniere: derniere }, now);
  $('qstats').innerHTML = '<span class="qs-n">Nouvelles <b>' + f.nNouv + '</b></span><span class="qs-a">À revoir <b>' + f.nAppr +
    '</b></span><span class="qs-r">Dues <b>' + f.nRev + '</b></span><span class="qs-t">Cartes <b>' + actives.length + '</b></span>';
  var zone = $('qcard');
  courante = f.suivante; revelee = false;
  if (!actives.length) { zone.innerHTML = '<p class="vide">Aucune carte : ajoutez des mots avec une traduction dans <code>mots.txt</code>, ou élargissez les filtres.</p>'; return; }
  if (!courante) {
    var msg = '<p class="fini">✔ Terminé pour aujourd’hui.</p>';
    if (f.prochain) msg += '<p class="sub">Prochaine carte dans ' + Plan.libelleDelai(Math.max(0, f.prochain - now)) + '.</p>';
    zone.innerHTML = msg + '<p class="sub">Aujourd’hui : ' + cpt.nouvelles + ' nouvelles, ' + cpt.revues + ' révisions.</p>';
    return;
  }
  var saisie = r.saisie && courante.dir === 'md';
  zone.innerHTML = face(courante) +
    (saisie ? '<div class="q-saisie"><input id="qsaisie" type="text" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="Votre réponse en allemand…"></div>' : '') +
    '<div id="qdos"></div><div class="q-actions" id="qact"><button class="btn q-reveler" id="qreveler" type="button">Afficher la réponse <small>(espace)</small></button></div>';
  $('qreveler').onclick = reveler;
  if (saisie) $('qsaisie').focus();
}

function reveler() {
  if (!courante || revelee) return;
  revelee = true;
  var saisieEl = $('qsaisie'), verdict = saisieEl ? verifie(courante, saisieEl.value) : '';
  $('qdos').innerHTML = (verdict ? '<div class="q-verdict">' + verdict + '</div>' : '') + dos(courante);
  var etat = store.cards[courante.k] || Plan.nouvelleCarte(), now = Date.now();
  var noms = ['Encore', 'Difficile', 'Bien', 'Facile'], h = '';
  for (var g = 1; g <= 4; g++)
    h += '<button class="btn q-note q-g' + g + '" data-g="' + g + '" type="button"><span>' + noms[g - 1] + ' <small>(' + g + ')</small></span><small>' + Plan.apercu(etat, g, now) + '</small></button>';
  $('qact').innerHTML = h;
  [].forEach.call(document.querySelectorAll('.q-note'), function (b) { b.onclick = function () { donnerNote(parseInt(b.dataset.g, 10)); }; });
}

function donnerNote(g) {
  if (!courante || !revelee) return;
  var now = Date.now(), cpt = compteurs(now), ancien = store.cards[courante.k];
  if (!ancien || ancien.s === 0) cpt.nouvelles++; else cpt.revues++;
  avant = { k: courante.k, etat: ancien ? JSON.parse(JSON.stringify(ancien)) : null, nouv: !ancien || ancien.s === 0 };
  store.cards[courante.k] = Plan.noter(ancien || Plan.nouvelleCarte(), g, now);
  derniere = courante.id;
  ecrire();
  $('qannuler').disabled = false;
  rendre();
}
function annuler() {
  if (!avant) return;
  if (avant.etat) store.cards[avant.k] = avant.etat; else delete store.cards[avant.k];
  var cpt = compteurs(Date.now()); if (avant.nouv) cpt.nouvelles = Math.max(0, cpt.nouvelles - 1); else cpt.revues = Math.max(0, cpt.revues - 1);
  avant = null; $('qannuler').disabled = true; ecrire(); rendre();
}

function reglagesVersUI() {
  var r = store.reglages;
  $('qdir').value = r.dir; $('qnouv').value = r.nouveaux; $('qsaisiecase').checked = !!r.saisie; $('qart').checked = !!r.article;
  $('qt-mot').checked = r.mot; $('qt-derive').checked = r.derive; $('qt-expr').checked = r.expr;
  var lettres = {}; DATA.forEach(function (c) { lettres[c.l] = 1; });
  $('qlettre').innerHTML = '<option value="">Toutes</option>' + Object.keys(lettres).sort().map(function (l) { return '<option>' + l + '</option>'; }).join('');
  $('qlettre').value = r.lettre;
}
function reglagesDepuisUI() {
  var r = store.reglages;
  r.dir = $('qdir').value; r.nouveaux = Math.max(0, parseInt($('qnouv').value, 10) || 0); r.saisie = $('qsaisiecase').checked; r.article = $('qart').checked;
  r.mot = $('qt-mot').checked; r.derive = $('qt-derive').checked; r.expr = $('qt-expr').checked; r.lettre = $('qlettre').value;
  ecrire(); rendre();
}

document.addEventListener('DOMContentLoaded', function () {
  reglagesVersUI();
  ['qdir', 'qnouv', 'qsaisiecase', 'qart', 'qt-mot', 'qt-derive', 'qt-expr', 'qlettre'].forEach(function (i) { $(i).addEventListener('change', reglagesDepuisUI); });
  $('qannuler').onclick = annuler;
  $('qexport').onclick = function () {
    var blob = new Blob([JSON.stringify(store)], { type: 'application/json' }), a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = 'jardin-quiz-progression.json'; a.click();
  };
  $('qimport').onchange = function (ev) {
    var f = ev.target.files[0]; if (!f) return;
    var lec = new FileReader();
    lec.onload = function () {
      try { var v = JSON.parse(lec.result); if (!v.cards) throw 0; store = v; ecrire(); reglagesVersUI(); rendre(); }
      catch (e) { alert('Fichier de progression invalide.'); }
    };
    lec.readAsText(f);
  };
  $('qreset').onclick = function () {
    if (confirm('Effacer toute la progression du quiz ?')) { store.cards = {}; store.daily = { jour: '', nouvelles: 0, revues: 0 }; avant = null; derniere = null; ecrire(); rendre(); }
  };
  document.addEventListener('keydown', function (ev) {
    var enSaisie = ev.target && ev.target.tagName === 'INPUT' && ev.target.type === 'text';
    if (ev.target && /^(SELECT|TEXTAREA)$/.test(ev.target.tagName)) return;
    if (ev.key === 'Enter' || (ev.key === ' ' && !enSaisie)) { if (!revelee && courante) { ev.preventDefault(); reveler(); } return; }
    if (revelee && /^[1-4]$/.test(ev.key) && !enSaisie) donnerNote(parseInt(ev.key, 10));
  });
  rendre();
});
})(typeof self !== 'undefined' ? self : this);
