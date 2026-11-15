"""MalixAris Polish & Export - Part 3B"""
import os, sys, re, json, time, glob, shutil, base64, threading, subprocess, functools

BASE = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
WORK = os.path.join(BASE, "work", "polish")
CFG = os.path.join(DATA, "polish.json")
NOWIN = 0x08000000 if os.name == "nt" else 0

GRADES = {"none": "None", "warm": "Warm", "cool": "Cool", "cinematic": "Cinematic",
          "vivid": "Vivid", "punchy": "Punchy", "soft": "Soft film", "bw": "Black & white"}
PRESETS = {"keep": "Same quality", "capcut": "CapCut-friendly",
           "youtube": "YouTube", "small": "Small file"}

DEFAULT = {
    "auto": False, "preset": "keep",
    "loud": {"on": False, "lufs": -14},
    "grade": {"name": "none", "amount": 70},
    "intro": {"on": False, "title": "", "sub": "", "secs": 3.0},
    "outro": {"on": False, "title": "Thanks for watching", "sub": "", "secs": 3.0},
    "bg": "#0b0b16", "fg": "#ffffff",
}

STATE = {"running": False, "pct": 0, "msg": "Ready", "out": "", "error": "", "log": []}
_proc = None
_cancel = False


# ---------- logging / settings ----------
def _log(msg):
    STATE["log"] = (STATE["log"] + [msg])[-12:]
    try:
        import engine
        engine.log(msg)
        return
    except Exception:
        pass
    try:
        os.makedirs(os.path.join(BASE, "logs"), exist_ok=True)
        with open(os.path.join(BASE, "logs", "app.log"), "a", encoding="utf-8") as f:
            f.write(time.strftime("%H:%M:%S") + " | " + msg + "\n")
    except Exception:
        pass


def _set(**kw):
    STATE.update(kw)


def _merge(base, patch):
    out = json.loads(json.dumps(base))
    for k, v in (patch or {}).items():
        if k not in out:
            continue
        if isinstance(out[k], dict):
            if isinstance(v, dict):
                for kk, vv in v.items():
                    if kk in out[k]:
                        out[k][kk] = vv
        else:
            out[k] = v
    return out


def _num(v, lo, hi, dflt):
    try:
        v = float(v)
    except Exception:
        v = dflt
    return max(lo, min(hi, v))


def _clean(c):
    c["auto"] = bool(c["auto"])
    if c["preset"] not in PRESETS:
        c["preset"] = "keep"
    c["loud"]["on"] = bool(c["loud"]["on"])
    c["loud"]["lufs"] = _num(c["loud"]["lufs"], -30, -8, -14)
    if c["grade"]["name"] not in GRADES:
        c["grade"]["name"] = "none"
    c["grade"]["amount"] = _num(c["grade"]["amount"], 0, 100, 70)
    for k in ("intro", "outro"):
        c[k]["on"] = bool(c[k]["on"])
        c[k]["title"] = str(c[k]["title"])[:120]
        c[k]["sub"] = str(c[k]["sub"])[:160]
        c[k]["secs"] = _num(c[k]["secs"], 1, 8, 3)
    for k, d in (("bg", "#0b0b16"), ("fg", "#ffffff")):
        if not re.match(r"^#[0-9a-fA-F]{6}$", str(c[k])):
            c[k] = d
    return c


def get():
    c = _merge(DEFAULT, {})
    try:
        with open(CFG, encoding="utf-8") as f:
            c = _merge(DEFAULT, json.load(f))
    except Exception:
        pass
    return _clean(c)


def save(patch):
    c = _clean(_merge(get(), patch))
    os.makedirs(DATA, exist_ok=True)
    with open(CFG, "w", encoding="utf-8") as f:
        json.dump(c, f, indent=2)
    return c


# ---------- ffmpeg helpers ----------
_FF = {}


def _tool(name):
    if name in _FF:
        return _FF[name]
    exe = name + (".exe" if os.name == "nt" else "")
    found = None
    for dp, _d, fs in os.walk(os.path.join(BASE, "tools", "ffmpeg")):
        if exe in fs:
            found = os.path.join(dp, exe)
            break
    _FF[name] = found or shutil.which(name) or name
    return _FF[name]


def _out(args, binary=False, timeout=None):
    kw = dict(capture_output=True, creationflags=NOWIN, timeout=timeout)
    if not binary:
        kw.update(text=True, encoding="utf-8", errors="replace")
    return subprocess.run(args, **kw)


def probe(path):
    r = _out([_tool("ffprobe"), "-v", "error", "-print_format", "json",
              "-show_streams", "-show_format", path])
    d = json.loads(r.stdout or "{}")
    st = d.get("streams", [])
    v = next((s for s in st if s.get("codec_type") == "video"), None)
    a = next((s for s in st if s.get("codec_type") == "audio"), None)
    if not v:
        raise RuntimeError("No video found in " + os.path.basename(path))
    fps_s, fps = "30", 30.0
    try:
        n, dn = (v.get("r_frame_rate") or "30/1").split("/")
        if float(dn) > 0 and 1 <= float(n) / float(dn) <= 240:
            fps, fps_s = float(n) / float(dn), "%s/%s" % (n, dn)
    except Exception:
        pass
    return {"w": int(v["width"]), "h": int(v["height"]), "fps": fps, "fps_s": fps_s,
            "has_audio": a is not None, "dur": float(d.get("format", {}).get("duration") or 0)}


_GPU = {}


def gpu():
    if "v" in _GPU:
        return _GPU["v"]
    found = ""
    try:
        enc = _out([_tool("ffmpeg"), "-hide_banner", "-encoders"]).stdout
        for e in ("h264_nvenc", "h264_qsv", "h264_amf"):
            if e in enc:
                t = _out([_tool("ffmpeg"), "-v", "error", "-f", "lavfi", "-i",
                          "color=s=256x256:d=0.2", "-c:v", e, "-f", "null", "-"],
                         binary=True, timeout=25)
                if t.returncode == 0:
                    found = e
                    break
    except Exception:
        pass
    _GPU["v"] = found
    return found


def enc_args(preset, info):
    crf, ab, px, gop = {"keep": (14, "256k", "fast", 0),
                        "capcut": (12, "320k", "fast", int(round(info["fps"]))),
                        "youtube": (16, "256k", "medium", 0),
                        "small": (24, "128k", "medium", 0)}[preset]
    g = gpu()
    if g == "h264_nvenc":
        v = ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", str(crf + 3), "-b:v", "0"]
    elif g == "h264_qsv":
        v = ["-c:v", "h264_qsv", "-global_quality", str(crf + 4), "-preset", "medium"]
    elif g == "h264_amf":
        v = ["-c:v", "h264_amf", "-quality", "quality", "-rc", "cqp",
             "-qp_i", str(crf + 4), "-qp_p", str(crf + 5)]
    else:
        v = ["-c:v", "libx264", "-preset", px, "-crf", str(crf)]
    v += ["-pix_fmt", "yuv420p"]
    if gop:
        v += ["-g", str(gop)]
    if info["has_audio"]:
        v += ["-c:a", "aac", "-b:a", ab, "-ar", "48000", "-ac", "2"]
    return v + ["-movflags", "+faststart"]


# ---------- grade + loudness ----------
def grade_filter(name, amount):
    k = max(0.0, min(100.0, float(amount))) / 100.0
    f = lambda x: "%.3f" % x
    if name == "warm":
        return ("colorbalance=rs=%s:rm=%s:bs=%s:bm=%s:bh=%s,eq=saturation=%s"
                % (f(.06 * k), f(.08 * k), f(-.06 * k), f(-.09 * k), f(-.04 * k), f(1 + .10 * k)))
    if name == "cool":
        return ("colorbalance=rs=%s:rm=%s:bs=%s:bm=%s,eq=saturation=%s"
                % (f(-.06 * k), f(-.08 * k), f(.07 * k), f(.09 * k), f(1 + .04 * k)))
    if name == "cinematic":
        return ("colorbalance=rs=%s:bs=%s:rh=%s:gh=%s:bh=%s,eq=contrast=%s:saturation=%s"
                % (f(-.08 * k), f(.10 * k), f(.10 * k), f(.02 * k), f(-.10 * k),
                   f(1 + .10 * k), f(1 + .08 * k)))
    if name == "vivid":
        return "eq=saturation=%s:contrast=%s" % (f(1 + .45 * k), f(1 + .06 * k))
    if name == "punchy":
        return ("eq=contrast=%s:saturation=%s,unsharp=5:5:%s:5:5:0.0"
                % (f(1 + .18 * k), f(1 + .12 * k), f(.5 * k)))
    if name == "soft":
        return ("eq=contrast=%s:saturation=%s:brightness=%s"
                % (f(1 - .10 * k), f(1 - .12 * k), f(.02 * k)))
    if name == "bw":
        return "hue=s=0,eq=contrast=1.080"
    return ""


def measure_loud(path, lufs):
    r = _out([_tool("ffmpeg"), "-hide_banner", "-nostats", "-i", path, "-vn", "-af",
              "loudnorm=I=%s:TP=-1.5:LRA=11:print_format=json" % lufs, "-f", "null", "-"])
    m = re.findall(r"\{[^{}]*\}", r.stderr or "", re.S)
    if not m:
        return None
    d = json.loads(m[-1])
    for key in ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset"):
        float(d[key])
        if d[key] in ("-inf", "inf", "nan"):
            return None
    return d


def loud_filter(lufs, m):
    return ("loudnorm=I=%s:TP=-1.5:LRA=11:measured_I=%s:measured_LRA=%s:measured_TP=%s:"
            "measured_thresh=%s:offset=%s:linear=true"
            % (lufs, m["input_i"], m["input_lra"], m["input_tp"], m["input_thresh"], m["target_offset"]))


# ---------- title cards ----------
def _hex(c):
    return "0x" + c.lstrip("#")


def _font():
    for p in (os.path.join(DATA, "capfonts", "Poppins-Bold.ttf"), r"C:\Windows\Fonts\segoeuib.ttf",
              r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\arial.ttf"):
        if os.path.isfile(p):
            return p
    return ""


def _drawtext(kind, c, cfg, W, H):
    font = _font()
    if font:
        shutil.copy(font, os.path.join(WORK, "font.ttf"))
    fpart = "fontfile=font.ttf:" if font else ""
    items = []
    if c["title"].strip():
        items.append(("%s_t.txt" % kind, c["title"].strip(), int(H * 0.085)))
    if c["sub"].strip():
        items.append(("%s_s.txt" % kind, c["sub"].strip(), int(H * 0.042)))
    rows, total = [], 0.0
    for fn, text, sz in items:
        lines = text.split("\n")
        longest = max(len(x) for x in lines)
        s = max(12, min(sz, int(W * 0.88 / (max(longest, 1) * 0.58))))
        bh = len(lines) * s * 1.3
        rows.append((fn, text, s, bh))
        total += bh + H * 0.03
    total -= H * 0.03
    y = H * 0.5 - total / 2
    out = []
    for fn, text, s, bh in rows:
        with open(os.path.join(WORK, fn), "w", encoding="utf-8") as f:
            f.write(text)
        col = _hex(cfg["fg"]) + ("@0.75" if fn.endswith("_s.txt") else "")
        out.append("drawtext=%stextfile=%s:fontsize=%d:fontcolor=%s:x=(w-text_w)/2:y=%d:line_spacing=%d"
                   % (fpart, fn, s, col, int(y), int(s * 0.15)))
        y += bh + H * 0.03
    return "".join(o + "," for o in out)


def _cards_on(cfg):
    return any(cfg[k]["on"] and (cfg[k]["title"].strip() or cfg[k]["sub"].strip())
               for k in ("intro", "outro"))


def _build(src, dst, cfg, info, meas, use_cards):
    W, H = info["w"], info["h"]
    pr = cfg["preset"]
    scale = ""
    if pr == "small" and H > 1080:
        W, H = int(round(W * 1080 / H / 2.0)) * 2, 1080
        scale = "scale=%d:%d" % (W, H)
    cmd = [_tool("ffmpeg"), "-hide_banner", "-y", "-nostats", "-progress", "pipe:1", "-i", src]
    fc = []
    vf = [x for x in (scale, grade_filter(cfg["grade"]["name"], cfg["grade"]["amount"])) if x]
    fc.append("[0:v]%sformat=yuv420p,setsar=1[vm]" % "".join(x + "," for x in vf))
    AF = "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"
    if info["has_audio"]:
        pre = (loud_filter(cfg["loud"]["lufs"], meas) + ",") if meas else ""
        fc.append("[0:a]%s%s[am]" % (pre, AF))
    cards, idx, extra = {}, 1, 0.0
    if use_cards:
        for kind in ("intro", "outro"):
            c = cfg[kind]
            if not (c["on"] and (c["title"].strip() or c["sub"].strip())):
                continue
            secs, vi, ai = c["secs"], idx, idx + 1
            idx += 2
            cards[kind] = vi
            cmd += ["-f", "lavfi", "-i", "color=c=%s:s=%dx%d:r=%s:d=%.2f"
                    % (_hex(cfg["bg"]), W, H, info["fps_s"], secs)]
            cmd += ["-f", "lavfi", "-t", "%.2f" % secs, "-i", "anullsrc=r=48000:cl=stereo"]
            fc.append("[%d:v]%sfade=t=in:st=0:d=0.5,fade=t=out:st=%.2f:d=0.5,format=yuv420p,setsar=1[cv%d]"
                      % (vi, _drawtext(kind, c, cfg, W, H), secs - 0.5, vi))
            if info["has_audio"]:
                fc.append("[%d:a]%s[ca%d]" % (ai, AF, vi))
            extra += secs
    order = []
    if "intro" in cards:
        order.append(("[cv%d]" % cards["intro"], "[ca%d]" % cards["intro"]))
    order.append(("[vm]", "[am]"))
    if "outro" in cards:
        order.append(("[cv%d]" % cards["outro"], "[ca%d]" % cards["outro"]))
    ha = info["has_audio"]
    if len(order) == 1:
        vmap, amap = "[vm]", ("[am]" if ha else None)
    elif ha:
        fc.append("".join(v + a for v, a in order) + "concat=n=%d:v=1:a=1[vo][ao]" % len(order))
        vmap, amap = "[vo]", "[ao]"
    else:
        fc.append("".join(v for v, a in order) + "concat=n=%d:v=1:a=0[vo]" % len(order))
        vmap, amap = "[vo]", None
    cmd += ["-filter_complex", ";".join(fc), "-map", vmap]
    if amap:
        cmd += ["-map", amap]
    cmd += enc_args(pr, info) + [dst]
    return cmd, info["dur"] + extra


def _encode(cmd, total):
    global _proc
    _proc = subprocess.Popen(cmd, cwd=WORK, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, encoding="utf-8", errors="replace", creationflags=NOWIN)
    tail = []
    for line in _proc.stdout:
        line = line.strip()
        m = re.match(r"out_time_(?:us|ms)=(\d+)", line)
        if m:
            _set(pct=min(99, int(100 * (int(m.group(1)) / 1e6) / max(total, 0.1))))
        elif line and not re.match(r"^[a-z_0-9]+=", line):
            tail.append(line)
    rc = _proc.wait()
    return rc, tail[-6:]


def _need(cfg):
    return (cfg["loud"]["on"] or cfg["grade"]["name"] != "none" or cfg["preset"] != "keep"
            or _cards_on(cfg))


def _worker(src, cfg):
    global _cancel
    _cancel = False
    t0 = time.time()
    part = ""
    try:
        os.makedirs(WORK, exist_ok=True)
        _set(running=True, pct=0, msg="Reading video...", out="", error="")
        info = probe(src)
        meas = None
        if cfg["loud"]["on"] and info["has_audio"]:
            _set(msg="Measuring loudness...")
            try:
                meas = measure_loud(src, cfg["loud"]["lufs"])
            except Exception:
                meas = None
            if not meas:
                _log("Polish: could not measure loudness - normalize skipped")
        dst = os.path.splitext(src)[0] + "_polished.mp4"
        part = dst[:-4] + ".part.mp4"
        _set(msg="Polishing...")
        ok, tail = False, []
        for cards in ((True, False) if _cards_on(cfg) else (False,)):
            cmd, total = _build(src, part, cfg, info, meas, cards)
            rc, tail = _encode(cmd, total)
            if _cancel:
                raise RuntimeError("Cancelled")
            if rc == 0 and os.path.isfile(part):
                ok = True
                break
            _log("Polish: FFmpeg problem: " + " | ".join(tail[-2:]))
            if cards:
                _log("Polish: retrying without title cards")
        if not ok:
            raise RuntimeError("FFmpeg failed: " + " | ".join(tail[-3:]))
        os.replace(part, dst)
        _set(running=False, pct=100, out=dst, msg="Done in %d s" % (time.time() - t0))
        _log("Polish: saved " + dst)
    except Exception as e:
        _set(running=False, error=str(e), msg="Failed")
        _log("Polish: " + str(e))
        try:
            if part and os.path.isfile(part):
                os.remove(part)
        except Exception:
            pass


# ---------- finding videos ----------
def _out_dirs():
    ds = [os.path.join(BASE, "output")]
    try:
        with open(os.path.join(DATA, "settings.json"), encoding="utf-8") as f:
            for k, v in json.load(f).items():
                if "out" in k.lower() and isinstance(v, str) and os.path.isdir(v):
                    ds.append(v)
    except Exception:
        pass
    return ds


def latest(since=0):
    best = None
    for d in _out_dirs():
        for f in glob.glob(os.path.join(d, "*.mp4")):
            low = f.lower()
            if low.endswith("_polished.mp4") or ".part." in low:
                continue
            m = os.path.getmtime(f)
            if m >= since and (best is None or m > best[0]):
                best = (m, f)
    return best[1] if best else ""


def run(path=""):
    if STATE["running"]:
        return {"ok": False, "error": "Already running"}
    cfg = get()
    path = path or latest()
    if not path or not os.path.isfile(path):
        return {"ok": False, "error": "No video found - render first or pick a file"}
    if path.lower().endswith("_polished.mp4"):
        return {"ok": False, "error": "That file is already polished - pick the original"}
    if not _need(cfg):
        return {"ok": False, "error": "Turn on at least one tool first"}
    _set(running=True, pct=0, msg="Starting...", out="", error="")
    threading.Thread(target=_worker, args=(path, cfg), daemon=True).start()
    return {"ok": True, "path": path}


def cancel():
    global _cancel
    _cancel = True
    try:
        if _proc and _proc.poll() is None:
            _proc.kill()
    except Exception:
        pass


def preview(src):
    try:
        cfg = get()
        info = probe(src)
        vf = [x for x in (grade_filter(cfg["grade"]["name"], cfg["grade"]["amount"]), "scale=640:-2") if x]
        r = _out([_tool("ffmpeg"), "-v", "error", "-ss", "%.2f" % min(1.0, info["dur"] / 2), "-i", src,
                  "-frames:v", "1", "-vf", ",".join(vf), "-f", "image2pipe", "-vcodec", "png", "-"],
                 binary=True, timeout=40)
        if r.returncode != 0 or not r.stdout:
            return {"ok": False, "error": "Could not make a preview frame"}
        return {"ok": True, "img": "data:image/png;base64," + base64.b64encode(r.stdout).decode()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------- hooks ----------
def _wrap_engine():
    try:
        import engine
        orig = getattr(engine, "run_job", None)
        if not orig or getattr(orig, "_pl", False):
            return

        @functools.wraps(orig)
        def run_job(*a, **k):
            t0 = time.time()
            res = orig(*a, **k)
            try:
                if get()["auto"]:
                    f = latest(t0 - 2)
                    if f:
                        _log("Polish: auto-polishing " + os.path.basename(f))
                        r = run(f)
                        if not r.get("ok"):
                            _log("Polish: " + r.get("error", ""))
            except Exception as e:
                _log("Polish: auto step failed: %s" % e)
            return res

        run_job._pl = True
        engine.run_job = run_job
    except Exception as e:
        _log("Polish: auto hook not attached (%s) - use the Polish button" % e)


def install(Api):
    def polish_get(self):
        return get()

    def polish_save(self, patch):
        return save(patch or {})

    def polish_run(self, path=""):
        return run(path)

    def polish_cancel(self):
        cancel()
        return True

    def polish_status(self):
        return dict(STATE)

    def polish_latest(self):
        return latest()

    def polish_preview(self, path=""):
        p = path or latest()
        return preview(p) if p and os.path.isfile(p) else {"ok": False, "error": "No video selected"}

    def polish_pick(self):
        import webview
        try:
            kind = webview.FileDialog.OPEN
        except AttributeError:
            kind = webview.OPEN_DIALOG
        r = webview.windows[0].create_file_dialog(
            kind, allow_multiple=False, file_types=("Video files (*.mp4;*.mov;*.mkv)",))
        return r[0] if r else ""

    def polish_open(self, path=""):
        try:
            if path and os.path.isfile(path):
                subprocess.Popen(["explorer", "/select," + os.path.normpath(path)])
            return True
        except Exception:
            return False

    for fn in (polish_get, polish_save, polish_run, polish_cancel, polish_status,
               polish_latest, polish_preview, polish_pick, polish_open):
        setattr(Api, fn.__name__, fn)
    _wrap_engine()
