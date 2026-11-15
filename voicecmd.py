"""MalixAris Voice + Polish commands - Part 3D"""
import os, sys, re, base64, threading, subprocess
import polish

BASE = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(BASE, "work", "voice")
STATE = {"ready": False, "msg": "Speech model not loaded yet"}
_M = {"m": None}
_LOCK = threading.Lock()
HISTORY = []
HINT = ("Video editing commands: clip, line, caption, captions, transition, dissolve, "
        "music, volume, normalize audio, color grade, intro, outro, undo, render.")
JUNK = {"thank you", "thanks for watching", "you", "bye", "thanks"}


def _log(m):
    polish._log("Voice: " + m)


# ---------- speech to text ----------
def _model():
    with _LOCK:
        if _M["m"] is None:
            STATE.update(ready=False, msg="Loading speech model (first time downloads about 145 MB)...")
            from faster_whisper import WhisperModel
            _M["m"] = WhisperModel("base", device="cpu", compute_type="int8",
                                   cpu_threads=min(8, os.cpu_count() or 4))
            STATE.update(ready=True, msg="Speech model ready")
            _log("speech model ready")
        return _M["m"]


def _warm():
    try:
        _model()
    except Exception as e:
        STATE.update(ready=False, msg="Speech model failed: %s" % e)
        _log("model load failed: %s" % e)


def transcribe(data):
    try:
        raw = base64.b64decode(str(data).split(",", 1)[-1])
        if len(raw) < 1500:
            return {"ok": False, "error": "Recording was empty - check your microphone"}
        os.makedirs(WORK, exist_ok=True)
        src, wav = os.path.join(WORK, "rec.webm"), os.path.join(WORK, "rec.wav")
        if os.path.isfile(wav):
            os.remove(wav)
        with open(src, "wb") as f:
            f.write(raw)
        r = subprocess.run([polish._tool("ffmpeg"), "-v", "error", "-y", "-i", src,
                            "-ac", "1", "-ar", "16000", wav],
                           capture_output=True, text=True, creationflags=polish.NOWIN, timeout=60)
        if r.returncode != 0 or not os.path.isfile(wav):
            return {"ok": False, "error": "Could not read the recording: " + (r.stderr or "")[-120:]}
        model = _model()
        segs, info = model.transcribe(wav, beam_size=1, vad_filter=True,
                                      initial_prompt=HINT, condition_on_previous_text=False)
        text = " ".join(s.text.strip() for s in segs).strip()
        if not text or text.lower().strip(" .!?") in JUNK:
            return {"ok": False, "error": "I did not catch that - try again closer to the mic"}
        _log("heard (%s): %s" % (info.language, text))
        return {"ok": True, "text": text, "lang": info.language}
    except Exception as e:
        _log("transcribe failed: %s" % e)
        return {"ok": False, "error": str(e)}


# ---------- command parser ----------
NEG = re.compile(r"\b(?:no|not|don'?t|do not|without|remove|delete|disable|turn off|switch off|skip|stop|cancel|never)\b")
RUN = re.compile(r"\b(?:polish (?:it|now|the video|video|everything)|run polish|start polish(?:ing)?|"
                 r"export (?:it|now|the video)|render (?:the )?polished)\b")
LOUD = re.compile(r"\b(?:normali[sz]\w*|loudness|loudnorm|lufs|(?:level|even)\s+out\s+(?:the\s+)?(?:audio|sound|volume))")
INTRO = re.compile(r"\b(?:intro|outro|title card|end card|end screen|opening title|closing title)\b")
OUTRO = re.compile(r"\b(?:outro|end card|end screen|closing)\b")
AUTO = re.compile(r"auto(?:matic(?:ally)?)?\s*polish|polish\w*\s+(?:automatically|after (?:every|each) render)|after (?:every|each) render")
CTX = re.compile(r"\b(?:grade|grading|graded|colou?rs?|look|tone|tint|filter|footage|video|picture|visuals?|image)\b")
NOGRADE = re.compile(r"\b(?:grad(?:e|ing)|colou?r (?:correction|filter)|filter)\b")
TITLE_RX = re.compile(r"\b(?:says?|saying|titled|title(?:\s+(?:is|of))?|called|reads?|text(?:\s+is)?|"
                      r"with\s+(?:the\s+)?(?:title|text))\s+(.+)$", re.I)
GR_STRONG = [("bw", r"black\s*(?:and|&|n)\s*white|b\s*&\s*w|\bbw\b|monochrome|grayscale|greyscale|\bnoir\b"),
             ("cinematic", r"teal\s*(?:and|&)?\s*orange|orange\s*(?:and|&)?\s*teal|hollywood")]
GR_AMBIG = [("cinematic", r"\bcinematic\b"),
            ("warm", r"\bwarm(?:er)?\b|\bgolden\b"),
            ("cool", r"\bcool(?:er)?\b|\bcold\b|\bbluish\b|\bicy\b"),
            ("vivid", r"\bvivid\b|\bcolou?rful\b|\bsaturated\b"),
            ("punchy", r"\bpunch\w*\b|\bhigh contrast\b|\bcontrasty\b"),
            ("soft", r"\bsoft film\b|\bfaded\b|\bsoft look\b|\bmatte\b|\bsoft (?:grade|colou?rs?|tone)\b")]
PRE = [("capcut", r"cap\s?cut|editing[- ]friendly"),
       ("small", r"small(?:er)? (?:file|size|export)|compress\w*|lighter file"),
       ("keep", r"same quality|original quality|max(?:imum)? quality|best quality"),
       ("youtube", r"youtube (?:preset|upload|export|version)|(?:export|render) for youtube|for youtube upload")]
SPLIT = re.compile(
    r"[;\n!?]+|\.(?=\s|$)|\s*,\s*|\s+(?:and then|then|also)\s+|"
    r"\s+and\s+(?=(?:also\s+)?(?:(?:an?\s+)?(?:intro|outro)|add|use|make|set|turn|switch|normali\w*|"
    r"apply|polish|export|remove|delete|no|don't|put|change|give|undo|show|enable|disable)\b)", re.I)


def _split(text):
    t = (text.replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
         .replace("\u2212", "-").replace("\u2013", "-"))
    quotes = []

    def hold(m):
        quotes.append(m.group(1).strip())
        return " \x00%d\x00 " % (len(quotes) - 1)

    t = re.sub(r'"([^"]{1,120})"', hold, t)
    return [p.strip() for p in SPLIT.split(t) if p and p.strip()], quotes


def _restore(s, quotes):
    s = re.sub(r"\x00(\d+)\x00", lambda m: '"%s"' % quotes[int(m.group(1))], s)
    return re.sub(r"\s+", " ", s).strip()


def _lufs(c):
    m = re.search(r"(-?\d{2})\s*(?:lufs|lu\b)", c) or re.search(r"(?<![\d.])-(14|16|23)\b", c)
    if m:
        v = -abs(int(m.group(1)))
        if 8 <= abs(v) <= 30:
            return v
    if re.search(r"youtube|social|tiktok|instagram|shorts|reels|facebook", c):
        return -14
    if re.search(r"podcast|spotify", c):
        return -16
    if re.search(r"broadcast|\btv\b|television", c):
        return -23
    return None


def _grade(c, neg):
    name = None
    for n, rx in GR_STRONG:
        if re.search(rx, c):
            name = n
            break
    if not name and CTX.search(c):
        for n, rx in GR_AMBIG:
            if re.search(rx, c):
                name = n
                break
    if neg and (name or NOGRADE.search(c)):
        return ("none", None)
    if not name:
        return None
    amt = None
    m = re.search(r"(\d{1,3})\s*(?:%|percent)", c)
    if m:
        amt = max(0, min(100, int(m.group(1))))
    elif re.search(r"strong|heavy|intense|bold|a lot", c):
        amt = 100
    elif re.search(r"subtle|slight|light|gentle|mild|little", c):
        amt = 35
    elif "medium" in c:
        amt = 70
    return (name, amt)


def _card_text(c0, quotes):
    s, secs = c0, None
    m = re.search(r"(?:for\s+)?(\d+(?:\.\d+)?)\s*(?:s|sec|secs|second|seconds)\b", s, re.I)
    if m:
        secs = float(m.group(1))
        s = s[:m.start()] + s[m.end():]
    ids = [int(x) for x in re.findall(r"\x00(\d+)\x00", s)]
    title = sub = ""
    if ids:
        title = quotes[ids[0]]
        sub = quotes[ids[1]] if len(ids) > 1 else ""
    else:
        m = TITLE_RX.search(s)
        if m:
            parts = re.split(r"\s+(?:and\s+)?(?:with\s+)?(?:an?\s+)?sub-?title(?:\s+(?:says?|of|is|reads?))?\s+",
                             m.group(1), maxsplit=1, flags=re.I)
            title = parts[0]
            sub = parts[1] if len(parts) > 1 else ""

    def clean(x):
        return x.strip(" ,.'\"")[:120]

    return clean(title), clean(sub), secs


def parse(text):
    low = text.lower().replace("\u2019", "'")
    if re.search(r"^\s*(?:please\s+)?undo\b.*\b(?:polish\w*|grad\w*|colou?r|audio|loudness|normali[sz]\w*|export|intro|outro)\b", low):
        return {"patch": {}, "notes": [], "run": False, "undo": True, "rest": ""}
    clauses, quotes = _split(text)
    patch, notes, rest, run = {}, [], [], False
    cur = polish.get()
    for c0 in clauses:
        c = c0.lower()
        neg = bool(NEG.search(c))
        hit = False
        if INTRO.search(c):
            kind = "outro" if OUTRO.search(c) else "intro"
            card = patch.setdefault(kind, {})
            if neg:
                card["on"] = False
                notes.append("%s removed" % kind.capitalize())
            else:
                title, sub, secs = _card_text(c0, quotes)
                card["on"] = True
                if title:
                    card["title"] = title
                if sub:
                    card["sub"] = sub
                if secs:
                    card["secs"] = secs
                have = title or sub or cur[kind]["title"] or cur[kind]["sub"]
                if have:
                    notes.append('%s ON: "%s"' % (kind.capitalize(), title or cur[kind]["title"] or sub))
                else:
                    notes.append('%s is ON but has no text - say: add %s "My Video"' % (kind.capitalize(), kind))
            hit = True
        else:
            if RUN.search(c):
                run = hit = True
            if LOUD.search(c):
                d = patch.setdefault("loud", {})
                d["on"] = not neg
                v = _lufs(c)
                if v and not neg:
                    d["lufs"] = v
                notes.append("Loudness normalize ON (%d LUFS)" % (v or cur["loud"]["lufs"]) if not neg
                             else "Loudness normalize OFF")
                hit = True
            g = _grade(c, neg)
            if g:
                name, amt = g
                d = patch.setdefault("grade", {})
                d["name"] = name
                if amt is not None:
                    d["amount"] = amt
                if name == "none":
                    notes.append("Color grade removed")
                else:
                    notes.append("Color grade: %s (%d%%)" % (polish.GRADES[name],
                                                             amt if amt is not None else cur["grade"]["amount"]))
                hit = True
            for n, rx in PRE:
                if re.search(rx, c):
                    patch["preset"] = "keep" if neg else n
                    notes.append("Export preset: " + polish.PRESETS[patch["preset"]])
                    hit = True
                    break
            if AUTO.search(c):
                patch["auto"] = not neg
                notes.append("Auto-polish after render " + ("ON" if not neg else "OFF"))
                hit = True
        if not hit:
            rest.append(_restore(c0, quotes))
    return {"patch": patch, "notes": notes, "run": run, "undo": False, "rest": ". ".join(rest)}


def route(text):
    text = str(text or "")
    try:
        r = parse(text)
    except Exception as e:
        _log("parser error: %s" % e)
        return {"ok": True, "notes": [], "rest": text}
    notes = list(r["notes"])
    if r["undo"]:
        if HISTORY:
            polish.save(HISTORY.pop())
            notes.append("Polish settings restored to the previous state")
        else:
            notes.append("Nothing to undo in Polish settings")
    elif r["patch"]:
        HISTORY.append(polish.get())
        del HISTORY[:-20]
        polish.save(r["patch"])
    if r["run"]:
        res = polish.run("")
        notes.append("Polishing started - see Polish & Export" if res.get("ok")
                     else "Polish: " + res.get("error", "failed"))
    handled = bool(notes) or bool(r["patch"])
    if handled:
        _log("command handled: " + " | ".join(notes))
    return {"ok": True, "notes": notes, "rest": r["rest"] if handled else text}


# ---------- hooks ----------
def install(Api):
    def voice_status(self):
        return dict(STATE)

    def voice_warm(self):
        threading.Thread(target=_warm, daemon=True).start()
        return True

    def voice_transcribe(self, data):
        return transcribe(data)

    def voice_route(self, text):
        return route(text)

    for fn in (voice_status, voice_warm, voice_transcribe, voice_route):
        setattr(Api, fn.__name__, fn)
