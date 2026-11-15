(function(){
const css=`
#p-finish input[type=range]{padding:0;height:6px;accent-color:#8b5cf6}
#p-finish input[type=color]{width:56px;height:38px;padding:2px;cursor:pointer}
#p-finish .rv{display:flex;align-items:center;gap:10px}
#p-finish .rv span{font:12px var(--mono);color:#22d3ee;min-width:48px}
#fcImg{width:100%;border-radius:10px;margin-top:12px;border:1px solid var(--line);display:none}
#p-finish .dim{opacity:.45;pointer-events:none}`;
const st=document.createElement('style');st.textContent=css;document.head.appendChild(st);

const nav=document.querySelector('nav');
nav.querySelector('button[data-p="about"]').insertAdjacentHTML('beforebegin','<button data-p="finish">&#9835; Captions &amp; Music</button>');
document.getElementById('p-about').insertAdjacentHTML('beforebegin',`
<section class="page" id="p-finish">
  <h1>Captions &amp; Music</h1><p class="sub">Both are OFF until you switch them on. They are added when you press Render.</p>
  <div class="opts">
    <div class="card" id="fcCard">
      <div class="ct">Captions</div>
      <div class="chk"><input type="checkbox" id="fcOn"><span>Burn captions into the video</span></div>
      <div id="fcBody">
        <label>Font</label><select id="fcFont"></select>
        <label>Size</label><div class="rv"><input type="range" id="fcSize" min="3" max="9" step="0.5"><span id="fcSizeV"></span></div>
        <label>Words per caption</label><div class="rv"><input type="range" id="fcWords" min="2" max="10" step="1"><span id="fcWordsV"></span></div>
        <label>Position</label><select id="fcPos"><option value="bottom">Bottom</option><option value="middle">Middle</option><option value="top">Top</option></select>
        <div class="row" style="margin-top:12px"><div><label>Text colour</label><input type="color" id="fcColor"></div><div><label>Outline colour</label><input type="color" id="fcOutline"></div></div>
        <div class="chk"><input type="checkbox" id="fcUpper"><span>CAPITAL LETTERS</span></div>
        <div class="chk"><input type="checkbox" id="fcBox"><span>Dark box behind the text</span></div>
        <div class="row" style="margin-top:12px"><button class="btn" id="fcPrev">Preview captions</button></div>
        <img id="fcImg">
      </div>
      <p class="note">Captions cost one extra encoding pass at the end of a render. A .srt file is always saved too.</p>
    </div>
    <div class="card" id="fmCard">
      <div class="ct">Background music</div>
      <div class="chk"><input type="checkbox" id="fmOn"><span>Add background music</span></div>
      <div id="fmBody">
        <label>Music file or folder</label><input id="fmPath" placeholder="Pick a file or a folder of songs">
        <div class="row" style="margin-top:10px"><button class="btn" id="fmFile">Pick file</button><button class="btn" id="fmFolder">Pick folder</button></div>
        <div class="info" id="fmTrack" style="margin-top:10px"></div>
        <label>Volume</label><div class="rv"><input type="range" id="fmVol" min="0" max="50" step="1"><span id="fmVolV"></span></div>
        <label>Fade in (seconds)</label><div class="rv"><input type="range" id="fmFi" min="0" max="8" step="0.5"><span id="fmFiV"></span></div>
        <label>Fade out (seconds)</label><div class="rv"><input type="range" id="fmFo" min="0" max="10" step="0.5"><span id="fmFoV"></span></div>
        <div class="chk"><input type="checkbox" id="fmDuck"><span>Lower the music while the voice speaks</span></div>
      </div>
      <p class="note">With a folder, the first song is used. The music loops if it is shorter than your video. Free songs: YouTube Audio Library or Pixabay Music.</p>
    </div>
  </div>
</section>`);

const g=id=>document.getElementById(id);
nav.querySelector('button[data-p="finish"]').onclick=function(){
  nav.querySelectorAll('button').forEach(x=>x.classList.remove('on'));this.classList.add('on');
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('on'));
  g('p-finish').classList.add('on');load();
};

let loading=false,tm=null;
function vals(){
  g('fcSizeV').textContent=g('fcSize').value+'%';g('fcWordsV').textContent=g('fcWords').value;
  g('fmVolV').textContent=g('fmVol').value+'%';g('fmFiV').textContent=g('fmFi').value+'s';g('fmFoV').textContent=g('fmFo').value+'s';
  g('fcBody').classList.toggle('dim',!g('fcOn').checked);g('fmBody').classList.toggle('dim',!g('fmOn').checked);
}
function collect(){return{
  captions:{on:g('fcOn').checked,font:g('fcFont').value,size:+g('fcSize').value,words:+g('fcWords').value,pos:g('fcPos').value,
    color:g('fcColor').value,outline:g('fcOutline').value,upper:g('fcUpper').checked,box:g('fcBox').checked},
  music:{on:g('fmOn').checked,path:g('fmPath').value.trim(),volume:+g('fmVol').value,fade_in:+g('fmFi').value,
    fade_out:+g('fmFo').value,duck:g('fmDuck').checked}};}
function saveNow(){clearTimeout(tm);tm=setTimeout(async()=>{
  if(loading)return;const r=await api().finish_set(collect());
  const t=await api().finish_get();g('fmTrack').textContent=t.track?('Will use: '+t.track):'';},350);}
async function load(){
  if(typeof READY==='undefined'||!READY)return;
  loading=true;const r=await api().finish_get(),c=r.settings.captions,m=r.settings.music;
  g('fcFont').innerHTML=r.fonts.map(f=>'<option>'+esc(f)+'</option>').join('');
  g('fcOn').checked=c.on;g('fcFont').value=c.font;g('fcSize').value=c.size;g('fcWords').value=c.words;g('fcPos').value=c.pos;
  g('fcColor').value=c.color;g('fcOutline').value=c.outline;g('fcUpper').checked=c.upper;g('fcBox').checked=c.box;
  g('fmOn').checked=m.on;g('fmPath').value=m.path;g('fmVol').value=m.volume;g('fmFi').value=m.fade_in;g('fmFo').value=m.fade_out;
  g('fmDuck').checked=m.duck;g('fmTrack').textContent=r.track?('Will use: '+r.track):'';
  vals();loading=false;
}
['fcOn','fcFont','fcSize','fcWords','fcPos','fcColor','fcOutline','fcUpper','fcBox','fmOn','fmPath','fmVol','fmFi','fmFo','fmDuck']
  .forEach(id=>{const e=g(id);e.addEventListener('input',()=>{vals();saveNow();});e.addEventListener('change',()=>{vals();saveNow();});});
g('fmFile').onclick=async()=>{const p=await api().pick_audio();if(p){g('fmPath').value=p;g('fmOn').checked=true;vals();saveNow();}};
g('fmFolder').onclick=async()=>{const p=await api().pick_folder();if(p){g('fmPath').value=p;g('fmOn').checked=true;vals();saveNow();}};
g('fcPrev').onclick=async()=>{
  await api().finish_set(collect());
  g('fcPrev').disabled=true;toast('Making the preview (the first time it downloads the font)...');
  const r=await api().finish_preview();g('fcPrev').disabled=false;
  if(r.ok){const im=g('fcImg');im.style.display='block';im.src='file:///'+encodeURI(r.path.replace(/\\/g,'/'))+'?t='+Date.now();}
  else toast('Preview failed: '+r.error,'err');
};
})();
