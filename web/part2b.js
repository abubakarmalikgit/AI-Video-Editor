(function(){
const css=`
.agrid{display:grid;grid-template-columns:1.6fr 1fr;gap:16px}
.chat{height:calc(100vh - 340px);min-height:260px;overflow:auto;padding:4px 6px 10px}
.msg{max-width:88%;padding:10px 14px;border-radius:14px;margin:8px 0;white-space:pre-wrap;line-height:1.55}
.msg.me{margin-left:auto;background:linear-gradient(135deg,#7c5cff,#5b8cff);color:#fff}
.msg.bot{background:var(--panel2);border:1px solid var(--line)}
.msg ul{margin:8px 0 0 18px;color:var(--cy);font:12px/1.7 var(--mono)}
.msg .sk{margin-top:8px;color:var(--warn);font-size:12px}
.msg .btn{margin-top:10px}
#chatIn{min-height:56px;height:56px;resize:none;font:14px var(--ui)}
.qs{display:flex;flex-direction:column;gap:8px}
.qs .btn{text-align:left;white-space:normal}
.ex{color:var(--mute);font-size:12px;line-height:1.8;margin-top:6px}
.ex code{font:12px var(--mono)}`;
const st=document.createElement('style');st.textContent=css;document.head.appendChild(st);

const nav=document.querySelector('nav');
nav.querySelectorAll('button.soon').forEach(b=>{if(/Agent/.test(b.textContent))b.remove();});
nav.querySelector('button[data-p="library"]').insertAdjacentHTML('beforebegin','<button data-p="agent">&#10024; AI Agent</button>');

document.getElementById('p-about').insertAdjacentHTML('beforebegin',`
<section class="page" id="p-agent">
  <h1>AI Agent</h1><p class="sub">Tell the agent what to change. It edits only what you name, and you can undo.</p>
  <div class="agrid">
    <div class="card">
      <div class="chat" id="chat"></div>
      <div class="row" style="margin-top:10px"><textarea id="chatIn" placeholder="Example: lines 10 to 15 use calmer clips   (Enter to send, Shift+Enter for a new line)"></textarea><button class="btn primary" id="chatSend">Send</button></div>
    </div>
    <div>
      <div class="card"><div class="ct">Editing styles</div><div class="qs" id="qs"></div></div>
      <div class="card" style="margin-top:16px"><div class="ct">Your edits</div><div id="agInfo" class="info" style="margin:0 0 10px"></div>
        <div class="row"><button class="btn" id="agUndo">Undo last edit</button><button class="btn danger" id="agReset">Reset all</button></div></div>
      <div class="card" style="margin-top:16px"><div class="ct">Things you can say</div><div class="ex">
        <code>Line 7 use clip 112 and 113</code><br><code>Make line 12 slower</code><br><code>Replace clip 045 everywhere</code><br>
        <code>From 0:30 to 0:45 use calmer clips</code><br><code>Remove all transitions in lines 30 to 40</code><br><code>Make the cut after line 20 a dip to black</code></div></div>
    </div>
  </div>
</section>`);

nav.querySelector('button[data-p="agent"]').onclick=function(){
  nav.querySelectorAll('button').forEach(x=>x.classList.remove('on'));this.classList.add('on');
  document.querySelectorAll('.page').forEach(p=>p.classList.remove('on'));
  document.getElementById('p-agent').classList.add('on');refreshInfo();
};

const PRESETS=[
  ['Pure hard cuts','Use pure hard cuts everywhere. Remove all transitions.'],
  ['Fast and energetic','Editing style: fast and energetic. Mostly hard cuts, with a quick slide or wipe only where the topic changes. Apply it to the whole video.'],
  ['Calm documentary','Editing style: calm documentary. Hard cuts mostly, with a soft dissolve only at scene changes. Apply it to the whole video.'],
  ['Cinematic','Editing style: cinematic. Dip to black on big topic changes, hard cuts everywhere else. Apply it to the whole video.']];
PRESETS.forEach(p=>{const b=document.createElement('button');b.className='btn';b.textContent=p[0];
  b.onclick=()=>{$('#chatIn').value=p[1];$('#chatIn').focus();};$('#qs').appendChild(b);});

const chat=$('#chat');let busy=false;
function addMsg(who,text,r,orig){
  const d=document.createElement('div');d.className='msg '+who;d.textContent=text;
  if(r){
    if(r.changes&&r.changes.length){const u=document.createElement('ul');
      r.changes.forEach(c=>{const li=document.createElement('li');li.textContent=c;u.appendChild(li);});d.appendChild(u);}
    if(r.skipped&&r.skipped.length){const s=document.createElement('div');s.className='sk';s.textContent='Skipped: '+r.skipped.join(' | ');d.appendChild(s);}
    if(r.propose_script){const b=document.createElement('button');b.className='btn primary';b.textContent='Use this as my script';
      b.onclick=()=>{$('#script').value=orig;saveSoon();inspectProject(false);toast('Script replaced. Press Build timeline.','ok');b.disabled=true;};d.appendChild(b);}
  }
  chat.appendChild(d);chat.scrollTop=chat.scrollHeight;return d;
}
addMsg('bot','Hi! I am your editing agent. First press Build timeline on the Project page, then tell me what to change, or pick an editing style on the right. You can also paste a script here and I will offer to use it.');

async function send(){
  const message=$('#chatIn').value.trim();if(!message||busy)return;
  busy=true;$('#chatSend').disabled=true;$('#chatIn').value='';
  addMsg('me',message);const wait=addMsg('bot','Thinking...');
  let r;try{r=await api().agent_chat(message,opts());}catch(e){r={ok:false,reply:String(e)};}
  wait.remove();addMsg('bot',r.reply||'...',r,message);
  busy=false;$('#chatSend').disabled=false;refreshInfo();
  if(r.changed){toast('Edit applied. Rebuilding the timeline...','ok');start(false);}
}
$('#chatSend').onclick=send;
$('#chatIn').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send();}});

async function refreshInfo(){
  if(typeof READY==='undefined'||!READY)return;
  const i=await api().agent_info(opts());
  $('#agInfo').innerHTML='<span class="pill acc">'+i.edited_lines+' lines pinned</span><span class="pill acc">'+i.transitions+' transitions</span>'+
    (i.style?'<br><span class="pill ok">style: '+esc(i.style.slice(0,60))+'</span>':'')+
    (i.history.length?'<br><span style="font-size:12px">Last: '+esc(i.history[i.history.length-1])+'</span>':'');
}
$('#agUndo').onclick=async()=>{
  const r=await api().agent_undo(opts());
  if(r.ok){addMsg('bot','Undone: '+r.label);toast('Undone. Rebuilding...','ok');start(false);}else toast('Nothing to undo','warn');
  refreshInfo();
};
$('#agReset').onclick=async()=>{
  if(!confirm('Remove all agent edits (clip changes and transitions)? You can still press Undo.'))return;
  await api().agent_reset(opts());addMsg('bot','All edits cleared.');refreshInfo();start(false);
};

const oldRT=window.renderTimeline;
if(typeof oldRT==='function')window.renderTimeline=function(r){
  oldRT(r);
  if(!r.lines||!r.lines.length)return;
  const tr=r.transitions||[],by={};tr.forEach(t=>by[t.after_line]=t);
  $('#tlProblems').insertAdjacentHTML('beforeend','<span class="pill acc">'+tr.length+' transitions scheduled</span>');
};
})();
