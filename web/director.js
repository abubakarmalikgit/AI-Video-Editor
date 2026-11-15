(function(){
const g=id=>document.getElementById(id);
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const pad3=n=>String(n).padStart(3,'0');
const mmss=t=>Math.floor(t/60)+':'+String(Math.floor(t%60)).padStart(2,'0');
const css=`
#p-director .card{margin-top:16px}
#p-director .opts .card{margin-top:0}
#dScript,#dStamps,#dBrief{resize:vertical;font:13px var(--ui)}
#dScript{min-height:90px}#dStamps{min-height:64px}#dBrief{min-height:150px}
#p-director .big{font-size:15px;padding:13px 26px;margin-top:14px}
.dbar{height:8px;border-radius:99px;background:rgba(139,92,246,.15);overflow:hidden;margin:10px 0 4px}
.dbar i{display:block;height:100%;width:0;background:linear-gradient(90deg,#8b5cf6,#22d3ee);transition:width .4s}
.dsteps{display:flex;gap:18px;flex-wrap:wrap;margin-top:12px}
.dst{display:flex;align-items:center;gap:7px;font-size:12.5px;color:var(--mute)}
.dst i{width:9px;height:9px;border-radius:50%;background:#3a3660}
.dst.run{color:#fff}.dst.run i{background:#22d3ee;animation:dpulse 1s infinite}
.dst.done i{background:#34d399}.dst.skip i{background:#6b7280}.dst.err i{background:#f43f5e}
@keyframes dpulse{50%{opacity:.35}}
.dtl{max-height:340px;overflow:auto;border:1px solid var(--line);border-radius:10px;margin-top:12px}
.dtl table{width:100%;border-collapse:collapse;font-size:12.5px}
.dtl td,.dtl th{padding:6px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
.dtl th{position:sticky;top:0;background:var(--panel2)}
.dchat{max-height:280px;overflow:auto;margin-top:12px}
.dq{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}
.dprob{color:#fbbf24;font-size:12.5px;margin-top:6px}`;
const stl=document.createElement('style');stl.textContent=css;document.head.appendChild(stl);

const nav=document.querySelector('nav');
nav.querySelector('button').insertAdjacentHTML('beforebegin','<button data-p="director">&#127916; Director</button>');
document.getElementById('p-about').insertAdjacentHTML('beforebegin',`
<section class="page" id="p-director">
  <h1>Director</h1><p class="sub">Give your material and a brief. The agent builds the timeline, edits, captions and music, then waits for your Render click.</p>
  <div class="opts">
    <div class="card">
      <div class="ct">1. Your material</div>
      <label>Voiceover</label><div class="row"><input id="dAudio" placeholder="Path to the voiceover file"><button class="btn" id="dAudioPick">Pick</button></div>
      <label>Clips folder</label><div class="row"><input id="dClips" placeholder="Folder with 001.mp4, 002.mp4 ..."><button class="btn" id="dClipsPick">Pick</button></div>
      <label>Script</label><textarea id="dScript" placeholder="Paste the script here (plain text, or numbered like 001 : text)"></textarea>
      <div class="row" style="margin-top:8px"><button class="btn" id="dScriptLoad">Load .txt file</button></div>
      <label>Timestamps (optional)</label><textarea id="dStamps" placeholder="0:00-0:06 First sentence&#10;0:06-0:14 Second sentence   (or paste an SRT)"></textarea>
      <div class="row" style="margin-top:8px"><button class="btn" id="dStampsLoad">Load .srt / .txt</button></div>
      <p class="note">If you fill the timestamps, their text replaces the script and speech recognition is skipped.</p>
      <label>Music file or folder (optional)</label><div class="row"><input id="dMusic" placeholder="Used only if the brief asks for music"><button class="btn" id="dMusicFile">File</button><button class="btn" id="dMusicFolder">Folder</button></div>
      <div class="row" style="margin-top:12px"><div><label>Quality</label><select id="dQuality"><option value="max">Maximum</option><option value="high">High (recommended)</option><option value="balanced">Balanced (faster)</option></select></div>
      <div><label>Resolution</label><select id="dRes"><option value="original">Original</option><option value="1080p">1080p</option><option value="720p">720p</option></select></div></div>
    </div>
    <div class="card">
      <div class="ct">2. Your brief</div>
      <textarea id="dBrief" placeholder="Describe the edit. Example: Calm documentary. Hard cuts, soft dissolve only when the topic changes. White captions at the bottom. Soft music at 10%."></textarea>
      <div class="dq" id="dQ"></div>
      <div class="chk" style="margin-top:12px"><input type="checkbox" id="dAuto"><span>Render automatically after planning</span></div>
      <div class="row"><button class="btn primary big" id="dPlan">&#10024; Plan everything</button><button class="btn danger" id="dStop" style="display:none">Stop</button></div>
      <p class="note">Leave the brief empty for hard cuts, no captions and no music.</p>
    </div>
  </div>
  <div class="card" id="dProg" style="display:none">
    <div class="ct">Progress</div><div class="dsteps" id="dSteps"></div>
    <div class="dbar" id="dBar"><i></i></div><div class="info" id="dStage" style="margin:0"></div>
  </div>
  <div class="card" id="dSum" style="display:none">
    <div class="ct">3. Plan summary</div>
    <div id="dPills"></div><div id="dProb"></div><div class="dtl" id="dTl"></div>
    <div class="row" style="margin-top:14px"><button class="btn primary" id="dRender">&#9654; Render video</button><button class="btn" id="dOpen" style="display:none">Open output folder</button></div>
    <div class="ct" style="margin-top:22px">Change anything</div>
    <div class="dchat" id="dChat"></div>
    <div class="row" style="margin-top:10px"><textarea id="dIn" style="min-height:52px;height:52px;resize:none;font:14px var(--ui)" placeholder="Example: make captions bigger, no music in the last line, lines 5 to 9 use calmer clips"></textarea><button class="btn primary" id="dSend">Send</button><button class="btn" id="dUndo">Undo</button></div>
    <p class="note">Undo covers clip and transition edits. Change captions and music on the Captions &amp; Music page.</p>
  </div>
</section>`);

const D={busy:false,out:'',projectDirty:false,mainFingerprint:''};
const BRIEFS=[
 ['Calm documentary','Calm documentary style. Mostly hard cuts, a soft dissolve only when the topic changes. White captions at the bottom, 5 words each. Soft background music at 10%, lowered under the voice.'],
 ['Fast and energetic','Fast and energetic style. Mostly hard cuts with a quick slide or wipe where the topic changes. Bold captions in Anton in the middle, 3 words each, capital letters. No music.'],
 ['Clean, no extras','Hard cuts only. No captions. No music.']];
BRIEFS.forEach(b=>{const e=document.createElement('button');e.className='btn';e.textContent=b[0];
  e.onclick=()=>{g('dBrief').value=b[1];saveSoon();};g('dQ').appendChild(e);});

function readForm(){return{audio:g('dAudio').value.trim(),clips_dir:g('dClips').value.trim(),script:g('dScript').value,
  stamps:g('dStamps').value,brief:g('dBrief').value,quality:g('dQuality').value,res:g('dRes').value,auto_render:g('dAuto').checked};}
function projectFingerprint(b){return [b.audio||'',b.clips_dir||'',b.script||''].join('\n');}
function makeOpts(){
  let base={};try{base=Object.assign({},opts()||{});}catch(e){}
  const f=readForm();
  // Prefer the currently configured main Project page unless the user deliberately
  // edits the Director's own source fields. A newly changed main-page project takes priority.
  const mainFingerprint=projectFingerprint(base);
  const mainChanged=!!D.mainFingerprint&&mainFingerprint!==D.mainFingerprint;
  const useMain=!!(base.audio&&base.clips_dir&&base.script)&&(!D.projectDirty||mainChanged);
  if(mainChanged)D.projectDirty=false;
  D.mainFingerprint=mainFingerprint;
  const chosen=useMain?base:f;
  if(useMain){g('dAudio').value=base.audio;g('dClips').value=base.clips_dir;g('dScript').value=base.script;g('dStamps').value='';}
  const o=Object.assign(base,{quality:f.quality,res:f.res});
  if(chosen.audio)o.audio=chosen.audio;if(chosen.clips_dir)o.clips_dir=chosen.clips_dir;
  if(!useMain&&f.stamps.trim()){o.script=f.stamps;o.use_stamps=true;}else{o.script=chosen.script||'';o.use_stamps=false;}
  return o;
}
let ft=null;
function saveSoon(){clearTimeout(ft);ft=setTimeout(()=>{try{api().director_save(readForm());}catch(e){}},400);}
['dAudio','dClips','dScript','dStamps'].forEach(id=>{
  g(id).addEventListener('input',()=>{D.projectDirty=true;saveSoon();});
  g(id).addEventListener('change',()=>{D.projectDirty=true;saveSoon();});
});
['dBrief','dQuality','dRes','dAuto'].forEach(id=>{
  g(id).addEventListener('input',saveSoon);g(id).addEventListener('change',saveSoon);
});

async function loadForm(){
  const d=await api().director_load();
  g('dAudio').value=d.audio||'';g('dClips').value=d.clips_dir||'';g('dScript').value=d.script||'';
  g('dStamps').value=d.stamps||'';g('dBrief').value=d.brief||'';g('dQuality').value=d.quality||'high';
  g('dRes').value=d.res||'original';g('dAuto').checked=!!d.auto_render;
  D.projectDirty=false;
  try{const b=opts();D.mainFingerprint=projectFingerprint(b);if(b.audio&&b.clips_dir&&b.script){
    g('dAudio').value=b.audio;g('dClips').value=b.clips_dir;g('dScript').value=b.script;g('dStamps').value='';
  }}catch(e){}
  const fr=await api().finish_get();g('dMusic').value=fr.settings.music.path||'';
}

g('dAudioPick').onclick=async()=>{const p=await api().pick_audio();if(p){g('dAudio').value=p;D.projectDirty=true;saveSoon();}};
g('dClipsPick').onclick=async()=>{const p=await api().pick_folder();if(p){g('dClips').value=p;D.projectDirty=true;saveSoon();}};
g('dScriptLoad').onclick=async()=>{const p=await api().pick_text();if(p){g('dScript').value=await api().read_text(p);D.projectDirty=true;saveSoon();}};
g('dStampsLoad').onclick=async()=>{const p=await api().director_pick_stamps();if(p){g('dStamps').value=await api().read_text(p);D.projectDirty=true;saveSoon();}};

async function setMusic(p){if(p){g('dMusic').value=p;await api().finish_set({music:{path:p}});toast('Music source saved','ok');}}
g('dMusicFile').onclick=async()=>setMusic(await api().pick_audio());
g('dMusicFolder').onclick=async()=>setMusic(await api().pick_folder());
g('dMusic').onchange=()=>api().finish_set({music:{path:g('dMusic').value.trim()}});

nav.querySelector('button[data-p="director"]').onclick=function(){
  nav.querySelectorAll('button').forEach(x=>x.classList.remove('on'));this.classList.add('on');
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('on'));g('p-director').classList.add('on');
};
nav.querySelectorAll('button').forEach(x=>x.classList.remove('on'));
nav.querySelector('button[data-p="director"]').classList.add('on');
document.querySelectorAll('.page').forEach(p=>p.classList.remove('on'));g('p-director').classList.add('on');
const wt=setInterval(()=>{if(typeof READY!=='undefined'&&READY){clearInterval(wt);loadForm();}},300);

const NAMES=['Check clips','Build timeline','AI direction','Plan ready'];
function drawSteps(st){g('dSteps').innerHTML=NAMES.map((n,i)=>'<div class="dst '+(['','run','done','skip','err'][st[i]]||'')+'"><i></i>'+n+'</div>').join('');}
function setBar(stage,pct){g('dStage').textContent=(stage||'')+' '+Math.round(pct||0)+'%';g('dBar').firstElementChild.style.width=(pct||0)+'%';}
function lock(b){['dPlan','dRender','dSend','dUndo'].forEach(i=>g(i).disabled=b);g('dStop').style.display=b?'':'none';}
async function waitIdle(){for(;;){const s=await api().get_state(999999);setBar(s.stage,s.progress);if(!s.running)return s;await sleep(700);}}

function say(who,text,r){
  const d=document.createElement('div');d.className='msg '+who;d.textContent=text;
  if(r){
    if(r.changes&&r.changes.length){const u=document.createElement('ul');
      r.changes.forEach(c=>{const li=document.createElement('li');li.textContent=c;u.appendChild(li);});d.appendChild(u);}
    if(r.skipped&&r.skipped.length){const s=document.createElement('div');s.className='sk';s.textContent='Skipped: '+r.skipped.join(' | ');d.appendChild(s);}
  }
  const c=g('dChat');c.appendChild(d);c.scrollTop=c.scrollHeight;
}
async function rebuild(o){
  g('dProg').style.display='';
  const r=await api().start(o,false);if(!r.ok)throw new Error(r.error);
  const s=await waitIdle();
  if(s.error)throw new Error(s.error);
  if(!s.result)throw new Error(s.stage==='Cancelled'?'Stopped':'Timeline failed - see Logs');
  return s.result;
}
async function showSummary(res,o){
  const fr=await api().finish_get(),inf=await api().agent_info(o);
  const c=fr.settings.captions,m=fr.settings.music,cf=res.cfg||{};
  const tr=res.transitions||[],by={};tr.forEach(t=>by[t.after_line]=t);
  const sourceVideos=Number(res.source_videos||0), sourceImages=Number(res.source_images||0);
  const scriptLines=Number(res.script_lines||res.lines.length);
  const pieces=Number(res.clip_pieces||res.lines.reduce((n,l)=>n+(l.pieces||[]).length,0));
  let h='<span class="pill acc">'+sourceVideos+' source videos · '+sourceImages+' images</span><span class="pill acc">'+scriptLines+' script rows</span>'+
    '<span class="pill acc">'+pieces+' timeline pieces</span><span class="pill acc">'+mmss(res.duration)+'</span>'+
    '<span class="pill acc">'+cf.W+'x'+cf.H+' @ '+cf.fps+' fps</span><span class="pill acc">'+tr.length+' transitions planned</span>';
  h+=c.on?'<span class="pill ok">Captions ON: '+esc(c.font)+'</span>':'<span class="pill">Captions OFF</span>';
  if(m.on)h+=fr.track?'<span class="pill ok">Music ON: '+esc(fr.track)+' at '+Math.round(m.volume)+'%</span>':'<span class="pill warn">Music ON but no file chosen</span>';
  else h+='<span class="pill">Music OFF</span>';
  if(inf.style)h+='<br><span class="pill ok" style="margin-top:8px">style: '+esc(inf.style.slice(0,90))+'</span>';
  g('dPills').innerHTML=h;
  g('dProb').innerHTML=(res.problems||[]).map(p=>'<div class="dprob">&#9888; '+esc(p)+'</div>').join('');
  g('dTl').innerHTML='<table><tr><th>Line</th><th>Time</th><th>Clips</th><th>Text</th></tr>'+res.lines.map(l=>{
    const t=by[l.i];return '<tr><td>'+l.i+'</td><td>'+mmss(l.start)+'</td><td>'+l.pieces.map(p=>pad3(p.num)).join(', ')+
      (t?' <span class="chip">&rarr; '+esc(t.type)+' '+t.dur+'s</span>':'')+'</td><td>'+esc((l.text||'').slice(0,90))+'</td></tr>';}).join('')+'</table>';
  g('dSum').style.display='';
}

async function plan(){
  if(D.busy)return;const f=readForm();
  if(!f.audio){toast('Choose the voiceover first','warn');return;}
  if(!f.clips_dir){toast('Choose the clips folder first','warn');return;}
  if(!f.script.trim()&&!f.stamps.trim()){toast('Add a script or timestamps first','warn');return;}
  D.busy=true;lock(true);g('dSum').style.display='none';g('dOpen').style.display='none';g('dChat').innerHTML='';
  const st=[0,0,0,0];drawSteps(st);g('dProg').style.display='';setBar('Starting',0);
  let result=null;
  try{
    await api().director_save(f);const o=makeOpts();
    if(f.stamps.trim()){const si=await api().director_stamps_info(f.stamps);
      if(!si.count)throw new Error('Could not read the timestamps. Use lines like 0:05-0:12 text, or an SRT file.');}
    st[0]=1;drawSteps(st);
    const ins=await api().inspect(Object.assign({},o,{script:f.stamps.trim()?'':o.script}),true);
    const cl=ins&&ins.clips;
    if(!cl||!(cl.videos+cl.images))throw new Error('No usable clips found in that folder');
    const manual=!!(ins.script&&ins.script.mode==='manual');
    const needAI=!!f.brief.trim()||!manual;
    if(needAI){
      const items=await api().get_library(),a=await api().ai_status();
      if(a.has_key&&a.enabled&&items.some(i=>!i.desc)){
        toast('Describing your clips with AI first (this can take a few minutes)...');
        const r=await api().start_scan(o);if(!r.ok)throw new Error(r.error);
        const s=await waitIdle();
        if(s.stage==='Cancelled')throw new Error('Stopped');
        if(s.scan_error)toast(s.scan_error,'warn');
      }
    }
    st[0]=2;st[1]=1;drawSteps(st);
    result=await rebuild(o);st[1]=2;
    if(f.brief.trim()){
      st[2]=1;drawSteps(st);setBar('AI is reading your brief',100);
      const ans=await api().director_chat(f.brief,o);
      say('me',f.brief);say('bot',ans.reply||'',ans);
      if(ans.ok&&ans.changed){result=await rebuild(o);}
      st[2]=ans.ok?2:4;
    }else st[2]=3;
    st[3]=2;drawSteps(st);setBar('Plan ready',100);
    await showSummary(result,o);
    if(f.auto_render)await render();
  }catch(e){
    const i=st.indexOf(1);if(i>=0)st[i]=4;drawSteps(st);
    toast(String(e.message||e),'err');
  }finally{D.busy=false;lock(false);}
}
async function render(){
  g('dProg').style.display='';
  const r=await api().start(makeOpts(),true);if(!r.ok){toast(r.error,'err');return;}
  const s=await waitIdle();
  if(s.error){toast(s.error,'err');return;}
  if(s.result&&s.result.output){D.out=s.result.output;g('dOpen').style.display='';
    say('bot','Your video is ready: '+s.result.output);toast('Video ready','ok');
    (s.result.problems||[]).forEach(p=>say('bot','Note: '+p));}
  else if(s.stage==='Cancelled')toast('Stopped','warn');
}
g('dPlan').onclick=plan;
g('dStop').onclick=()=>api().cancel();
g('dRender').onclick=async()=>{if(D.busy)return;D.busy=true;lock(true);try{await render();}finally{D.busy=false;lock(false);}};
g('dOpen').onclick=()=>api().open_output(D.out);

async function send(){
  const m=g('dIn').value.trim();if(!m||D.busy)return;
  D.busy=true;lock(true);g('dIn').value='';say('me',m);
  try{
    const o=makeOpts();const a=await api().director_chat(m,o);say('bot',a.reply||'...',a);
    if(a.changed){const res=await rebuild(o);await showSummary(res,o);}
    else if(a.ok&&a.changes&&a.changes.length){const res=await rebuild(o);await showSummary(res,o);}
  }catch(e){say('bot','Problem: '+(e.message||e));}
  finally{D.busy=false;lock(false);}
}
g('dSend').onclick=send;
g('dIn').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send();}});
g('dUndo').onclick=async()=>{
  if(D.busy)return;const r=await api().agent_undo(makeOpts());
  if(!r.ok){toast('Nothing to undo','warn');return;}
  say('bot','Undone: '+r.label);D.busy=true;lock(true);
  try{const o=makeOpts();const res=await rebuild(o);await showSummary(res,o);}
  catch(e){toast(String(e.message||e),'err');}finally{D.busy=false;lock(false);}
};
})();
