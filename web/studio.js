/* MalixAris Studio shell: navigation, dashboard, command palette and workspace polish. */
(function () {
  'use strict';
  const $ = (s, r=document) => r.querySelector(s);
  const $$ = (s, r=document) => Array.from(r.querySelectorAll(s));
  const nav = $('nav');
  const content = $('.content');
  if (!nav || !content) return;

  const home = document.createElement('section');
  home.className = 'page'; home.id = 'p-home';
  home.innerHTML = `
    <div class="studio-hero">
      <div><h2>Your production workspace.</h2><p>Plan, assemble and finish videos from one desktop studio. Your existing clip-matching, AI Director, captions, audio and export workflows remain available.</p></div>
      <div class="hero-actions"><button class="btn primary" data-go="project">Start a project</button><button class="btn" data-go="director">Open AI Director</button></div>
    </div>
    <div class="studio-status-grid">
      <div class="studio-stat"><small>Workspace</small><b>Ready</b></div>
      <div class="studio-stat"><small>Editing workflow</small><b>Script-based</b></div>
      <div class="studio-stat"><small>AI assistant</small><b>Integrated</b></div>
      <div class="studio-stat"><small>Export</small><b>Local render</b></div>
    </div>
    <div class="studio-section-head"><strong>Production tools</strong><span>Choose a workspace</span></div>
    <div class="studio-grid">
      <div class="studio-tile" data-go="projects"><div class="tile-icon">▦</div><strong>Open saved projects</strong><span>Browse previous editing sessions and continue their saved timelines.</span></div><div class="studio-tile" data-go="project"><div class="tile-icon">▧</div><strong>New production</strong><span>Choose footage, voiceover and script. Inspect and prepare your project.</span></div>
      <div class="studio-tile" data-go="timeline"><div class="tile-icon">▤</div><strong>Timeline overview</strong><span>Review generated line timings, clip assignments and detected issues.</span></div>
      <div class="studio-tile" data-go="director"><div class="tile-icon">✦</div><strong>AI Director</strong><span>Build an edit plan, apply supported changes and review the result.</span></div>
      <div class="studio-tile" data-action="polish"><div class="tile-icon">◈</div><strong>Polish &amp; Export</strong><span>Open final video finishing, quality presets and export controls.</span></div>
      <div class="studio-tile" data-action="voice"><div class="tile-icon">♩</div><strong>Voice commands</strong><span>Use the microphone control where available to dictate supported commands.</span></div>
      <div class="studio-tile" data-go="output"><div class="tile-icon">⚙</div><strong>Render settings</strong><span>Configure resolution, frame rate, quality and processing options.</span></div>
    </div>
    <div class="studio-section-head"><strong>Workflow status</strong><span>Existing engine</span></div>
    <div class="studio-note">MalixAris currently assembles videos from numbered clips, a voiceover and script/timestamp mapping. The timeline view represents the generated sequence. A fully manual multitrack drag-and-drop NLE is a separate engine feature and is not implied by this redesigned interface.</div>
    <div class="studio-section-head"><strong>Quick actions</strong><span>Keyboard shortcuts: Ctrl+K</span></div>
    <div class="row" style="flex-wrap:wrap"><button class="btn" data-go="project">Set up footage</button><button class="btn" data-go="director">Plan with AI</button><button class="btn" data-go="logs">View activity logs</button><button class="btn" data-go="about">System information</button></div>`;
  content.insertBefore(home, content.firstChild);

  const projects = document.createElement('section');
  projects.className = 'page'; projects.id = 'p-projects';
  projects.innerHTML = `
    <div class="projects-heading"><div><h1>Projects</h1><p class="sub">Your saved editing sessions. Reopen an older project to restore its script, media paths, export settings and saved timeline.</p></div><span class="template-count" id="project-library-count">LOADING PROJECTS</span></div>
    <div class="project-manager-toolbar"><input id="project-search" placeholder="Search your projects…" aria-label="Search projects"><button class="btn" id="project-refresh">Refresh</button><button class="btn primary" id="project-new">＋ New Project</button><button class="btn" id="project-save-current">Save Current Project</button></div>
    <div id="project-manager-list" class="project-manager-list"><div class="project-empty">Loading saved projects…</div></div>
    <div class="project-manager-note">Projects store your script, footage and voiceover paths, language, export settings, timeline snapshot and AI edit state. Media files remain in their original folders. Recovered legacy entries may contain a saved timeline but not all original setup fields.</div>
    <details class="project-templates-details"><summary>Starter templates (optional)</summary><div class="template-grid" id="studio-template-grid"></div><div class="template-footnote">Templates are optional starting scripts. They do not replace your saved editing projects.</div></details>`;
  content.insertBefore(projects, home.nextSibling);
  if (!$('button[data-p="projects"]', nav)) {
    const b=document.createElement('button'); b.dataset.p='projects'; nav.insertBefore(b, nav.children[1] || null);
  }

  const top = document.createElement('div');
  top.className = 'studio-topbar';
  top.innerHTML = `<div class="studio-crumb"><strong id="studio-page-title">Home</strong><span id="studio-page-subtitle">MalixAris Video Production Studio</span></div><div class="studio-top-spacer"></div><div class="studio-status"><i></i><span>Desktop workspace</span></div><button class="studio-top-btn" id="studio-theme" title="Toggle light and dark appearance">Appearance</button><button class="studio-top-btn" id="studio-command-open" title="Command palette (Ctrl+K)">⌘ Commands</button>`;
  const main = $('main');
  main.insertBefore(top, content);

  // Rebuild the navigation labels while preserving the existing page IDs and feature scripts.
  const labels = {
    home: 'Home', projects: 'Projects', project: 'Create Project', timeline: 'Timeline', output: 'Render Settings',
    logs: 'Activity Logs', finish: 'Captions & Music', director: 'AI Director', about: 'System Settings'
  };
  const glyphs = {home:'⌂',projects:'▦',project:'▧',timeline:'▤',output:'⚙',logs:'≡',finish:'♫',director:'✦',about:'◉'};
  $$('.soon', nav).forEach(b => b.remove());
  if (!$('button[data-p="home"]', nav)) {
    const b = document.createElement('button'); b.dataset.p='home'; nav.insertBefore(b, nav.firstChild);
  }
  $$('button[data-p]', nav).forEach(b => {
    const key=b.dataset.p;
    if(labels[key]) b.textContent = glyphs[key]+'  '+labels[key];
    b.classList.remove('soon');
  });
  // Existing Director script adds its nav entry after the original inline navigation handler.
  function activate(page) {
    if (!$('#p-'+page)) return;
    $$('nav button[data-p]').forEach(b => b.classList.toggle('on', b.dataset.p===page));
    $$('.page').forEach(p => p.classList.toggle('on', p.id==='p-'+page));
    const title = labels[page] || (page==='voice'?'Voice Commands':page);
    $('#studio-page-title').textContent = title;
    const subtitles = {
      home:'MalixAris Video Production Studio', projects:'Your saved editing sessions and previous timelines', project:'Footage, voiceover and script setup',
      timeline:'Generated sequence and clip assignment review', output:'Video processing and output configuration',
      logs:'Processing activity, warnings and errors', finish:'Subtitle generation and background music controls', director:'AI-assisted planning and supported editing actions',
      about:'Application version and system capabilities'
    };
    $('#studio-page-subtitle').textContent = subtitles[page] || 'MalixAris Studio';
    try { localStorage.setItem('malixaris.lastPage', page); } catch(e) {}
  }
  // Delegation also handles navigation buttons injected by feature modules.
  nav.addEventListener('click', e => {
    const b=e.target.closest('button[data-p]'); if(!b) return;
    e.preventDefault(); activate(b.dataset.p);
  });
  document.addEventListener('click', e => {
    const go=e.target.closest('[data-go]');
    if(go){activate(go.dataset.go);return;}
    const action=e.target.closest('[data-action]');
    if(action){
      if(action.dataset.action==='polish'){
        const opener=$('[data-pl="1"]') || $('#pl-float'); if(opener) opener.click(); else if(window.pxToast) window.pxToast('Polish panel is not available yet.','warn');
      }
      if(action.dataset.action==='voice'){
        const mic=$('#vx-fab'); if(mic) mic.click(); else if(window.pxToast) window.pxToast('Voice controls are added to supported command fields.','ok');
      }
    }
  });

  // Command palette: actions navigate to real existing workspaces or open existing tools.
  const backdrop=document.createElement('div'); backdrop.id='studio-command-backdrop';
  backdrop.innerHTML=`<div class="studio-command" role="dialog" aria-modal="true" aria-label="Command palette"><input id="studio-command-input" placeholder="Search actions and workspaces…" autocomplete="off"><div class="studio-command-list" id="studio-command-list"></div></div>`;
  document.body.appendChild(backdrop);
  const commands=[
    ['Go to Home','home','Dashboard'],['Projects','projects','Premade editable project templates'],['Create Project','project','Footage and script setup'],
    ['Open Timeline','timeline','Generated sequence'],['Captions & Music','finish','Subtitle and music controls'],['Open AI Director','director','AI editing assistant'],
    ['Render Settings','output','Resolution and quality'],['Activity Logs','logs','Processing diagnostics'],
    ['System Settings','about','Version and system information'],['Polish & Export','polish','Final finishing panel'],['Voice Commands','voice','Microphone controls']
  ];
  const input=$('#studio-command-input'), list=$('#studio-command-list');
  function drawCommands(q=''){
    const rows=commands.filter(c=>(c[0]+' '+c[2]).toLowerCase().includes(q.toLowerCase()));
    list.innerHTML=rows.map(c=>`<div class="studio-command-item" data-cmd="${c[1]}"><span>${c[0]}</span><small>${c[2]}</small></div>`).join('') || '<div class="studio-command-item">No matching actions</div>';
  }
  function openPalette(){backdrop.classList.add('open');input.value='';drawCommands();input.focus();}
  function closePalette(){backdrop.classList.remove('open');}
  function runCommand(c){closePalette();if(c==='polish'){const x=$('[data-pl="1"]') || $('#pl-float');if(x)x.click();return;}if(c==='voice'){const x=$('#vx-fab');if(x)x.click();return;}activate(c);}
  $('#studio-command-open').addEventListener('click',openPalette);
  $('#studio-theme').addEventListener('click',()=>{document.body.classList.toggle('studio-light');try{localStorage.setItem('malixaris.theme',document.body.classList.contains('studio-light')?'light':'dark');}catch(e){}});
  input.addEventListener('input',()=>drawCommands(input.value));
  list.addEventListener('click',e=>{const x=e.target.closest('[data-cmd]');if(x)runCommand(x.dataset.cmd);});
  backdrop.addEventListener('click',e=>{if(e.target===backdrop)closePalette();});
  document.addEventListener('keydown',e=>{
    if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();openPalette();}
    if(e.key==='Escape')closePalette();
    if(!e.ctrlKey&&!e.metaKey&&!e.altKey&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){
      const k=e.key.toLowerCase(); if(k==='1')activate('home'); if(k==='2')activate('project'); if(k==='3')activate('timeline'); if(k==='4')activate('director');
    }
  });
  try { if(localStorage.getItem('malixaris.theme')==='light')document.body.classList.add('studio-light'); } catch(e) {}
  let last='home'; try{last=localStorage.getItem('malixaris.lastPage')||'home';}catch(e){}
  activate($('#p-'+last)?last:'home');
})();

// Real project manager: named sessions plus recoverable legacy timeline snapshots.
(function(){
  'use strict';
  const $=s=>document.querySelector(s);
  let activeId='', activeName='';
  const fields=['clips','audio','lang','script','res','fps','quality','fit','smooth','lead','wmodel'];
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const readOpts=()=>{const o={};fields.forEach(k=>{const el=document.getElementById(k);if(el)o[k]=el.value;});return {clips_dir:o.clips||'',audio:o.audio||'',lang:o.lang||'',script:o.script||'',res:o.res||'original',fps:o.fps||'auto',quality:o.quality||'high',fit:o.fit||'blur',smooth:o.smooth||'off',lead_ms:parseInt(o.lead||'100',10),whisper_model:o.wmodel||''};};
  function when(t){if(!t)return 'Date unavailable';try{return new Date(t*1000).toLocaleString();}catch(e){return 'Date unavailable';}}
  function toastMsg(m){if(window.pxToast)window.pxToast(m,'ok');else if(window.toast)window.toast(m);}
  async function refresh(){
    const box=$('#project-manager-list'); if(!box||!window.pywebview?.api)return;
    box.innerHTML='<div class="project-empty">Loading projects…</div>';
    try{
      const rows=await window.pywebview.api.list_projects();
      const q=($('#project-search')?.value||'').trim().toLowerCase();
      const visible=(rows||[]).filter(r=>!q||[r.name,r.clips_dir,r.audio].join(' ').toLowerCase().includes(q));
      $('#project-library-count').textContent=(rows||[]).length+' PROJECT'+((rows||[]).length===1?'':'S');
      if(!visible.length){box.innerHTML='<div class="project-empty"><strong>No saved projects found</strong><span>Create a project or save your current editing session. Older timeline snapshots will appear here when recoverable.</span></div>';return;}
      box.innerHTML=visible.map(r=>`<article class="project-row" data-project-id="${esc(r.id)}"><div class="project-row-main"><div class="project-file-icon">${r.legacy?'↻':'▤'}</div><div class="project-row-copy"><strong>${esc(r.name)}</strong><small>${r.legacy?'Recovered legacy project':'Saved editing project'} · Updated ${esc(when(r.updated_at))}</small><div class="project-row-meta"><span>${Number(r.line_count||0)} timeline rows</span><span>${r.timeline_saved?'Timeline saved':'No timeline snapshot'}</span>${r.clips_dir?`<span title="${esc(r.clips_dir)}">Footage linked</span>`:'<span>Footage not linked</span>'}</div></div></div><div class="project-row-actions"><button class="btn primary" data-project-open="${esc(r.id)}">${r.legacy?'Recover':'Open'}</button><button class="btn" data-project-rename="${esc(r.id)}">Rename</button><button class="btn" data-project-duplicate="${esc(r.id)}" ${r.legacy?'disabled':''}>Duplicate</button><button class="btn danger" data-project-delete="${esc(r.id)}" ${r.legacy?'disabled':''}>Delete</button></div></article>`).join('');
    }catch(e){box.innerHTML='<div class="project-empty">Could not load projects: '+esc(String(e))+'</div>';}
  }
  async function saveCurrent(createIfNeeded=false,quiet=false){
    if(!window.pywebview?.api)return;
    if(activeId.startsWith('legacy-')&&!createIfNeeded)return;
    let name=activeName;
    if(!activeId||createIfNeeded){name=prompt('Project name:',name||'Untitled Project');if(name===null)return;}
    const r=await window.pywebview.api.save_project(readOpts(),activeId,name||'Untitled Project');
    if(!r.ok){if(!quiet)alert(r.error||'Could not save project');return;}
    activeId=r.project.id;activeName=r.project.name;
    if(!quiet){toastMsg('Saved project: '+activeName);refresh();}
  }
  async function createNew(){
    if(!window.pywebview?.api)return;
    const name=prompt('Name your new project:','Untitled Project');if(name===null)return;
    const blank={clips_dir:'',audio:'',lang:'',script:'',res:'original',fps:'auto',quality:'high',fit:'blur',smooth:'off',lead_ms:100,whisper_model:''};
    const r=await window.pywebview.api.create_project(name,blank);
    if(!r.ok){alert(r.error||'Could not create project');return;}
    activeId=r.project.id;activeName=r.project.name;
    fields.forEach(k=>{const el=document.getElementById(k);if(el)el.value=({clips:'',audio:'',lang:'',script:'',res:'original',fps:'auto',quality:'high',fit:'blur',smooth:'off',lead:'100',wmodel:''})[k]??'';});
    fields.forEach(k=>document.getElementById(k)?.dispatchEvent(new Event('change',{bubbles:true})));
    $('#tlEmpty')?.classList.remove('hide');$('#tlWrap')?.classList.add('hide');
    document.querySelector('nav button[data-p="project"]')?.click();
    toastMsg('New project created: '+activeName);refresh();
  }
  async function openProject(id){
    const r=await window.pywebview.api.load_project(id);if(!r.ok){alert(r.error||'Could not open project');return;}
    const p=r.project||{};activeId=p.id||id;activeName=p.name||'Recovered Project';
    const o=p.opts||{};
    const map={clips:o.clips_dir||'',audio:o.audio||'',lang:o.lang||'',script:o.script||'',res:o.res||'original',fps:o.fps||'auto',quality:o.quality||'high',fit:o.fit||'blur',smooth:o.smooth||'off',lead:String(o.lead_ms??100),wmodel:o.whisper_model||''};
    if(!p.legacy){
      fields.forEach(k=>{const el=document.getElementById(k);if(el)el.value=map[k]??'';});
      fields.forEach(k=>document.getElementById(k)?.dispatchEvent(new Event('change',{bubbles:true})));
    }
    if(p.timeline?.lines?.length){
      const state=p.state||{}, ts=state.transitions||{};
      const trans=Object.entries(ts).map(([line,v])=>({after_line:Number(line),type:v.type||v.name||'fade',dur:Number(v.dur||v.duration||0.5)}));
      if(typeof window.renderTimeline==='function')window.renderTimeline({lines:p.timeline.lines,problems:[],cfg:{W:1920,H:1080,fps:Number(o.fps)||30},coverage:1,transitions:trans});
      $('#tlEmpty')?.classList.add('hide');$('#tlWrap')?.classList.remove('hide');
    }else{$('#tlEmpty')?.classList.remove('hide');$('#tlWrap')?.classList.add('hide');}
    document.querySelector('nav button[data-p="project"]')?.click();
    if(map.clips)document.getElementById('bRescan')?.click();
    toastMsg('Opened '+activeName+' — review media paths before rendering.');
  }
  document.addEventListener('click',async e=>{
    if(e.target.closest('#project-refresh'))refresh();
    if(e.target.closest('#project-new'))createNew();
    if(e.target.closest('#project-save-current'))saveCurrent(true);
    const open=e.target.closest('[data-project-open]');if(open){openProject(open.dataset.projectOpen);return;}
    const ren=e.target.closest('[data-project-rename]');if(ren){const id=ren.dataset.projectRename;const name=prompt('New project name:');if(name&&await window.pywebview.api.rename_project(id,name).then(x=>x.ok))refresh();return;}
    const dup=e.target.closest('[data-project-duplicate]');if(dup){const x=await window.pywebview.api.duplicate_project(dup.dataset.projectDuplicate);if(!x.ok)alert(x.error||'Could not duplicate');refresh();return;}
    const del=e.target.closest('[data-project-delete]');if(del){if(confirm('Delete this project entry? Its saved timeline and AI state files will be retained for recovery.')){await window.pywebview.api.delete_project(del.dataset.projectDelete);if(activeId===del.dataset.projectDelete){activeId='';activeName='';}refresh();}return;}
  });
  $('#project-search')?.addEventListener('input',refresh);
  let autosaveTimer=null;
  fields.forEach(k=>{const el=document.getElementById(k);if(!el)return;['input','change'].forEach(evt=>el.addEventListener(evt,()=>{if(!activeId||activeId.startsWith('legacy-'))return;clearTimeout(autosaveTimer);autosaveTimer=setTimeout(()=>saveCurrent(false,true),1100);}));});
  window.addEventListener('pywebviewready',refresh);
  window.addEventListener('malixaris-project-refresh',refresh);
  window.malixarisProjectManager={refresh,saveCurrent,getActive:()=>({id:activeId,name:activeName})};
  setTimeout(()=>{if(window.pywebview?.api)refresh();},1200);
})();

// Editable starter projects. Applying a template only fills the existing script/output controls.
(function(){
  const templates = [
    {id:'documentary',icon:'◉',tag:'STORY-DRIVEN',name:'YouTube Documentary',desc:'A structured mini-documentary with a strong hook, context, evidence and conclusion.',duration:'6–10 min',res:'1080p',fps:'30',script:[
      'OPENING HOOK: Start with the most surprising fact or unanswered question.',
      'CONTEXT: Explain when and where the story begins, and why it matters.',
      'BACKGROUND: Introduce the people, technology or event involved.',
      'KEY DEVELOPMENT: Describe the first major turning point using clear evidence.',
      'DEEPER EXPLANATION: Break down the important details in a simple sequence.',
      'CONSEQUENCES: Explain what changed and who was affected.',
      'FINAL REVEAL: Present the strongest finding or most important takeaway.',
      'CONCLUSION: Resolve the opening question and close with a concise final thought.'
    ]},
    {id:'gaming',icon:'⌁',tag:'FAST-PACED',name:'Gaming Montage',desc:'A high-energy sequence for gameplay highlights, clutch moments and match recaps.',duration:'30–90 sec',res:'1080p',fps:'60',script:[
      'COLD OPEN: Show the strongest gameplay moment immediately.',
      'SETUP: Introduce the game, mode and challenge in one short line.',
      'BUILD-UP: Show movement, preparation or the start of the match.',
      'HIGHLIGHT 1: Feature the first standout play.',
      'ESCALATION: Increase pace and build toward the main moment.',
      'MAIN MOMENT: Show the clutch, win or most impressive sequence.',
      'REACTION: Give the result or a short reaction.',
      'OUTRO: End cleanly with a short call to action.'
    ]},
    {id:'promo',icon:'◇',tag:'BRAND / PRODUCT',name:'Product Promo',desc:'A concise promotional video covering the problem, product benefits and call to action.',duration:'30–60 sec',res:'1080p',fps:'30',script:[
      'HOOK: State the audience problem or desired result.',
      'PROBLEM: Show the frustrating situation the audience recognizes.',
      'INTRODUCE PRODUCT: Present the product or service clearly.',
      'BENEFIT 1: Explain the most important practical benefit.',
      'BENEFIT 2: Demonstrate another useful feature or advantage.',
      'PROOF: Add a real demonstration, result or customer evidence.',
      'OFFER: Explain the next step or relevant offer without unsupported claims.',
      'CALL TO ACTION: Tell viewers exactly where to learn more or take action.'
    ]},
    {id:'explainer',icon:'▤',tag:'EDUCATIONAL',name:'Educational Explainer',desc:'A lesson-style video that moves from a clear question to a step-by-step explanation.',duration:'3–7 min',res:'1080p',fps:'30',script:[
      'LEARNING HOOK: Ask a question that the viewer will be able to answer by the end.',
      'CORE IDEA: Define the topic in plain language.',
      'WHY IT MATTERS: Explain where this concept appears in real life.',
      'STEP 1: Introduce the first part of the process or concept.',
      'STEP 2: Explain the next part with a concrete example.',
      'STEP 3: Connect the parts and clarify a common misunderstanding.',
      'RECAP: Summarize the main points in a few sentences.',
      'CLOSING: Give one useful takeaway and finish the lesson.'
    ]},
    {id:'shorts',icon:'▯',tag:'VERTICAL SHORT',name:'YouTube Shorts',desc:'A compact short-form structure designed around one idea and a fast payoff.',duration:'20–45 sec',res:'1080p',fps:'30',script:[
      '0–2 SEC HOOK: Lead with a bold question, result or surprising fact.',
      '2–8 SEC CONTEXT: Give only the information needed to understand the topic.',
      '8–20 SEC VALUE: Deliver the key explanation or demonstration.',
      '20–32 SEC PAYOFF: Reveal the result, lesson or strongest moment.',
      'FINAL BEAT: End with a memorable line or simple call to action.'
    ]}
  ];
  const grid=document.getElementById('studio-template-grid');
  if(!grid)return;
  const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  grid.innerHTML=templates.map(t=>`<article class="template-card"><div class="template-card-top"><span class="template-icon">${t.icon}</span><span class="template-tag">${t.tag}</span></div><h2>${t.name}</h2><p>${t.desc}</p><div class="template-meta"><span>${t.duration}</span><span>${t.res} · ${t.fps} FPS</span></div><button class="btn primary" data-use-template="${t.id}">Use template</button><button class="template-preview" data-preview-template="${t.id}">Preview structure</button><div class="template-preview-body" data-preview-body="${t.id}" hidden>${t.script.map((line,i)=>`<div><b>${String(i+1).padStart(2,'0')}</b>${esc(line)}</div>`).join('')}</div></article>`).join('');
  grid.addEventListener('click',e=>{
    const preview=e.target.closest('[data-preview-template]');
    if(preview){const body=grid.querySelector(`[data-preview-body="${preview.dataset.previewTemplate}"]`);if(body){body.hidden=!body.hidden;preview.textContent=body.hidden?'Preview structure':'Hide preview';}return;}
    const use=e.target.closest('[data-use-template]');if(!use)return;
    const t=templates.find(x=>x.id===use.dataset.useTemplate);if(!t)return;
    const script=document.getElementById('script');
    if(script.value.trim()&&!window.confirm('Replace the current script with this template? Your clips folder and voiceover will stay unchanged.'))return;
    script.value=t.script.map((line,i)=>`${String(i+1).padStart(3,'0')} : ${line}`).join('\n');
    const res=document.getElementById('res'),fps=document.getElementById('fps');
    if(res)res.value=t.res;if(fps)fps.value=t.fps;
    script.dispatchEvent(new Event('input',{bubbles:true}));script.dispatchEvent(new Event('change',{bubbles:true}));
    if(window.pywebview?.api){const data={script:script.value,res:t.res,fps:t.fps};window.pywebview.api.save_settings(data);}
    const projectNav=document.querySelector('nav button[data-p="project"]');if(projectNav)projectNav.click();
    const info=document.getElementById('scriptInfo');if(info)info.textContent=`${t.name} template loaded. Edit the sample lines, then select your footage and voiceover.`;
    const toast=document.createElement('div');toast.textContent=`${t.name} loaded into Create Project.`;document.getElementById('toast')?.appendChild(toast);setTimeout(()=>toast.remove(),3500);
  });
})();

// Rendered-project library: list and replay previous exports, not only the latest render.
(function(){
  const $=s=>document.querySelector(s);
  function fileUrl(path){
    const normalized=String(path||'').replace(/\\/g,'/');
    return 'file:///'+encodeURI(normalized).replace(/#/g,'%23');
  }
  async function refresh(){
    const box=$('#outputLibrary'); if(!box||!window.pywebview?.api)return;
    box.innerHTML='<div class="info">Scanning output folder…</div>';
    try{
      const rows=await window.pywebview.api.list_outputs();
      if(!rows.length){box.innerHTML='<div class="info">No rendered videos found in the output folder yet.</div>';return;}
      box.innerHTML=rows.map((r,i)=>{
        const mb=(r.size/1048576).toFixed(1)+' MB';
        const dur=r.duration?Math.floor(r.duration/60)+':'+String(Math.floor(r.duration%60)).padStart(2,'0'):'Duration unavailable';
        return '<div class="output-item"><div class="meta"><strong title="'+escHtml(r.name)+'">'+escHtml(r.name)+'</strong><small>'+dur+' · '+mb+'</small></div><button class="btn primary" data-play-output="'+i+'">Play</button><button class="btn" data-open-output="'+i+'">Folder</button></div>';
      }).join('');
      box._rows=rows;
    }catch(e){box.innerHTML='<div class="info">Could not load rendered projects: '+escHtml(String(e))+'</div>';}
  }
  function escHtml(v){return String(v||'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
  document.addEventListener('click',e=>{
    const play=e.target.closest('[data-play-output]');
    if(play){const r=$('#outputLibrary')?$('#outputLibrary')._rows?.[Number(play.dataset.playOutput)]:null;if(!r)return;
      const v=$('#outputPlayer');v.src=r.uri||fileUrl(r.path);v.style.display='block';$('#outputPlayerName').textContent=r.name;v.load();v.play().catch(()=>{v.controls=true;});v.onerror=()=>{const n=$('#outputPlayerName');if(n)n.textContent=r.name+' — WebView could not play this format. Use Folder to open it in your system player.';};return;}
    const open=e.target.closest('[data-open-output]');
    if(open){const r=$('#outputLibrary')?$('#outputLibrary')._rows?.[Number(open.dataset.openOutput)]:null;if(r&&window.pywebview?.api)window.pywebview.api.open_output(r.path);}
  });
  document.addEventListener('click',e=>{if(e.target.closest('#refreshOutputs'))refresh();if(e.target.closest('#openOutputs')&&window.pywebview?.api)window.pywebview.api.open_output('');});
  window.addEventListener('pywebviewready',()=>refresh());
  document.addEventListener('click',e=>{if(e.target.closest('button[data-p="output"]'))setTimeout(refresh,100);});
  setTimeout(()=>{if(window.pywebview?.api)refresh();},1800);
})();
