/* MalixAris Polish & Export panel (Part 3B) */
(function () {
  "use strict";
  var CSS = `
#pl-back{position:fixed;inset:0;background:rgba(4,4,12,.55);backdrop-filter:blur(3px);z-index:9000;opacity:0;pointer-events:none;transition:opacity .25s}
#pl-drawer{position:fixed;top:0;right:0;bottom:0;width:470px;max-width:96vw;z-index:9001;display:flex;flex-direction:column;
 background:#0e0e1c!important;border-left:1px solid rgba(139,92,246,.35)!important;border-radius:0!important;
 box-shadow:-20px 0 60px -20px rgba(139,92,246,.45);transform:translateX(105%);transition:transform .35s cubic-bezier(.2,.8,.2,1)}
body.pl-open #pl-back{opacity:1;pointer-events:auto}
body.pl-open #pl-drawer{transform:none}
#pl-drawer *{box-sizing:border-box}
.pl-head{display:flex;align-items:center;justify-content:space-between;padding:18px 20px;border-bottom:1px solid rgba(255,255,255,.08)}
.pl-head h2{margin:0;font-size:19px;background:linear-gradient(90deg,#fff,#c4b5fd 50%,#67e8f9);-webkit-background-clip:text;background-clip:text;color:transparent}
.pl-body{flex:1;overflow:auto;padding:14px 20px}
.pl-hint{font-size:12.5px;opacity:.65;margin:0 0 12px;line-height:1.5}
.pl-sec{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);border-radius:14px;padding:12px 14px;margin-bottom:12px}
.pl-sec h3{margin:0 0 9px;font-size:13px;letter-spacing:.04em;text-transform:uppercase;color:#a78bfa}
.pl-row{display:flex;gap:8px;align-items:center;margin:6px 0;flex-wrap:wrap}
.pl-row label{font-size:13px;display:flex;align-items:center;gap:7px}
.pl-drawer-in,#pl-drawer input[type=text],#pl-drawer input[type=number],#pl-drawer select,#pl-drawer textarea{
 flex:1;min-width:0;background:rgba(0,0,0,.35);color:#fff;border:1px solid rgba(255,255,255,.12);border-radius:9px;padding:8px 10px;font:inherit;font-size:13px}
#pl-drawer input[type=color]{width:42px;height:30px;border:0;background:none;padding:0}
#pl-drawer input[type=range]{flex:1}
.pl-btn{background:rgba(255,255,255,.08);color:#fff;border:1px solid rgba(255,255,255,.14);border-radius:10px;padding:8px 14px;font:inherit;font-size:13px;cursor:pointer}
.pl-btn.go{background:linear-gradient(135deg,#8b5cf6,#22d3ee);border:0;font-weight:600;box-shadow:0 6px 22px -6px rgba(139,92,246,.7)}
.pl-btn:disabled{opacity:.45;cursor:not-allowed}
.pl-foot{padding:14px 20px;border-top:1px solid rgba(255,255,255,.08)}
.pl-bar{height:8px;border-radius:8px;background:rgba(255,255,255,.08);overflow:hidden;margin-bottom:8px}
.pl-bar i{display:block;height:100%;width:0;background:linear-gradient(90deg,#8b5cf6,#22d3ee);box-shadow:0 0 14px rgba(34,211,238,.5);transition:width .4s}
#pl-msg{font-size:12.5px;opacity:.85;min-height:18px;margin-bottom:10px}
#pl-msg.err{color:#fbbf24;opacity:1}
#pl-prev{width:100%;border-radius:10px;margin-top:8px;display:none}
#pl-float{position:fixed;left:16px;bottom:16px;z-index:8000;display:none}
`;
  var HTML = `
<div class="pl-head"><h2>Polish &amp; Export</h2><button class="pl-btn" id="pl-x">Close</button></div>
<div class="pl-body">
 <p class="pl-hint">One extra pass on your finished MP4. Saves a new file ending in <b>_polished.mp4</b>. Your original is never changed. Everything is off until you switch it on.</p>
 <div class="pl-sec"><h3>Video file</h3>
  <div class="pl-row"><input type="text" id="pl-file" placeholder="Leave empty to use your latest render">
  <button class="pl-btn" id="pl-browse">Browse</button><button class="pl-btn" id="pl-latest">Latest</button></div></div>
 <div class="pl-sec"><h3>Export preset</h3>
  <div class="pl-row"><select id="pl-preset">
   <option value="keep">Same quality (high)</option><option value="capcut">CapCut-friendly (best for editing)</option>
   <option value="youtube">YouTube upload</option><option value="small">Small file (max 1080p)</option></select></div></div>
 <div class="pl-sec"><h3>Audio loudness</h3>
  <div class="pl-row"><label><input type="checkbox" id="pl-loud"> Normalize volume</label>
  <select id="pl-lufs"><option value="-14">YouTube / social (-14)</option><option value="-16">Podcast / Spotify (-16)</option><option value="-23">Broadcast (-23)</option></select></div></div>
 <div class="pl-sec"><h3>Color grade</h3>
  <div class="pl-row"><select id="pl-grade"><option value="none">None</option><option value="warm">Warm</option><option value="cool">Cool</option>
   <option value="cinematic">Cinematic teal-orange</option><option value="vivid">Vivid</option><option value="punchy">Punchy contrast</option>
   <option value="soft">Soft film</option><option value="bw">Black &amp; white</option></select></div>
  <div class="pl-row"><span style="font-size:13px">Strength</span><input type="range" id="pl-amount" min="0" max="100"><span id="pl-amtv" style="font-size:13px;width:34px"></span>
  <button class="pl-btn" id="pl-prevbtn">Preview</button></div>
  <img id="pl-prev" alt=""></div>
 <div class="pl-sec"><h3>Intro title card</h3>
  <div class="pl-row"><label><input type="checkbox" id="pl-in-on"> Add intro</label><span style="flex:1"></span>
   <input type="number" id="pl-in-secs" min="1" max="8" step="0.5" style="flex:0 0 70px"><span style="font-size:12px;opacity:.7">sec</span></div>
  <div class="pl-row"><input type="text" id="pl-in-title" placeholder="Title"></div>
  <div class="pl-row"><input type="text" id="pl-in-sub" placeholder="Subtitle (optional)"></div></div>
 <div class="pl-sec"><h3>Outro title card</h3>
  <div class="pl-row"><label><input type="checkbox" id="pl-out-on"> Add outro</label><span style="flex:1"></span>
   <input type="number" id="pl-out-secs" min="1" max="8" step="0.5" style="flex:0 0 70px"><span style="font-size:12px;opacity:.7">sec</span></div>
  <div class="pl-row"><input type="text" id="pl-out-title" placeholder="Title"></div>
  <div class="pl-row"><input type="text" id="pl-out-sub" placeholder="Subtitle (optional)"></div>
  <div class="pl-row"><span style="font-size:13px">Card colors</span><input type="color" id="pl-bg"><input type="color" id="pl-fg"><span style="font-size:12px;opacity:.6">background / text</span></div></div>
 <div class="pl-sec"><div class="pl-row"><label><input type="checkbox" id="pl-auto"> Polish automatically after every render</label></div></div>
</div>
<div class="pl-foot"><div class="pl-bar"><i id="pl-fill"></i></div><div id="pl-msg">Ready</div>
 <div class="pl-row" style="margin:0"><button class="pl-btn go" id="pl-run">Polish now</button>
 <button class="pl-btn" id="pl-cancel" disabled>Cancel</button><button class="pl-btn" id="pl-open" style="display:none">Show file</button></div></div>`;

  var $ = function (id) { return document.getElementById(id); };
  var out = "", wasRunning = false, saveT = 0;
  var ICON = '<span class="px-ico"><svg viewBox="0 0 24 24"><path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9Z"/><path d="M19 17v4M17 19h4"/></svg></span>';

  function api(n) {
    var a = [].slice.call(arguments, 1), p = window.pywebview && window.pywebview.api;
    if (!p || !p[n]) return Promise.reject(new Error("not ready"));
    return p[n].apply(p, a);
  }
  function toast(m, k) { if (window.pxToast) window.pxToast(m, k); }
  function open() { document.body.classList.add("pl-open"); load(); }
  function close() { document.body.classList.remove("pl-open"); }

  function collect() {
    return {
      auto: $("pl-auto").checked, preset: $("pl-preset").value,
      loud: { on: $("pl-loud").checked, lufs: parseFloat($("pl-lufs").value) },
      grade: { name: $("pl-grade").value, amount: parseInt($("pl-amount").value, 10) },
      intro: { on: $("pl-in-on").checked, title: $("pl-in-title").value, sub: $("pl-in-sub").value, secs: parseFloat($("pl-in-secs").value) },
      outro: { on: $("pl-out-on").checked, title: $("pl-out-title").value, sub: $("pl-out-sub").value, secs: parseFloat($("pl-out-secs").value) },
      bg: $("pl-bg").value, fg: $("pl-fg").value
    };
  }
  function fill(c) {
    $("pl-auto").checked = c.auto; $("pl-preset").value = c.preset;
    $("pl-loud").checked = c.loud.on; $("pl-lufs").value = String(c.loud.lufs);
    $("pl-grade").value = c.grade.name; $("pl-amount").value = c.grade.amount; $("pl-amtv").textContent = c.grade.amount + "%";
    $("pl-in-on").checked = c.intro.on; $("pl-in-title").value = c.intro.title; $("pl-in-sub").value = c.intro.sub; $("pl-in-secs").value = c.intro.secs;
    $("pl-out-on").checked = c.outro.on; $("pl-out-title").value = c.outro.title; $("pl-out-sub").value = c.outro.sub; $("pl-out-secs").value = c.outro.secs;
    $("pl-bg").value = c.bg; $("pl-fg").value = c.fg;
  }
  function load() { api("polish_get").then(fill).catch(function () {}); }
  function queueSave() {
    clearTimeout(saveT);
    $("pl-amtv").textContent = $("pl-amount").value + "%";
    saveT = setTimeout(function () { api("polish_save", collect()).catch(function () {}); }, 400);
  }
  function setMsg(t, err) { var m = $("pl-msg"); m.textContent = t; m.className = err ? "err" : ""; }

  function poll() {
    api("polish_status").then(function (s) {
      $("pl-fill").style.width = (s.running ? s.pct : (s.out ? 100 : 0)) + "%";
      $("pl-run").disabled = s.running; $("pl-cancel").disabled = !s.running;
      setMsg(s.error ? ("Problem: " + s.error) : (s.msg + (s.running ? " " + s.pct + "%" : "")), !!s.error);
      out = s.out || "";
      $("pl-open").style.display = out ? "" : "none";
      if (wasRunning && !s.running) {
        if (s.error) toast("Polish failed: " + s.error, "warn");
        else toast("Polished video saved (_polished.mp4)", "ok");
      }
      wasRunning = s.running;
    }).catch(function () {});
  }

  function build() {
    var st = document.createElement("style"); st.textContent = CSS; document.head.appendChild(st);
    var back = document.createElement("div"); back.id = "pl-back"; document.body.appendChild(back);
    var d = document.createElement("div"); d.id = "pl-drawer"; d.innerHTML = HTML; document.body.appendChild(d);
    back.onclick = close; $("pl-x").onclick = close;
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") close(); });
    d.addEventListener("input", queueSave); d.addEventListener("change", queueSave);
    $("pl-browse").onclick = function () { api("polish_pick").then(function (p) { if (p) $("pl-file").value = p; }); };
    $("pl-latest").onclick = function () { api("polish_latest").then(function (p) { $("pl-file").value = p || ""; if (!p) toast("No render found yet", "warn"); }); };
    $("pl-run").onclick = function () {
      api("polish_save", collect()).then(function () { return api("polish_run", $("pl-file").value.trim()); })
        .then(function (r) { if (!r.ok) { setMsg(r.error, true); toast(r.error, "warn"); } else { wasRunning = true; poll(); } });
    };
    $("pl-cancel").onclick = function () { api("polish_cancel"); };
    $("pl-open").onclick = function () { if (out) api("polish_open", out); };
    $("pl-prevbtn").onclick = function () {
      setMsg("Making preview...");
      api("polish_save", collect()).then(function () { return api("polish_preview", $("pl-file").value.trim()); })
        .then(function (r) {
          if (r.ok) { var i = $("pl-prev"); i.src = r.img; i.style.display = "block"; setMsg("Preview of the grade (frame near the start)"); }
          else { setMsg(r.error, true); }
        });
    };
    setInterval(poll, 900);
  }

  function addNav() {
    var all = document.querySelectorAll("nav *, aside *, .sidebar *, [class*=nav] *"), best = null;
    for (var i = 0; i < all.length; i++) {
      var t = (all[i].textContent || "").trim();
      if (t.length < 40 && /Captions/.test(t) && !all[i].dataset.pl) { best = all[i]; break; }
    }
    if (!best || !best.parentNode) return false;
    var c = best.cloneNode(false);
    [].slice.call(c.attributes).forEach(function (a) {
      if (a.name === "id" || a.name === "onclick" || a.name.indexOf("data-") === 0 || a.name === "href") c.removeAttribute(a.name);
    });
    c.classList.remove("active");
    c.dataset.pl = "1";
    c.innerHTML = ICON + "Polish &amp; Export";
    c.addEventListener("click", function (e) { e.preventDefault(); e.stopPropagation(); open(); }, true);
    best.parentNode.insertBefore(c, best.nextSibling);
    return true;
  }

  function init() {
    build();
    var tries = 0, iv = setInterval(function () {
      tries++;
      if (addNav()) { clearInterval(iv); }
      else if (tries > 12) {
        clearInterval(iv);
        var b = document.createElement("button"); b.id = "pl-float"; b.className = "pl-btn go";
        b.style.display = "block"; b.innerHTML = ICON + "Polish &amp; Export"; b.onclick = open;
        document.body.appendChild(b);
      }
    }, 700);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
