(function(){
const P2={items:[],lastScan:null};
const nav=document.querySelector('nav');
nav.querySelectorAll('button.soon').forEach(b=>{if(/Library/.test(b.textContent))b.remove();});
nav.querySelector('button[data-p="about"]').insertAdjacentHTML('beforebegin',
  '<button data-p="library">&#9635; Library</button><button data-p="settings">&#10022; AI Settings</button>');

document.getElementById('p-about').insertAdjacentHTML('beforebegin',`
<section class="page" id="p-library">
  <h1>Library</h1><p class="sub">Your clips with thumbnails and AI descriptions. Scan once, the result is saved.</p>
  <div class="card">
    <div class="row"><button class="btn primary" id="bScan">Scan clips</button><input id="libQ" placeholder="Search by number, word or tag..."></div>
    <div class="info" id="libCount">Choose the clips folder on the Project page, then press Scan clips.</div>
  </div>
  <div class="lgrid" id="libGrid"></div>
</section>
<section class="page" id="p-settings">
  <h1>AI Settings</h1><p class="sub">Connect Gemini once. The key is stored on this PC only.</p>
  <div class="opts">
    <div class="card">
      <div class="ct">Gemini key</div>
      <div id="aiState"></div>
      <label>Paste API key</label>
      <input id="aiKey" type="password" placeholder="Paste your key here (only needed once)" autocomplete="off">
      <div class="row" style="margin-top:12px"><button class="btn primary" id="aiSave">Save and test</button><button class="btn danger" id="aiRemove">Remove key</button></div>
      <ol class="steps"><li>Open aistudio.google.com and sign in with Google</li><li>Click <b>Get API key</b>, then <b>Create API key</b></li><li>Copy it, paste it above, press Save and test</li></ol>
      <p class="note">Never share your key with anyone, including in chats.</p>
    </div>
    <div class="card">
      <div class="ct">Behaviour</div>
      <div class="chk"><input type="checkbox" id="aiOn"><span>Use Cloud AI (Gemini)</span></div>
      <p class="note">When ON, the clip scan sends 3 small frames of each clip to Google, and clip matching sends your script lines as text. Turn it OFF to keep everything on your PC (manual numbering still works).</p>
      <label>Model</label>
      <select id="aiModel"><option value="gemini-3.6-flash">Gemini 3.6 Flash (fixed)</option></select>
      <p class="note">MalixAris uses Gemini 3.6 Flash only. Temporary quota limits are handled with bounded retries; the app will not silently switch models.</p>
    </div>
  </div>
</section>`);

nav.querySelectorAll('button[data-p="library"],button[data-p="settings"]').forEach(b=>b.onclick=()=>{
  nav.querySelectorAll('button').forEach(x=>x.classList.remove('on'));b.classList.add('on');
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('on'));
  document.getElementById('p-'+b.dataset.p).classList.add('on');
  if(b.dataset.p==='library')loadLibrary();else loadAI();
});

async function loadAI(){
  const s=await api().ai_status();
  $('#aiState').innerHTML=(s.has_key?'<span class="pill ok">Key saved</span>':'<span class="pill warn">No key yet</span>')+
    (s.active_model?'<span class="pill acc">model: '+esc(s.active_model)+'</span>':'');
  $('#aiOn').checked=!!s.enabled;
  $('#aiModel').value='gemini-3.6-flash';
}
$('#aiSave').onclick=async()=>{
  const k=$('#aiKey').value.trim();
  $('#aiSave').disabled=true;toast('Testing the connection (up to 1 minute)...');
  if(k){await api().ai_save_key(k);$('#aiKey').value='';}
  const r=await api().ai_test();$('#aiSave').disabled=false;
  if(r.ok)toast('Gemini connected: '+r.model,'ok');else toast(r.error,'err');
  loadAI();
};
$('#aiRemove').onclick=async()=>{await api().ai_remove_key();toast('Key removed');loadAI();};
$('#aiOn').onchange=()=>api().ai_set({enabled:$('#aiOn').checked});
$('#aiModel').onchange=()=>api().ai_set({model:'gemini-3.6-flash'});

async function loadLibrary(){
  if(typeof READY==='undefined'||!READY)return;
  P2.items=await api().get_library();drawLib();
}
function drawLib(){
  const q=($('#libQ').value||'').toLowerCase();
  const items=P2.items.filter(i=>!q||(pad(i.num)+' '+(i.desc||'')+' '+(i.tags||[]).join(' ')).toLowerCase().includes(q));
  $('#libGrid').innerHTML=items.map(i=>'<div class="lc"><div class="th">'+
    (i.thumb?'<img loading="lazy" src="file:///'+encodeURI(i.thumb.replace(/\\/g,'/'))+'">':'')+
    '<span class="nb">'+pad(i.num)+(i.kind==='image'?' IMG':'')+'</span></div><div class="ds">'+esc(i.desc||'Not described yet')+
    '</div><div>'+(i.tags||[]).map(t=>'<span class="chip">'+esc(t)+'</span>').join('')+'</div></div>').join('');
  const d=P2.items.filter(i=>i.desc).length;
  if(P2.items.length)$('#libCount').textContent=P2.items.length+' clips, '+d+' described by AI';
}
$('#libQ').oninput=drawLib;
$('#bScan').onclick=async()=>{
  const o=opts();if(!o.clips_dir){toast('Choose the clips folder on the Project page first','warn');return;}
  const r=await api().start_scan(o);
  if(!r.ok)toast(r.error,'err');else toast('Scan started - watch the progress bar at the bottom','ok');
};

setInterval(async()=>{
  if(typeof READY==='undefined'||!READY)return;
  try{
    const s=await api().get_state(999999);
    if(P2.lastScan===null){P2.lastScan=s.scan_done;return;}
    if(s.scan_done!==P2.lastScan){
      P2.lastScan=s.scan_done;
      if(s.scan_error)toast(s.scan_error,'err');
      else if(s.scan_summary){const m=s.scan_summary;
        toast(m.ai?('Scan finished: '+m.described+' of '+m.total+' clips described'+(m.failed?' ('+m.failed+' requests failed, see Logs)':'')):
          'Thumbnails ready. Add a Gemini key in AI Settings to get descriptions.',m.failed?'warn':'ok');}
      loadLibrary();
    }
  }catch(e){}
},1500);
})();
