(function(){
var r=document.documentElement;
try{var t=localStorage.getItem('theme');if(t==='dark'||t==='light')r.dataset.theme=t;}catch(e){}
function eff(){return r.dataset.theme||(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');}
function maj(b){var d=eff()==='dark';b.textContent=d?'\u2600':'\u263E';b.title=d?'Passer au thème clair':'Passer au thème sombre';}
document.addEventListener('DOMContentLoaded',function(){
 var b=document.getElementById('theme');if(!b)return;maj(b);
 b.addEventListener('click',function(){
  var n=eff()==='dark'?'light':'dark';r.dataset.theme=n;
  try{localStorage.setItem('theme',n);}catch(e){}
  maj(b);});
});})();
