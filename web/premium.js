/* MalixAris Premium look - auto-detects cards, pages and icons */
(function () {
  "use strict";

  var P = {
    copy: '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
    mic: '<path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><path d="M12 19v3"/>',
    music: '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
    play: '<polygon points="6 3 20 12 6 21 6 3"/>',
    check: '<path d="M20 6 9 17l-5-5"/>',
    sliders: '<path d="M4 7h16M4 17h16"/><circle cx="9" cy="7" r="2.2"/><circle cx="15" cy="17" r="2.2"/>',
    film: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7 3v18M17 3v18M3 8h4M3 16h4M17 8h4M17 16h4"/>',
    folder: '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>',
    bot: '<rect x="4" y="8" width="16" height="12" rx="3"/><path d="M12 8V4"/><circle cx="12" cy="3.5" r="1"/><circle cx="9" cy="14" r="1"/><circle cx="15" cy="14" r="1"/>',
    library: '<path d="M4 4v16M9 4v16"/><path d="m14 5 4-1 3 15-4 1Z"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
    undo: '<path d="M9 14 4 9l5-5"/><path d="M4 9h10a6 6 0 0 1 0 12h-3"/>',
    text: '<path d="M4 6h16M4 12h16M4 18h10"/>',
    key: '<circle cx="8" cy="15" r="4"/><path d="m11 12 9-9M16 7l3 3"/>',
    chat: '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12Z"/>',
    spark: '<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9Z"/><path d="M19 17v4M17 19h4"/>',
    timer: '<circle cx="12" cy="13" r="8"/><path d="M12 9v4l2 2M9 2h6"/>',
    down: '<path d="M12 3v12M7 10l5 5 5-5M4 21h16"/>',
    trash: '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
    stop: '<rect x="6" y="6" width="12" height="12" rx="2"/>',
    warn: '<path d="M12 3 2 20h20Z"/><path d="M12 10v5M12 18h.01"/>',
    cross: '<path d="M18 6 6 18M6 6l12 12"/>',
    lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>'
  };
  var MAP = {
    copy: "📋", mic: "🎤 🎙", music: "♫ ♪ 🎵 🎶", play: "▶ 🚀", check: "✓ ✔ ✅",
    sliders: "⚙ 🔧", film: "🎬 🎞 📽", folder: "📁 📂", bot: "🤖", library: "📚",
    info: "ℹ", undo: "↶ ↩", text: "📝", key: "🔑", chat: "💬", spark: "✨ 🧠",
    timer: "⏱ 🕒", down: "📤 💾", trash: "🗑", stop: "⏹", warn: "⚠",
    cross: "✕ ✖ ❌", lock: "🔒", search: "🔍"
  };
  var CH = {};
  Object.keys(MAP).forEach(function (n) {
    MAP[n].split(" ").forEach(function (c) { if (c) CH[c] = n; });
  });
  var RX = new RegExp("(" + Object.keys(CH).join("|") + ")\uFE0F?\\s*");

  function mkIcon(name) {
    var s = document.createElement("span");
    s.className = "px-ico";
    s.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true">' + (P[name] || P.spark) + "</svg>";
    return s;
  }

  function splitNode(t) {
    var m = RX.exec(t.nodeValue);
    if (!m || !t.parentNode) return;
    var before = t.nodeValue.slice(0, m.index);
    var after = t.nodeValue.slice(m.index + m[0].length);
    var f = document.createDocumentFragment();
    if (before) f.appendChild(document.createTextNode(before));
    f.appendChild(mkIcon(CH[m[1]]));
    var a = null;
    if (after) { a = document.createTextNode(after); f.appendChild(a); }
    t.parentNode.replaceChild(f, t);
    if (a) splitNode(a);
  }

  function icons() {
    var els = document.querySelectorAll("button,nav *,aside *,h1,h2,h3,[role=button]");
    for (var i = 0; i < els.length; i++) {
      var el = els[i];
      if (el.closest(".px-ico,textarea,script,style")) continue;
      var w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null);
      var nodes = [];
      while (w.nextNode()) nodes.push(w.currentNode);
      for (var j = 0; j < nodes.length; j++) {
        if (nodes[j].parentNode && !nodes[j].parentNode.closest(".px-ico")) splitNode(nodes[j]);
      }
    }
  }

  /* glass cards: big rounded boxes with a visible background */
  var seen = new WeakSet();
  function glass() {
    var els = document.body.querySelectorAll("div,section,article,aside,form,fieldset");
    for (var i = 0; i < els.length; i++) {
      var el = els[i];
      if (seen.has(el) || el.id === "px-toasts" || el.classList.contains("px-toast")) continue;
      var r = el.getBoundingClientRect();
      if (r.width < 180 || r.height < 50) continue;
      seen.add(el);
      if (r.height > innerHeight * 0.85) continue;
      if (r.width > innerWidth * 0.9 && r.height > innerHeight * 0.8) continue;
      if (el.parentElement && el.parentElement.closest(".px-glass")) continue;
      var cs = getComputedStyle(el);
      if ((parseFloat(cs.borderTopLeftRadius) || 0) < 6) continue;
      var m = /rgba?\(([^)]+)\)/.exec(cs.backgroundColor);
      if (!m) continue;
      var parts = m[1].split(",");
      var alpha = parts.length > 3 ? parseFloat(parts[3]) : 1;
      if (alpha < 0.3) continue;
      el.classList.add("px-glass");
    }
  }

  /* find the container holding all pages (most children hidden) */
  var attempts = 0;
  function pages() {
    if (document.querySelector(".px-page")) return;
    var all = document.body.querySelectorAll("div,main,section");
    for (var i = 0; i < all.length; i++) {
      var kids = [].filter.call(all[i].children, function (k) {
        return !/^(SCRIPT|STYLE|LINK|TEMPLATE)$/.test(k.tagName);
      });
      if (kids.length < 6) continue;
      var hidden = 0, big = 0;
      kids.forEach(function (k) {
        if (getComputedStyle(k).display === "none") hidden++;
        else {
          var r = k.getBoundingClientRect();
          if (r.width > innerWidth * 0.4 && r.height > 200) big++;
        }
      });
      if (hidden >= kids.length * 0.6 && big >= 1) {
        kids.forEach(function (k) { k.classList.add("px-page"); });
        return;
      }
    }
  }

  /* toasts */
  function toast(msg, kind) {
    var box = document.getElementById("px-toasts");
    if (!box) {
      box = document.createElement("div");
      box.id = "px-toasts";
      document.body.appendChild(box);
    }
    var t = document.createElement("div");
    t.className = "px-toast " + (kind || "ok");
    t.appendChild(mkIcon(kind === "err" || kind === "warn" ? "warn" : "check"));
    var s = document.createElement("span");
    s.textContent = String(msg);
    t.appendChild(s);
    box.appendChild(t);
    var life = 2600 + String(msg).length * 35;
    setTimeout(function () {
      t.classList.add("out");
      setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 380);
    }, life);
  }
  window.pxToast = toast;
  window.alert = function (m) { toast(m, "warn"); };
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      var oldCopy = navigator.clipboard.writeText.bind(navigator.clipboard);
      navigator.clipboard.writeText = function (t) { toast("Copied to clipboard", "ok"); return oldCopy(t); };
    }
  } catch (e) {}

  /* run now and whenever the page changes */
  var timer = 0, obs;
  function run() {
    try { icons(); glass(); if (attempts++ < 30) pages(); }
    catch (e) { console.warn("premium.js:", e); }
    if (obs) obs.takeRecords();
  }
  function sched() {
    if (timer) return;
    timer = setTimeout(function () { timer = 0; run(); }, 300);
  }
  function start() {
    run();
    obs = new MutationObserver(sched);
    obs.observe(document.body, {
      childList: true, subtree: true, attributes: true,
      attributeFilter: ["class", "style", "hidden"]
    });
    setTimeout(run, 800);
    setTimeout(run, 2500);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
