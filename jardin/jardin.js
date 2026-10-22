(function(){
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
