"""MalixAris Part 2C-2: captions + background music (both OFF by default)."""
import os, re, json, subprocess, urllib.request
import engine

DATA = os.path.join(engine.ROOT, "data")
FONT_DIR = os.path.join(DATA, "capfonts")
CFG = os.path.join(DATA, "finish.json")
os.makedirs(FONT_DIR, exist_ok=True)
GH = "https://github.com/google/fonts/raw/main/ofl/"
FONTS = {
    "Poppins": ("Poppins", True, [("Poppins-Bold.ttf", GH + "poppins/Poppins-Bold.ttf"),
                                  ("Poppins-Regular.ttf", GH + "poppins/Poppins-Regular.ttf")]),
    "Lato": ("Lato", True, [("Lato-Bold.ttf", GH + "lato/Lato-Bold.ttf"),
                            ("Lato-Regular.ttf", GH + "lato/Lato-Regular.ttf")]),
    "Anton": ("Anton", False, [("Anton-Regular.ttf", GH + "anton/Anton-Regular.ttf")]),
    "Bebas Neue": ("Bebas Neue", False, [("BebasNeue-Regular.ttf", GH + "bebasneue/BebasNeue-Regular.ttf")]),
    "Bangers": ("Bangers", False, [("Bangers-Regular.ttf", GH + "bangers/Bangers-Regular.ttf")]),
    "Arial": ("Arial", True, []),
    "Segoe UI": ("Segoe UI", True, []),
}
AUD = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus"}
DEFAULTS = {
    "captions": {"on": False, "font": "Poppins", "size": 5.5, "pos": "bottom", "color": "#FFFFFF",
                 "outline": "#000000", "words": 6, "upper": False, "box": False},
    "music": {"on": False, "path": "", "track": "", "volume": 12, "fade_in": 2.0, "fade_out": 3.0, "duck": True},
}


# ---------------------------------------------------------------- settings
def _num(v, lo, hi, dflt):
    try:
        return max(lo, min(hi, float(v)))
    except Exception:
        return dflt


def _hex(v, dflt):
    v = str(v or "").strip()
    return v if re.fullmatch(r"#[0-9a-fA-F]{6}", v) else dflt


def _clean(s):
    c, m = s["captions"], s["music"]
    c["on"] = bool(c["on"])
    c["font"] = c["font"] if c["font"] in FONTS else "Poppins"
    c["size"] = _num(c["size"], 3, 9, 5.5)
    c["pos"] = c["pos"] if c["pos"] in ("bottom", "middle", "top") else "bottom"
    c["color"] = _hex(c["color"], "#FFFFFF")
    c["outline"] = _hex(c["outline"], "#000000")
    c["words"] = int(_num(c["words"], 2, 10, 6))
    c["upper"], c["box"] = bool(c["upper"]), bool(c["box"])
    m["on"], m["duck"] = bool(m["on"]), bool(m["duck"])
    m["path"], m["track"] = str(m["path"] or "").strip(), str(m["track"] or "").strip()
    m["volume"] = _num(m["volume"], 0, 100, 12)
    m["fade_in"] = _num(m["fade_in"], 0, 10, 2)
    m["fade_out"] = _num(m["fade_out"], 0, 15, 3)
    return s


def load():
    s = {k: dict(v) for k, v in DEFAULTS.items()}
    try:
        with open(CFG, encoding="utf-8") as f:
            j = json.load(f)
        for sec in s:
            if isinstance(j.get(sec), dict):
                s[sec].update(j[sec])
    except Exception:
        pass
    return _clean(s)


def save(d):
    s = load()
    for sec in ("captions", "music"):
        if isinstance(d.get(sec), dict):
            s[sec].update(d[sec])
    s = _clean(s)
    with open(CFG, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2)
    return s


# ---------------------------------------------------------------- fonts
def ensure_font(name, log):
    fam, bold, files = FONTS.get(name) or FONTS["Arial"]
    for fn, url in files:
        dest = os.path.join(FONT_DIR, fn)
        if os.path.exists(dest) and os.path.getsize(dest) > 20000:
            continue
        try:
            log.info(f"Downloading caption font {fn} (one time)...")
            req = urllib.request.Request(url, headers={"User-Agent": "MalixAris"})
            with urllib.request.urlopen(req, timeout=40) as r:
                data = r.read()
            if len(data) < 20000:
                raise RuntimeError("file too small")
            with open(dest, "wb") as f:
                f.write(data)
        except Exception as e:
            log.warn(f"Could not download font {fn} ({str(e)[:80]}) - using Arial instead")
            return "Arial", True
    return fam, bold


# ---------------------------------------------------------------- captions
def build_chunks(entries, tt, adur, max_words, upper):
    words, k = [], 0
    for e in entries:
        first = True
        for w in e["text"].split():
            if engine.norm_tokens(w):
                t = tt[k] if k < len(tt) else None
                k += 1
                words.append([w, t, first])
                first = False
            elif words:
                words[-1][0] += " " + w
    prev = 0.0
    for w in words:
        if w[1] is None:
            w[1] = prev
        w[1] = max(float(w[1]), prev)
        prev = w[1]
    groups, cur = [], []
    for w, t, first in words:
        if cur and (first or len(cur) >= max_words or len(" ".join(x[0] for x in cur) + " " + w) > 48):
            groups.append(cur)
            cur = []
        cur.append((w, t))
        end = w.rstrip()[-1:]
        if end in ".!?\u2026" or (end in ",;:" and len(cur) >= 3):
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    out = []
    for i, g in enumerate(groups):
        start = g[0][1]
        nxt = groups[i + 1][0][1] if i + 1 < len(groups) else adur
        end = min(nxt, max(start + 0.35, g[-1][1] + 0.9))
        if nxt - end < 0.12:
            end = nxt
        end = min(end, adur)
        if end <= start + 0.1:
            end = min(adur, start + 0.25)
        text = " ".join(x[0] for x in g)
        text = text.replace("{", "(").replace("}", ")").replace("\\", "")
        out.append((text.upper() if upper else text, start, end))
    return out


def _col(h, alpha=0):
    h = h.lstrip("#")
    return f"&H{alpha:02X}{h[4:6]}{h[2:4]}{h[0:2]}".upper()


def _t(s):
    cs = int(round(max(0.0, s) * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    sec, cs = divmod(cs, 100)
    return f"{h}:{m:02}:{sec:02}.{cs:02}"


def write_ass(chunks, cap, W, H, path, log):
    fam, bold = ensure_font(cap["font"], log)
    px = round(H * cap["size"] / 100)
    align = {"bottom": 2, "middle": 5, "top": 8}[cap["pos"]]
    mv = 0 if cap["pos"] == "middle" else round(H * 0.07)
    ml = round(W * 0.08)
    if cap["box"]:
        style, outline, oc = 3, max(4, round(px * 0.28)), _col("#000000", 0x55)
    else:
        style, outline, oc = 1, max(2, round(px * 0.07)), _col(cap["outline"])
    lines = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}",
             "WrapStyle: 0", "ScaledBorderAndShadow: yes", "", "[V4+ Styles]",
             "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
             "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
             "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
             f"Style: Default,{fam},{px},{_col(cap['color'])},{_col(cap['color'])},{oc},{_col('#000000', 0x60)},"
             f"{-1 if bold else 0},0,0,0,100,100,0,0,{style},{outline},1,{align},{ml},{ml},{mv},1",
             "", "[Events]",
             "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    for text, a, b in chunks:
        lines.append(f"Dialogue: 0,{_t(a)},{_t(b)},Default,,0,0,0,,{{\\fad(60,40)}}{text}")
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines) + "\n")


def _rel(p):
    return os.path.relpath(p, engine.ROOT).replace("\\", "/")


def _run(cmd, ctl=None):
    if ctl:
        ctl.check()
    p = subprocess.Popen(cmd, cwd=engine.ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.PIPE, creationflags=engine.NO_WINDOW)
    if ctl:
        ctl.proc = p
    err = p.communicate()[1].decode("utf-8", "replace")
    if ctl:
        ctl.proc = None
        if ctl.cancel:
            raise engine.Cancelled()
    if p.returncode != 0:
        raise RuntimeError(err.strip()[-600:] or "ffmpeg failed")


# ---------------------------------------------------------------- music
def pick_music(m, log=None):
    p = (m.get("path") or "").strip()
    if p and os.path.isfile(p):
        return p
    if p and os.path.isdir(p):
        files = sorted(f for f in os.listdir(p) if os.path.splitext(f)[1].lower() in AUD)
        t = (m.get("track") or "").lower()
        if t:
            hit = [f for f in files if t in f.lower()]
            if hit:
                files = hit
        if files:
            return os.path.join(p, files[0])
    if log:
        log.warn("Music file or folder not found - rendering without music")
    return None


# ---------------------------------------------------------------- final mux
def _cmd(lst, audio, adur, out, cfg, ass, mus, m):
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
           "-i", audio]
    if mus:
        cmd += ["-stream_loop", "-1", "-i", mus]
    fc = []
    if ass:
        fc.append(f"[0:v]ass=filename={_rel(ass)}:fontsdir={_rel(FONT_DIR)}[v]")
    if mus:
        vol = m["volume"] / 100.0
        fi, fo = min(m["fade_in"], adur / 2), min(m["fade_out"], adur / 2)
        ch = f"[2:a]aresample=48000,atrim=duration={adur:.3f},asetpts=PTS-STARTPTS,volume={vol:.4f}"
        if fi > 0:
            ch += f",afade=t=in:st=0:d={fi:.2f}"
        if fo > 0:
            ch += f",afade=t=out:st={max(0.0, adur - fo):.2f}:d={fo:.2f}"
        fc.append(ch + "[m]")
        if m["duck"]:
            fc.append("[1:a]aresample=48000,asplit=2[v1][v2]")
            fc.append("[m][v2]sidechaincompress=threshold=0.03:ratio=5:attack=30:release=400[md]")
            fc.append("[v1][md]amix=inputs=2:duration=first:normalize=0[mx]")
        else:
            fc.append("[1:a]aresample=48000[v1]")
            fc.append("[v1][m]amix=inputs=2:duration=first:normalize=0[mx]")
        fc.append("[mx]alimiter=limit=0.97[a]")
    if fc:
        cmd += ["-filter_complex", ";".join(fc)]
    cmd += ["-map", "[v]" if ass else "0:v:0", "-map", "[a]" if mus else "1:a:0"]
    if ass:
        cmd += engine.enc_args(dict(cfg, preset="veryfast")) + ["-pix_fmt", "yuv420p"]
    else:
        cmd += ["-c:v", "copy"]
    cmd += ["-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-shortest", "-movflags", "+faststart", out]
    return cmd


def mux(segs, audio, adur, out_mp4, cfg, entries, tok_times, ctl, log, report, problems):
    lst = os.path.join(engine.WORK, "concat.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for s in segs:
            path = os.path.abspath(s).replace("\\", "/").replace("'", "'\\''")
            f.write(f"file '{path}'\n")
    st = load()
    cap, mc = st["captions"], st["music"]
    ass = mus = None
    if cap["on"]:
        try:
            chunks = build_chunks(entries, tok_times, adur, cap["words"], cap["upper"])
            if chunks:
                ass = os.path.join(engine.WORK, "captions.ass")
                write_ass(chunks, cap, cfg["W"], cfg["H"], ass, log)
                log.info(f"Captions ON: {len(chunks)} captions, font {cap['font']}")
        except Exception as e:
            ass = None
            log.warn(f"Captions skipped: {str(e)[:160]}")
    if mc["on"]:
        mus = pick_music(mc, log)
        if mus:
            log.info(f"Music ON: {os.path.basename(mus)} at {mc['volume']:.0f}%")
    combos = []
    for c in ((ass, mus), (None, mus), (ass, None), (None, None)):
        if c not in combos:
            combos.append(c)
    last = None
    for a, m in combos:
        if a or m:
            report("Adding captions and music", 96)
        try:
            _run(_cmd(lst, audio, adur, out_mp4, cfg, a, m, mc), ctl)
            if ass and not a:
                problems.append("Captions could not be added (see Logs). Use the .srt file in CapCut.")
            if mus and not m:
                problems.append("Music could not be added (see Logs).")
            return
        except engine.Cancelled:
            raise
        except Exception as e:
            last = e
            log.warn(f"Final step failed (captions={bool(a)}, music={bool(m)}): {str(e)[:220]}")
    raise RuntimeError(f"Could not create the final video: {last}")


# ---------------------------------------------------------------- Api methods
def preview(self):
    log = engine.Log()
    try:
        cap = load()["captions"]
        W, H = 1280, 720
        ass = os.path.join(engine.WORK, "preview.ass")
        write_ass([("This is how your captions will look", 0.0, 3.0)], cap, W, H, ass, log)
        out = os.path.join(DATA, "preview.png")
        _run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
              f"color=c=0x24203a:s={W}x{H}:d=2:r=25", "-vf",
              f"ass=filename={_rel(ass)}:fontsdir={_rel(FONT_DIR)}", "-ss", "1", "-frames:v", "1", out])
        return {"ok": True, "path": out}
    except Exception as e:
        log.warn(f"Caption preview failed: {str(e)[:200]}")
        return {"ok": False, "error": str(e)[:240]}


def finish_get(self):
    st = load()
    mp = pick_music(st["music"])
    return {"settings": st, "fonts": list(FONTS), "track": os.path.basename(mp) if mp else ""}


def finish_set(self, d):
    return {"ok": True, "settings": save(d or {})}


def install(api_class):
    api_class.finish_get = finish_get
    api_class.finish_set = finish_set
    api_class.finish_preview = preview
