/* MalixAris Voice + command routing (Part 3D) */
(function () {
  "use strict";
  var CSS = `
.vx-mic{display:inline-flex;align-items:center;gap:6px;margin-right:8px;padding:8px 12px;border-radius:10px;
 border:1px solid rgba(139,92,246,.5);background:rgba(139,92,246,.16);color:#c4b5fd;cursor:pointer;font:inherit;font-size:12.5px}
.vx-mic:hover{background:rgba(139,92,246,.3);color:#fff}
.vx-i{display:inline-block;width:1.15em;height:1.15em}
.vx-i svg{width:100%;height:100%;stroke:currentColor;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.vx-rec{background:#f43f5e!important;border-color:#f43f5e!important;color:#fff!important;animation:vxPulse 1.2s infinite}
.vx-busy{opacity:.65;cursor:progress}
@keyframes vxPulse{0%{box-shadow:0 0 0 0 rgba(244,63,94,.6)}100%{box-shadow:0 0 0 16px rgba(244,63,94,0)}}
#vx-fab{position:fixed;left:18px;bottom:72px;width:48px;height:48px;border-radius:50%;z-index:8500;border:0;color:#fff;
 display:flex;align-items:center;justify-content:center;cursor:pointer;background:linear-gradient(135deg,#8b5cf6,#22d3ee);
 box-shadow:0 8px 26px -6px rgba(139,92,246,.75)}
#vx-fab .vx-lb{display:none}
`;
  var ICON = '<span class="vx-i"><svg viewBox="0 0 24 24"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><path d="M12 19v3"/></svg></span>';
  var S = { rec: null, stream: null, chunks: [], btn: null, cb: null, t0: 0, tick: 0, busy: false, warmed: false };
  var pairs = [];

  function api(n) {
    var a = [].slice.call(arguments, 1), p = window.pywebview && window.pywebview.api;
    if (!p || !p[n]) return Promise.reject(new Error("not ready"));
    return p[n].apply(p, a);
  }
  function toast(m, k) { if (window.pxToast) window.pxToast(m, k); }
  function setVal(inp, v) { inp.value = v; inp.dispatchEvent(new Event("input", { bubbles: true })); }
  function setBtn(b, state, label) {
    b.classList.toggle("vx-rec", state === "rec");
    b.classList.toggle("vx-busy", state === "busy");
    b.innerHTML = ICON + (label ? '<span class="vx-lb">' + label + "</span>" : "");
  }

  /* ---- recording ---- */
  function start(btn, cb) {
    if (S.busy) return;
    if (S.rec) { stop(); return; }
    if (!navigator.mediaDevices || !window.MediaRecorder) { toast("Microphone is not available in this window", "warn"); return; }
    if (!S.warmed) { S.warmed = true; api("voice_warm").catch(function () {}); }
    navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 } })
      .then(function (stream) {
        var mt = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus"].filter(function (m) { return MediaRecorder.isTypeSupported(m); })[0];
        var rec = mt ? new MediaRecorder(stream, { mimeType: mt }) : new MediaRecorder(stream);
        S.rec = rec; S.stream = stream; S.chunks = []; S.btn = btn; S.cb = cb; S.t0 = Date.now();
        rec.ondataavailable = function (e) { if (e.data && e.data.size) S.chunks.push(e.data); };
        rec.onstop = finish;
        rec.start(250);
        setBtn(btn, "rec", "0:00");
        S.tick = setInterval(function () {
          var s = Math.floor((Date.now() - S.t0) / 1000);
          setBtn(btn, "rec", Math.floor(s / 60) + ":" + ("0" + (s % 60)).slice(-2));
          if (s >= 25) stop();
        }, 500);
        toast("Listening... press the mic again when you finish", "ok");
      })
      .catch(function (e) {
        var n = e && e.name;
        toast(n === "NotFoundError" ? "No microphone found"
          : "Microphone blocked. Windows Settings > Privacy > Microphone: allow desktop apps, then restart the app", "warn");
      });
  }
  function stop() { if (S.rec && S.rec.state !== "inactive") S.rec.stop(); }
  function finish() {
    clearInterval(S.tick);
    if (S.stream) S.stream.getTracks().forEach(function (t) { t.stop(); });
    var btn = S.btn, cb = S.cb, short = Date.now() - S.t0 < 600;
    var blob = new Blob(S.chunks, { type: (S.rec && S.rec.mimeType) || "audio/webm" });
    S.rec = null; S.stream = null;
    if (short || blob.size < 1500) { setBtn(btn, "idle"); toast("Too short - speak a little longer", "warn"); return; }
    S.busy = true; setBtn(btn, "busy", "...");
    api("voice_status").then(function (s) { if (!s.ready) toast(s.msg, "ok"); }).catch(function () {});
    var fr = new FileReader();
    fr.onload = function () {
      api("voice_transcribe", fr.result).then(function (r) {
        S.busy = false; setBtn(btn, "idle");
        if (!r || !r.ok || !r.text) { toast((r && r.error) || "I did not catch that", "warn"); return; }
        toast('Heard: "' + r.text + '"', "ok");
        cb(r.text);
      }).catch(function (e) { S.busy = false; setBtn(btn, "idle"); toast("Voice failed: " + (e && e.message || e), "warn"); });
    };
    fr.readAsDataURL(blob);
  }

  /* ---- command routing ---- */
  function route(t) {
    return api("voice_route", t).then(function (r) {
      (r.notes || []).forEach(function (n) { toast(n, "ok"); });
      return typeof r.rest === "string" ? r.rest : t;
    }).catch(function () { return t; });
  }

  function wire(b, inp) {
    var m = document.createElement("button");
    m.type = "button"; m.className = "vx-mic"; m.title = "Speak a command (Ctrl+Shift+M)"; m.innerHTML = ICON;
    b.parentNode.insertBefore(m, b);
    m.onclick = function (e) {
      e.preventDefault();
      start(m, function (t) { setVal(inp, (inp.value ? inp.value + " " : "") + t); inp.focus(); });
    };
    b.addEventListener("click", function (e) {
      if (b._vxPass) { b._vxPass = false; return; }
      var t = inp.value.trim();
      if (!t) return;
      e.stopImmediatePropagation(); e.preventDefault();
      route(t).then(function (rest) {
        if (rest) { setVal(inp, rest); b._vxPass = true; b.click(); }
        else setVal(inp, "");
      });
    }, true);
    inp.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey && !e.isComposing && inp.value.trim()) {
        e.preventDefault(); e.stopImmediatePropagation(); b.click();
      }
    }, true);
    pairs.push({ b: b, inp: inp });
  }

  function scan() {
    [].forEach.call(document.querySelectorAll("button"), function (b) {
      if (b.dataset.vx || b.classList.contains("vx-mic")) return;
      if (!/^send\b/i.test((b.textContent || "").trim())) return;
      var p = b.parentElement, inp = null;
      for (var i = 0; i < 5 && p && !inp; i++) {
        inp = p.querySelector("textarea,input[type=text],input:not([type])");
        p = p.parentElement;
      }
      if (!inp) return;
      b.dataset.vx = "1";
      wire(b, inp);
    });
  }
  function visiblePair() {
    for (var i = 0; i < pairs.length; i++) if (pairs[i].inp.offsetParent !== null) return pairs[i];
    return null;
  }

  function fab() {
    var b = document.createElement("button");
    b.id = "vx-fab"; b.type = "button"; b.title = "Voice command (Ctrl+Shift+M)"; b.innerHTML = ICON;
    document.body.appendChild(b);
    b.onclick = function () {
      start(b, function (t) {
        route(t).then(function (rest) {
          if (!rest) return;
          var p = visiblePair();
          if (p) { setVal(p.inp, (p.inp.value ? p.inp.value + " " : "") + rest); p.inp.focus(); toast("Press Send to apply it", "ok"); }
          else toast("Open the Director page and send this there: " + rest, "warn");
        });
      });
    };
    document.addEventListener("keydown", function (e) {
      if (e.ctrlKey && e.shiftKey && (e.key === "M" || e.key === "m")) { e.preventDefault(); b.click(); }
    });
  }

  function init() {
    var st = document.createElement("style"); st.textContent = CSS; document.head.appendChild(st);
    fab();
    scan();
    setInterval(scan, 1500);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
