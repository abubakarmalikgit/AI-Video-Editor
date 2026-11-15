(function () {
  const css = `
  #mx-copylogs{position:fixed;top:10px;right:14px;z-index:9999;display:flex;align-items:center;gap:7px;
    padding:7px 13px;border-radius:999px;cursor:pointer;font:600 12px Inter,system-ui,sans-serif;color:#e9e7ff;
    background:rgba(20,18,36,.85);border:1px solid rgba(139,92,246,.55);backdrop-filter:blur(8px);
    transition:all .18s ease}
  #mx-copylogs:hover{border-color:#22d3ee;box-shadow:0 0 14px rgba(34,211,238,.35);transform:translateY(-1px)}
  #mx-toast{position:fixed;top:52px;right:14px;z-index:10000;padding:9px 14px;border-radius:10px;
    font:500 12.5px Inter,system-ui,sans-serif;color:#fff;background:#1b1830;border:1px solid #8b5cf6;
    opacity:0;transform:translateY(-6px);transition:all .25s ease;pointer-events:none}
  #mx-toast.show{opacity:1;transform:none}
  #mx-toast.bad{border-color:#f43f5e}

  #mx-ai{position:fixed;right:18px;bottom:76px;width:380px;max-height:62vh;z-index:9998;display:flex;
    flex-direction:column;gap:10px;padding:14px 16px;border-radius:16px;background:rgba(16,14,30,.95);
    border:1px solid rgba(139,92,246,.55);box-shadow:0 12px 40px rgba(0,0,0,.55),0 0 28px rgba(139,92,246,.25);
    backdrop-filter:blur(12px);font:13px Inter,system-ui,sans-serif;color:#e9e7ff;opacity:0;
    transform:translateY(16px) scale(.98);pointer-events:none;transition:all .3s ease}
  #mx-ai.show{opacity:1;transform:none;pointer-events:auto}
  #mx-ai.done{border-color:rgba(52,211,153,.6)}
  #mx-ai.err{border-color:rgba(244,63,94,.7)}
  .mx-head{display:flex;align-items:center;gap:11px}
  .mx-orb{width:28px;height:28px;border-radius:50%;position:relative;flex:none;
    background:conic-gradient(from 0deg,#8b5cf6,#22d3ee,#8b5cf6);animation:mxspin 1.1s linear infinite;
    box-shadow:0 0 16px rgba(139,92,246,.6)}
  .mx-orb::after{content:"";position:absolute;inset:5px;border-radius:50%;background:#100e1e;
    animation:mxpulse 1.4s ease-in-out infinite}
  #mx-ai.done .mx-orb{animation:none;background:#34d399;box-shadow:0 0 14px rgba(52,211,153,.6)}
  #mx-ai.done .mx-orb::after{content:"\\2713";inset:0;display:flex;align-items:center;justify-content:center;
    background:none;color:#06281d;font-weight:800;animation:none}
  #mx-ai.err .mx-orb{animation:none;background:#f43f5e;box-shadow:0 0 14px rgba(244,63,94,.6)}
  #mx-ai.err .mx-orb::after{content:"!";inset:0;display:flex;align-items:center;justify-content:center;
    background:none;color:#fff;font-weight:800;animation:none}
  .mx-title{font:700 14px Sora,Inter,sans-serif;flex:1;min-width:0}
  .mx-time{font:500 11.5px "JetBrains Mono",monospace;color:#22d3ee}
  .mx-x{cursor:pointer;color:#8d89b3;font-size:15px;padding:0 2px}
  .mx-x:hover{color:#fff}
  #mx-steps{display:flex;flex-direction:column;gap:5px}
  .mx-st{display:flex;align-items:center;gap:8px;font-size:12.5px;color:#9a96c4}
  .mx-st i{width:7px;height:7px;border-radius:50%;background:#34d399;flex:none}
  .mx-st.now{color:#fff}
  .mx-st.now i{background:#22d3ee;animation:mxpulse 1s ease-in-out infinite}
  .mx-st.now::after{content:"";animation:mxdots 1.2s steps(4,end) infinite}
  .mx-lbl{font:600 10.5px Inter,sans-serif;letter-spacing:.09em;text-transform:uppercase;color:#8b5cf6}
  #mx-th{max-height:118px;overflow:auto;font-size:12px;line-height:1.5;color:#b9b4e6;font-style:italic;
    padding:8px 10px;border-radius:10px;background:rgba(139,92,246,.08);border:1px solid rgba(139,92,246,.2);
    white-space:pre-wrap}
  #mx-rp{max-height:100px;overflow:auto;font-size:13px;line-height:1.5;color:#e9e7ff;white-space:pre-wrap}
  @keyframes mxspin{to{transform:rotate(360deg)}}
  @keyframes mxpulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.55;transform:scale(.86)}}
  @keyframes mxdots{0%{content:""}25%{content:"."}50%{content:".."}75%{content:"..."}}
  `;
  const st = document.createElement('style');
  st.textContent = css;
  document.head.appendChild(st);

  // ---------- copy logs button
  const btn = document.createElement('div');
  btn.id = 'mx-copylogs';
  btn.innerHTML = '<span>📋</span><span>Copy logs</span>';
  const toastEl = document.createElement('div');
  toastEl.id = 'mx-toast';

  function toast(msg, bad) {
    toastEl.textContent = msg;
    toastEl.className = 'show' + (bad ? ' bad' : '');
    clearTimeout(toast._t);
    toast._t = setTimeout(() => { toastEl.className = ''; }, 2200);
  }
  async function copyText(text) {
    try { await navigator.clipboard.writeText(text); return true; } catch (e) {}
    try {
      const ta = document.createElement('textarea');
      ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      const ok = document.execCommand('copy'); ta.remove(); return ok;
    } catch (e) { return false; }
  }
  btn.onclick = async function () {
    try {
      const r = await window.pywebview.api.get_log_text(400);
      if (!r || !r.ok) { toast('Could not read logs', true); return; }
      const ok = await copyText(r.text);
      toast(ok ? 'Logs copied - paste them in the chat' : 'Copy failed', !ok);
    } catch (e) { toast('Copy failed: ' + e, true); }
  };

  // ---------- AI thinking card
  const card = document.createElement('div');
  card.id = 'mx-ai';
  card.innerHTML =
    '<div class="mx-head"><div class="mx-orb"></div><div class="mx-title" id="mx-tt">Thinking</div>' +
    '<div class="mx-time" id="mx-tm"></div><div class="mx-x" id="mx-xx">✕</div></div>' +
    '<div id="mx-steps"></div>' +
    '<div id="mx-thw" style="display:none"><div class="mx-lbl">What the AI is thinking</div><div id="mx-th"></div></div>' +
    '<div id="mx-rpw" style="display:none"><div class="mx-lbl">Answer</div><div id="mx-rp"></div></div>';

  function render(s, state) {
    const steps = s.steps || [];
    const box = card.querySelector('#mx-steps');
    box.innerHTML = '';
    steps.forEach((t, i) => {
      const d = document.createElement('div');
      d.className = 'mx-st' + (state === 'run' && i === steps.length - 1 ? ' now' : '');
      const dot = document.createElement('i');
      const sp = document.createElement('span');
      sp.textContent = t;
      d.appendChild(dot); d.appendChild(sp);
      box.appendChild(d);
    });
    const th = (s.thoughts || '').replace(/\*\*/g, '').trim();
    const thw = card.querySelector('#mx-thw'), thEl = card.querySelector('#mx-th');
    thw.style.display = th ? '' : 'none';
    if (th && thEl.textContent !== th) {
      const near = thEl.scrollHeight - thEl.scrollTop - thEl.clientHeight < 40;
      thEl.textContent = th;
      if (near) thEl.scrollTop = thEl.scrollHeight;
    }
    const rp = (s.reply || '').trim();
    card.querySelector('#mx-rpw').style.display = rp ? '' : 'none';
    card.querySelector('#mx-rp').textContent = rp;
    const secs = Math.max(0, s.elapsed || 0).toFixed(0);
    card.querySelector('#mx-tm').textContent = secs + 's';
    card.querySelector('#mx-tt').textContent =
      state === 'run' ? 'Thinking' : (state === 'err' ? 'Problem: ' + (s.error || '').slice(0, 70) : 'Done');
  }

  let busy = false, wasActive = false, hideT = null, dismissedId = 0;
  card.querySelector('#mx-xx').onclick = function () {
    card.classList.remove('show'); dismissedId = card._id || 0;
  };
  async function tick() {
    if (busy) return;
    const api = window.pywebview && window.pywebview.api;
    if (!api || !api.agent_live) return;
    busy = true;
    try {
      const s = await api.agent_live();
      if (!s || !s.id) return;
      card._id = s.id;
      if (s.active) {
        wasActive = true;
        clearTimeout(hideT);
        if (dismissedId !== s.id) card.classList.add('show');
        card.classList.remove('done', 'err');
        render(s, 'run');
      } else if (wasActive) {
        wasActive = false;
        const bad = !!s.error;
        render(s, bad ? 'err' : 'done');
        card.classList.add(bad ? 'err' : 'done');
        hideT = setTimeout(() => card.classList.remove('show'), bad ? 7000 : 2500);
      }
    } catch (e) {
    } finally { busy = false; }
  }
  setInterval(tick, 450);

  function mount() {
    document.body.appendChild(btn);
    document.body.appendChild(toastEl);
    document.body.appendChild(card);
  }
  if (document.body) mount(); else window.addEventListener('DOMContentLoaded', mount);
})();
