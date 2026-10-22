(function(){
var FONTS=[['Antiqua',"Georgia,'Times New Roman',serif"],['Kurrent',"'WiegelKurrent',serif"],['Fraktur',"'UnifrakturMaguntia',serif"],['Sütterlin',"'GlSuetterlin',serif"]];
function lire(k){try{return localStorage.getItem(k);}catch(e){return null;}}
function ecrire(k,v){try{localStorage.setItem(k,v);}catch(e){}}
function police(i){i=Math.max(0,Math.min(FONTS.length-1,parseInt(i,10)||0));
 document.documentElement.style.setProperty('--de-font',FONTS[i][1]);
 var n=document.getElementById('fontName');if(n)n.textContent=FONTS[i][0];
 var s=document.getElementById('fontSlider');if(s)s.value=i;ecrire('jardinFont',i);}
document.addEventListener('DOMContentLoaded',function(){
 police(lire('jardinFont')||0);
 var s=document.getElementById('fontSlider');if(s)s.addEventListener('input',function(){police(s.value);});
 var toc=document.querySelector('.toc'),tb=document.getElementById('toggleToc');
 if(tb)tb.addEventListener('click',function(){toc.classList.toggle('cache');tb.textContent=toc.classList.contains('cache')?'\u2b07':'\u2b06';});
 var q=document.getElementById('q');
 function norm(x){return x.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');}
 if(q)q.addEventListener('input',function(){var v=norm(q.value.trim());
  document.querySelectorAll('section.lettre').forEach(function(sec){var vis=0;
   sec.querySelectorAll(':scope>ul>li').forEach(function(li){var ok=!v||norm(li.textContent).indexOf(v)>=0;li.classList.toggle('masque',!ok);if(ok)vis++;});
   sec.classList.toggle('masque',!vis);});});
});})();
