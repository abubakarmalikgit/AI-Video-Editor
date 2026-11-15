"""MalixAris Video Maker - engine (Part 1). Made by MalixAris & Usman Mughal."""
import os, sys, re, json, time, hashlib, subprocess, unicodedata, difflib, threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(ROOT, "work")
CACHE = os.path.join(WORK, "cache")
TRANS = os.path.join(WORK, "transcripts")
OUT = os.path.join(ROOT, "output")
LOGS = os.path.join(ROOT, "logs")
for _d in (CACHE, TRANS, OUT, LOGS):
    os.makedirs(_d, exist_ok=True)

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


class Cancelled(Exception):
    pass


class NullLog:
    def info(self, m): pass
    def warn(self, m): pass
    def error(self, m): pass


class Log:
    def __init__(self):
        self.items = []
        self.lock = threading.Lock()
        self.path = os.path.join(LOGS, "app.log")

    def add(self, level, msg):
        line = {"t": time.strftime("%H:%M:%S"), "level": level, "msg": msg}
        with self.lock:
            self.items.append(line)
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(f"{line['t']} [{level}] {msg}\n")
        except Exception:
            pass

    def info(self, m): self.add("info", m)
    def warn(self, m): self.add("warn", m)
    def error(self, m): self.add("error", m)

    def since(self, i):
        with self.lock:
            return list(self.items[i:]), len(self.items)


class Ctl:
    def __init__(self):
        self.cancel = False
        self.proc = None

    def reset(self):
        self.cancel = False
        self.proc = None

    def check(self):
        if self.cancel:
            raise Cancelled()

    def stop(self):
        self.cancel = True
        p = self.proc
        if p and p.poll() is None:
            try:
                p.kill()
            except Exception:
                pass


# ------------------------------------------------------------------ helpers
def sysreport():
    try:
        with open(os.path.join(ROOT, "system_report.json")) as f:
            return json.load(f)
    except Exception:
        return {"video_encoder": "libx264", "whisper_device": "cpu",
                "whisper_compute_type": "int8", "whisper_model": "small"}


def run_ff(cmd, ctl):
    ctl.check()
    p = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.PIPE, creationflags=NO_WINDOW)
    ctl.proc = p
    err = p.communicate()[1].decode("utf-8", "replace")
    ctl.proc = None
    if ctl.cancel:
        raise Cancelled()
    if p.returncode != 0:
        raise RuntimeError(err.strip()[-700:] or "ffmpeg failed")


def _frac(s):
    try:
        a, b = str(s).split("/")
        return float(a) / float(b) if float(b) else 0.0
    except Exception:
        try:
            return float(s)
        except Exception:
            return 0.0


def probe(path):
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
           "stream=width,height,avg_frame_rate,r_frame_rate:format=duration", "-of", "json", path]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       creationflags=NO_WINDOW, timeout=60)
    d = json.loads(r.stdout or "{}")
    s = d["streams"][0]
    fps = _frac(s.get("avg_frame_rate")) or _frac(s.get("r_frame_rate"))
    try:
        dur = float(d["format"]["duration"])
    except Exception:
        dur = None
    return {"w": int(s["width"]), "h": int(s["height"]), "fps": fps, "dur": dur}


def audio_duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", path],
                       capture_output=True, text=True, creationflags=NO_WINDOW, timeout=60)
    return float(r.stdout.strip())


def ts_srt(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


# ------------------------------------------------------------------ library
def scan_library(folder, log):
    """Scan every supported media file. Numbered names keep their IDs; unnumbered
    files receive deterministic free IDs so the library count matches the folder."""
    lib = {"videos": {}, "images": {}, "bad": []}
    seen = {"video": set(), "image": set()}
    candidates = []
    try:
        names = sorted(os.listdir(folder), key=lambda x: x.casefold())
    except OSError as e:
        log.error(f"Cannot read clips folder: {e}")
        return lib
    unnumbered = []
    for fn in names:
        stem, ext = os.path.splitext(fn)
        ext = ext.lower()
        if ext not in VIDEO_EXT and ext not in IMAGE_EXT:
            continue
        # Do not accidentally import a previous render placed beside source clips.
        # Unnumbered genuine source footage is still included and assigned a stable ID.
        low_name = fn.casefold()
        generated_names = {"final.mp4", "output.mp4", "render.mp4", "rendered.mp4",
                           "preview.mp4", "merged.mp4", "combined.mp4", "export.mp4"}
        if low_name in generated_names or low_name.startswith("malixaris_"):
            log.info(f"Ignored previous render in source folder: '{fn}'")
            continue
        kind = "video" if ext in VIDEO_EXT else "image"
        m = re.search(r"\d+", stem)
        if not m:
            unnumbered.append((kind, fn))
            continue
        num = int(m.group())
        if num in seen[kind]:
            log.warn(f"Duplicate {kind} ID {num:03d}: '{fn}' retained under a new library ID")
            unnumbered.append((kind, fn))
            continue
        seen[kind].add(num)
        candidates.append((kind, num, os.path.join(folder, fn)))
    # Preserve explicit IDs; allocate unnumbered/duplicate files after the largest explicit ID.
    for kind, fn in unnumbered:
        num = max(seen[kind], default=0) + 1
        while num in seen[kind]:
            num += 1
        seen[kind].add(num)
        candidates.append((kind, num, os.path.join(folder, fn)))
        log.info(f"Assigned library ID {num:03d} to unnumbered file '{fn}'")

    def work(j):
        try:
            return j, probe(j[2]), None
        except Exception as e:
            return j, None, str(e)[:160]

    with ThreadPoolExecutor(4) as ex:
        results = list(ex.map(work, candidates))
    for (kind, num, path), info, err in results:
        if info is None:
            lib["bad"].append(f"{os.path.basename(path)}: {err}")
            log.error(f"Cannot read {os.path.basename(path)}: {err}")
            continue
        info.update(kind=kind, num=num, path=path, filename=os.path.basename(path))
        lib["videos" if kind == "video" else "images"][num] = info
    log.info(f"Library scanned: {len(lib['videos'])} videos, {len(lib['images'])} images, {len(lib['bad'])} unreadable")
    return lib


def lib_summary(lib):
    v, im = lib["videos"], lib["images"]
    s = {"videos": len(v), "images": len(im), "bad": lib["bad"][:20], "bad_count": len(lib["bad"])}
    if v:
        sizes = Counter((a["w"], a["h"]) for a in v.values())
        (w, h), _ = sizes.most_common(1)[0]
        fps = Counter(round(a["fps"], 2) for a in v.values()).most_common(1)[0][0]
        durs = [a["dur"] for a in v.values() if a["dur"]]
        nums = sorted(v)
        gaps = [n for n in range(nums[0], nums[-1] + 1) if n not in v]
        s.update(w=w, h=h, fps=fps, odd=sum(c for k, c in sizes.items() if k != (w, h)),
                 dur_min=round(min(durs), 2) if durs else 0, dur_max=round(max(durs), 2) if durs else 0,
                 range=[nums[0], nums[-1]], gaps=gaps[:40], gap_count=len(gaps))
    return s


# ------------------------------------------------------------------ script
KIND = r"(?:clip|image|img|video|vid|mp4)"
TOKEN_RE = re.compile(rf"({KIND})?\s*#?\s*(\d+)", re.I)
SPLIT_RE = re.compile(r"^\s*([^:|=]{1,60}?)\s*[:|=]\s*(.+?)\s*$")
NUMBERED_LINE_RE = re.compile(r"^\s*((?:(?:clip|video|image|img)\s*)?#?\d+(?:\s*(?:\+|,|&)\s*(?:(?:clip|video|image|img)\s*)?#?\d+)*)\s*[.)\-–—:]\s*(.+?)\s*$", re.I)
SENT_RE = re.compile(r"(?<=[.!?\u0964\u061f])\s+")


def parse_left(left):
    rest = TOKEN_RE.sub("", left)
    if re.sub(r"[\s+&,]", "", rest):
        return None
    toks, kind = [], None
    for m in TOKEN_RE.finditer(left):
        w = (m.group(1) or "").lower()
        if w:
            kind = "image" if w in ("image", "img") else "video"
        toks.append((kind or "video", int(m.group(2))))
    return toks or None


def parse_script(text, log):
    lines = [l.strip() for l in text.replace("\r", "").split("\n")]
    lines = [l for l in lines if l]
    parsed = []
    for l in lines:
        m = SPLIT_RE.match(l)
        if m:
            refs = parse_left(m.group(1))
            parsed.append((refs, m.group(2) if refs else l))
            continue
        m = NUMBERED_LINE_RE.match(l)
        refs = parse_left(m.group(1)) if m else None
        parsed.append((refs, m.group(2) if refs else l))
    nmap = sum(1 for r, _ in parsed if r)
    entries = []
    if lines and nmap >= max(1, len(lines) * 0.5):
        mode = "manual"
        for refs, t in parsed:
            if refs:
                entries.append({"refs": refs, "text": t})
            elif entries:
                entries[-1]["text"] += " " + t
                log.info("A line without a number was joined to the previous line")
            else:
                log.warn("A line before the first numbered line was ignored")
    else:
        mode = "auto"
        for l in lines:
            buf = ""
            for s in [x for x in SENT_RE.split(l) if x.strip()]:
                buf = (buf + " " + s).strip()
                if len(buf.split()) >= 6:
                    entries.append({"refs": [], "text": buf})
                    buf = ""
            if buf:
                if entries and len(buf.split()) < 3 and not entries[-1]["refs"]:
                    entries[-1]["text"] += " " + buf
                else:
                    entries.append({"refs": [], "text": buf})
    for i, e in enumerate(entries, 1):
        e["idx"] = i
    return mode, entries


def inspect(opts, lib):
    out = {"ok": True, "clips": lib_summary(lib) if lib else None, "script": None}
    txt = opts.get("script", "")
    if txt.strip():
        mode, entries = parse_script(txt, NullLog())
        info = {"mode": mode, "lines": len(entries), "missing": []}
        if mode == "manual" and lib:
            miss = set()
            for e in entries:
                for _, n in e["refs"]:
                    if n not in lib["videos"] and n not in lib["images"]:
                        miss.add(n)
            info["missing"] = sorted(miss)
        out["script"] = info
    return out


# ------------------------------------------------------------------ audio -> words
def _add_cuda_dlls():
    try:
        import nvidia
        for p in nvidia.__path__:
            for sub in os.listdir(p):
                b = os.path.join(p, sub, "bin")
                if os.path.isdir(b):
                    os.add_dll_directory(b)
                    os.environ["PATH"] = b + os.pathsep + os.environ["PATH"]
    except Exception:
        pass


def transcribe(audio, lang, model_name, device, compute, adur, log, progress, ctl):
    key = hashlib.sha1(f"{audio}|{os.path.getmtime(audio)}|{os.path.getsize(audio)}|{model_name}|{lang}".encode()).hexdigest()[:16]
    cache = os.path.join(TRANS, key + ".json")
    if os.path.exists(cache):
        log.info("Transcript found in cache - skipping speech recognition")
        with open(cache, encoding="utf-8") as f:
            return json.load(f)
    from faster_whisper import WhisperModel
    if device == "cuda":
        _add_cuda_dlls()
    attempts = [(device, compute)] + ([("cpu", "int8")] if device == "cuda" else [])
    last_err = None
    for dev, comp in attempts:
        try:
            log.info(f"Loading Whisper model '{model_name}' on {dev} (first time it downloads the model)...")
            model = WhisperModel(model_name, device=dev, compute_type=comp)
            segs, info = model.transcribe(audio, language=lang or None, word_timestamps=True,
                                          beam_size=1, vad_filter=False, condition_on_previous_text=False)
            words = []
            for seg in segs:
                ctl.check()
                for w in (seg.words or []):
                    words.append({"w": w.word, "s": float(w.start), "e": float(w.end)})
                progress(min(1.0, seg.end / max(adur, 0.1)))
            data = {"language": info.language, "words": words}
            with open(cache, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            log.info(f"Speech recognised: language={info.language}, {len(words)} words")
            return data
        except Cancelled:
            raise
        except Exception as e:
            last_err = e
            log.warn(f"Whisper on {dev} failed ({str(e)[:150]}) - trying fallback")
    raise RuntimeError(f"Speech recognition failed: {last_err}")


def norm_tokens(text):
    out = []
    for w in text.split():
        t = "".join(ch for ch in w.lower() if unicodedata.category(ch)[0] not in "PSC")
        if t:
            out.append(t)
    return out


def align_lines(entries, words, adur, log):
    """Returns the start time (seconds) of every script line."""
    s_tok, first = [], []
    for e in entries:
        toks = norm_tokens(e["text"])
        first.append(len(s_tok) if toks else None)
        s_tok += toks
    asr = [(norm_tokens(w["w"]), w) for w in words]
    asr = [(t[0] if t else "", w) for t, w in asr]
    asr = [(t, w) for t, w in asr if t]
    a_tok = [t for t, _ in asr]
    n = len(s_tok)
    if n == 0 or not a_tok:
        raise RuntimeError("Nothing to align (empty script or no speech found)")
    sm = difflib.SequenceMatcher(None, s_tok, a_tok, autojunk=False)
    tt = [None] * n
    matched = 0
    for a, b, size in sm.get_matching_blocks():
        for k in range(size):
            tt[a + k] = asr[b + k][1]["s"]
            matched += 1
    cov = matched / n
    log.info(f"Script/audio match: {cov * 100:.0f}% of words")
    if cov < 0.5:
        log.warn("The script does not match the voiceover well. Check that the script and audio are the same text/language.")
    anchors = [(-1, 0.0)] + [(i, t) for i, t in enumerate(tt) if t is not None] + [(n, min(adur, asr[-1][1]["e"]))]
    j = 0
    for i in range(n):
        if tt[i] is not None:
            continue
        while anchors[j + 1][0] < i:
            j += 1
        (i0, t0), (i1, t1) = anchors[j], anchors[j + 1]
        tt[i] = t0 + (t1 - t0) * (i - i0) / max(1, (i1 - i0))
    align_lines.last_tt = list(tt)
    raw = []
    for f in first:
        raw.append(tt[f] if f is not None else None)
    # lines with no words take the next line's start
    nxt = adur
    for i in range(len(raw) - 1, -1, -1):
        if raw[i] is None:
            raw[i] = nxt
        nxt = raw[i]
    return raw, cov


# ------------------------------------------------------------------ planning
def snap_fps(f):
    for s in (24, 25, 30, 50, 60):
        if abs(f - s) < 0.6:
            return s
    return int(round(f)) or 30


def make_cfg(opts, lib, sysr):
    vids = list(lib["videos"].values()) or list(lib["images"].values())
    (cw, ch), _ = Counter((a["w"], a["h"]) for a in vids).most_common(1)[0]
    res = str(opts.get("res", "original"))
    if res == "original":
        W, H = cw, ch
    else:
        H = int(res.replace("p", ""))
        W = int(round(H * cw / ch))
    W, H = W // 2 * 2, H // 2 * 2
    fps_opt = str(opts.get("fps", "auto"))
    if fps_opt == "auto":
        fl = [a["fps"] for a in lib["videos"].values() if a["fps"] > 0]
        fps = snap_fps(Counter(round(f, 2) for f in fl).most_common(1)[0][0]) if fl else 30
    else:
        fps = int(fps_opt)
    crf = {"max": 12, "high": 16, "balanced": 20}.get(opts.get("quality", "high"), 16)
    return {"W": W, "H": H, "fps": fps, "crf": crf, "preset": "fast",
            "encoder": sysr.get("video_encoder", "libx264"),
            "fit": opts.get("fit", "blur"), "smooth": opts.get("smooth", "off")}


def split_count(L, k):
    n = 1 if L <= 8.0 else max(2, int(L / 5.0 + 0.5))
    return max(n, k)


def make_piece(asset, frames, fps):
    dur = frames / fps
    p = {"kind": asset["kind"], "path": asset["path"], "num": asset["num"],
         "w": asset["w"], "h": asset["h"], "frames": frames, "asset": asset}
    if asset["kind"] == "image":
        p.update(speed=1.0, use=dur)
    else:
        c = asset["dur"] or 5.0
        speed = max(0.5, min(2.0, c / dur))
        p.update(speed=speed, use=min(c, dur * speed))
    return p


def enc_args(cfg):
    e = cfg["encoder"]
    if e == "h264_nvenc":
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "17", "-b:v", "0"]
    if e == "h264_qsv":
        return ["-c:v", "h264_qsv", "-global_quality", "17", "-preset", "slower"]
    if e == "h264_amf":
        return ["-c:v", "h264_amf", "-quality", "quality", "-rc", "cqp", "-qp_i", "17", "-qp_p", "17", "-qp_b", "17"]
    return ["-c:v", "libx264", "-preset", cfg["preset"], "-crf", str(cfg["crf"])]


def piece_cmd(p, cfg, out):
    W, H, fps, fit = cfg["W"], cfg["H"], cfg["fps"], cfg["fit"]
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    pre = []
    if p["kind"] == "video":
        cmd += ["-t", f"{p['use']:.4f}", "-i", p["path"]]
        if abs(p["speed"] - 1.0) > 0.001:
            pre.append(f"setpts=PTS/{p['speed']:.5f}")
        if cfg["smooth"] == "blend" and p["speed"] < 0.98:
            pre.append(f"framerate=fps={fps}")
        else:
            pre.append(f"fps={fps}")
        pre.append("tpad=stop=-1:stop_mode=clone")
    else:
        cmd += ["-loop", "1", "-framerate", str(fps), "-i", p["path"]]
        pre.append(f"fps={fps}")
    skip, take = p.get("skip", 0), p.get("take", p["frames"])
    if skip > 0 or take < p["frames"]:
        pre.append(f"trim=start_frame={skip}:end_frame={skip + take},setpts=PTS-STARTPTS")
    chain = ",".join(pre)
    tail = "setsar=1,format=yuv420p"
    if (p["w"], p["h"]) == (W, H):
        g = f"[0:v]{chain},{tail}[v]"
    elif fit == "crop":
        g = (f"[0:v]{chain},scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,"
             f"crop={W}:{H},{tail}[v]")
    elif fit == "bars":
        g = (f"[0:v]{chain},scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos,"
             f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black,{tail}[v]")
    else:
        g = (f"[0:v]{chain},split[a][b];"
             f"[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=25:5[bg];"
             f"[b]scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos[fg];"
             f"[bg][fg]overlay=(W-w)/2:(H-h)/2,{tail}[v]")
    cmd += ["-filter_complex", g, "-map", "[v]", "-frames:v", str(p.get("take", p["frames"])), "-an"]
    cmd += enc_args(cfg) + ["-pix_fmt", "yuv420p", "-r", str(fps), "-f", "mpegts", out]
    return cmd


def piece_key(p, cfg):
    st = os.stat(p["path"])
    raw = json.dumps([p["path"], st.st_mtime, st.st_size, round(p["speed"], 4), round(p["use"], 4),
                      p["frames"], p["w"], p["h"], cfg["W"], cfg["H"], cfg["fps"], cfg["fit"],
                      cfg["smooth"], cfg["encoder"], cfg["crf"], cfg["preset"], "v1",
                      p.get("skip", 0), p.get("take", p["frames"])])
    return hashlib.sha1(raw.encode()).hexdigest()[:20]


def render_piece(p, cfg, ctl):
    out = os.path.join(CACHE, piece_key(p, cfg) + ".ts")
    if os.path.exists(out) and os.path.getsize(out) > 0:
        return out
    tmp = out + ".part"
    run_ff(piece_cmd(p, cfg, tmp), ctl)
    os.replace(tmp, out)
    return out


# ------------------------------------------------------------------ main job
def run_job(opts, do_render, log, report, ctl, lib):
    ctl.reset()
    sysr = sysreport()
    audio = opts.get("audio", "")
    if not lib or not os.path.isdir(opts.get("clips_dir", "")):
        raise RuntimeError("Clips folder not found")
    if not os.path.isfile(audio):
        raise RuntimeError("Voiceover file not found")
    if not lib["videos"] and not lib["images"]:
        raise RuntimeError("No usable clips found in that folder")

    report("Reading script", 1)
    import director
    stamps = director.parse_stamps(opts.get("script", "")) if opts.get("use_stamps") else []
    if stamps:
        mode, entries = "stamps", director.entries_from_stamps(stamps)
    else:
        mode, entries = parse_script(opts.get("script", ""), log)
    if not entries:
        raise RuntimeError("The script is empty")
    import project
    legacy_hash = project.script_hash(opts.get("script", ""))
    shash = project.project_hash(opts.get("script", ""), opts.get("clips_dir", ""), opts.get("audio", ""))
    pstate = project.load_for(shash, legacy_hash)
    ovr = project.active_overrides(pstate, shash, log)
    for e in entries:
        o = ovr.get(str(e["idx"]))
        if o:
            if o.get("refs"):
                e["refs"] = [(k, int(n)) for k, n in o["refs"]]
            e["count"] = o.get("count")
    log.info(f"Script mode: {mode} ({len(entries)} lines)")
    adur = audio_duration(audio)
    log.info(f"Voiceover length: {adur:.1f} s")

    if stamps:
        raw, cov, tok_times = director.stamp_times(entries, stamps, adur, log)
    else:
        model = opts.get("whisper_model") or sysr.get("whisper_model", "small")
        tr = transcribe(audio, opts.get("lang") or None, model, sysr.get("whisper_device", "cpu"),
                        sysr.get("whisper_compute_type", "int8"), adur, log,
                        lambda p: report("Listening to voiceover", 2 + p * 38), ctl)
        ctl.check()
        report("Aligning script to audio", 41)
        raw, cov = align_lines(entries, tr["words"], adur, log)
        tok_times = list(getattr(align_lines, "last_tt", []))
    cfg = make_cfg(opts, lib, sysr)
    fps = cfg["fps"]
    lead = max(0, int(opts.get("lead_ms", 100) or 0)) / 1000.0
    starts = [0.0]
    for i in range(1, len(raw)):
        s = max(raw[i] - lead, starts[-1] + 0.2)
        starts.append(min(s, adur - 0.05))
    fb = [int(round(s * fps)) for s in starts] + [int(round(adur * fps))]
    picks = {}
    need = []
    for i, e in enumerate(entries):
        if not e["refs"]:
            L = (fb[i + 1] - fb[i]) / fps
            if L > 0:
                need.append({"idx": e["idx"], "text": e["text"], "n": split_count(L, 1), "dur": round(L, 1)})
    if need:
        import planner
        report("AI is choosing clips", 41)
        picks = planner.match(need, lib, opts, log, report, ctl)

    problems = []
    vids = lib["videos"] or lib["images"]
    first_asset = vids[min(vids)]
    auto_nums = sorted(lib["videos"]) or sorted(lib["images"])
    auto_ptr = 0
    prev = None
    lines, pieces = [], []
    for i, e in enumerate(entries):
        frames = fb[i + 1] - fb[i]
        if frames <= 0:
            msg = f"Line {e['idx']}: no time available in the audio - skipped"
            log.warn(msg); problems.append(msg)
            continue
        L = frames / fps
        assets = []
        for kind, num in e["refs"]:
            a = (lib["images"].get(num) or lib["videos"].get(num)) if kind == "image" \
                else (lib["videos"].get(num) or lib["images"].get(num))
            if a is None:
                fbk = prev or first_asset
                msg = f"Line {e['idx']}: clip {num:03d} not found -> repeated clip {fbk['num']:03d}"
                log.warn(msg); problems.append(msg)
                a = fbk
            assets.append(a)
        n = split_count(L, len(assets) or 1)
        if e.get("count"):
            n = max(1, min(8, int(e["count"])))
        if not assets:
            for num in picks.get(e["idx"], []):
                a = lib["videos"].get(num) or lib["images"].get(num)
                if a:
                    assets.append(a)
            while len(assets) < n:
                num = auto_nums[auto_ptr % len(auto_nums)]
                auto_ptr += 1
                assets.append(lib["videos"].get(num) or lib["images"].get(num))
        prev = assets[-1]
        line_pieces = []
        for j in range(n):
            fr = frames * (j + 1) // n - frames * j // n
            if fr <= 0:
                continue
            p = make_piece(assets[j % len(assets)], fr, fps)
            p["line"] = e["idx"]
            line_pieces.append(p)
        pieces += line_pieces
        lines.append({"i": e["idx"], "start": fb[i] / fps, "end": fb[i + 1] / fps, "text": e["text"],
                      "pieces": [{"num": p["num"], "kind": p["kind"], "speed": round(p["speed"], 2)} for p in line_pieces]})
        if L > 10.5:
            log.info(f"Line {e['idx']} is {L:.1f}s long -> {len(line_pieces)} clips")
    result = {"lines": lines, "problems": problems, "output": None, "srt": None, "duration": adur,
              "source_videos": len(lib["videos"]), "source_images": len(lib["images"]),
              "source_assets": len(lib["videos"]) + len(lib["images"]),
              "script_lines": len(lines), "clip_pieces": len(pieces),
              "cfg": {"W": cfg["W"], "H": cfg["H"], "fps": fps, "encoder": cfg["encoder"]}, "coverage": round(cov, 2)}
    project.save_timeline(shash, lines)
    import transitions
    saved_transitions = project.active_transitions(pstate, shash)
    log.info(f"Project state: {len(saved_transitions)} saved transition setting(s) for this exact project")
    tplan = transitions.plan(pieces, fps, saved_transitions, log)
    result["transitions"] = [{"after_line": t["line"], "type": t["name"], "dur": round(2 * t["h"] / fps, 2)}
                             for t in tplan]
    result["transition_count"] = len(tplan)
    if saved_transitions and not tplan:
        msg = "Saved transitions exist, but none matched a renderable boundary. Reapply transitions after rebuilding the timeline."
        log.warn(msg)
        problems.append(msg)
    if tplan:
        log.info(f"Transition plan: {len(tplan)} effect(s) scheduled at script-line boundaries")
    log.info(f"Timeline ready: {len(lines)} script lines, {len(pieces)} timeline clip pieces, "
             f"{len(lib['videos'])} source videos + {len(lib['images'])} source images")
    if not do_render:
        report("Timeline ready", 100)
        return result

    stamp = time.strftime("%Y%m%d_%H%M%S")
    out_mp4 = os.path.join(OUT, f"MalixAris_{stamp}.mp4")
    out_srt = os.path.join(OUT, f"MalixAris_{stamp}.srt")
    with open(out_srt, "w", encoding="utf-8") as f:
        for k, ln in enumerate(lines, 1):
            f.write(f"{k}\n{ts_srt(ln['start'])} --> {ts_srt(ln['end'])}\n{ln['text']}\n\n")

    t0 = time.time()
    segs = transitions.build_segments(pieces, cfg, tplan, ctl, log, report, problems)
    log.info(f"All clips rendered in {time.time() - t0:.0f}s")

    report("Joining clips and adding audio", 95)
    import finish
    finish.mux(segs, audio, adur, out_mp4, cfg, entries, tok_times, ctl, log, report, problems)
    try:
        d = audio_duration(out_mp4)
        if abs(d - adur) > 0.25:
            msg = f"Final length {d:.2f}s differs from voiceover {adur:.2f}s"
            log.warn(msg); problems.append(msg)
    except Exception:
        pass
    result.update(output=out_mp4, srt=out_srt)
    log.info(f"DONE: {out_mp4}")
    report("Finished", 100)
    return result
