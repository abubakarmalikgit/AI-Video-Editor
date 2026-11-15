"""MalixAris Part 2D: Director (timestamps + brief-driven planning)."""
import os, re, json
import engine, ai, scanner, project, transitions, finish, agent

DATA = os.path.join(engine.ROOT, "data")
CFG = os.path.join(DATA, "director.json")
DEFAULTS = {"audio": "", "clips_dir": "", "script": "", "stamps": "", "brief": "",
            "quality": "high", "res": "original", "auto_render": False}
FINISH_OPS = {"set_captions", "set_music"}
FONT_LIST = ", ".join(finish.FONTS)


# ---------------------------------------------------------------- saved form
def load():
    d = dict(DEFAULTS)
    try:
        with open(CFG, encoding="utf-8") as f:
            d.update(json.load(f))
    except Exception:
        pass
    return d


def save(d):
    s = load()
    for k in DEFAULTS:
        if k in (d or {}):
            s[k] = d[k]
    with open(CFG, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)
    return True


# ---------------------------------------------------------------- timestamps
TC = r"(?:\d{1,2}:)?\d{1,2}:\d{2}(?:[.,]\d{1,3})?"
LINE_RE = re.compile(
    rf"^\s*[\[(]?\s*({TC})\s*[\])]?\s*(?:(?:-+>?|\u2013|\u2014|to)\s*[\[(]?\s*({TC})\s*[\])]?)?"
    rf"\s*[:|\-\u2013\u2014]?\s*(.*)$", re.I)
ARROW_RE = re.compile(rf"({TC})\s*-->\s*({TC})")


def _tc(s):
    sec = 0.0
    for p in s.replace(",", ".").split(":"):
        sec = sec * 60 + float(p)
    return sec


def parse_stamps(text):
    text = (text or "").replace("\r", "")
    out = []
    if "-->" in text:
        for block in re.split(r"\n\s*\n", text.strip()):
            rows = [r.strip() for r in block.split("\n") if r.strip()]
            for k, r in enumerate(rows):
                m = ARROW_RE.search(r)
                if m:
                    body = re.sub(r"<[^>]+>", "", " ".join(rows[k + 1:])).strip()
                    if body:
                        out.append({"s": _tc(m.group(1)), "e": _tc(m.group(2)), "text": body})
                    break
    else:
        for row in text.split("\n"):
            if not row.strip():
                continue
            m = LINE_RE.match(row)
            if m and m.group(3).strip():
                out.append({"s": _tc(m.group(1)), "e": _tc(m.group(2)) if m.group(2) else None,
                            "text": m.group(3).strip()})
            elif not m and out:
                out[-1]["text"] += " " + row.strip()
    out.sort(key=lambda x: x["s"])
    return out


def entries_from_stamps(stamps):
    entries = []
    for i, s in enumerate(stamps, 1):
        refs, text = [], s["text"]
        m = engine.SPLIT_RE.match(text)
        if m:
            r = engine.parse_left(m.group(1))
            if r:
                refs, text = r, m.group(2)
        entries.append({"idx": i, "refs": refs, "text": text})
    return entries


def stamp_times(entries, stamps, adur, log):
    raw, tok = [], []
    for i, (e, s) in enumerate(zip(entries, stamps)):
        a = min(max(0.0, s["s"]), adur)
        nxt = stamps[i + 1]["s"] if i + 1 < len(stamps) else adur
        b = s["e"] if (s["e"] and s["e"] > a) else nxt
        b = min(max(b, a + 0.3), adur)
        raw.append(a)
        n = len([w for w in e["text"].split() if engine.norm_tokens(w)])
        for j in range(n):
            tok.append(a + (b - a) * j / n)
    log.info(f"Using your timestamps: {len(entries)} lines (speech recognition skipped)")
    return raw, 1.0, tok


# ---------------------------------------------------------------- captions / music actions
def _b(v):
    if isinstance(v, str):
        return v.strip().lower() in ("true", "yes", "1", "on")
    return bool(v)


def apply_finish(actions):
    changes, skipped = [], []
    for a in actions:
        op = a.get("op")
        if op == "set_captions":
            d = {k: a[k] for k in ("on", "font", "size", "pos", "color", "outline", "words", "upper", "box") if k in a}
            if not d:
                skipped.append("set_captions: nothing to change")
                continue
            for k in ("on", "upper", "box"):
                if k in d:
                    d[k] = _b(d[k])
            d.setdefault("on", True)
            c = finish.save({"captions": d})["captions"]
            if c["on"]:
                changes.append(f"Captions ON: {c['font']}, size {c['size']:g}%, {c['pos']}, "
                               f"{c['words']} words each, text {c['color']}")
            else:
                changes.append("Captions OFF")
        elif op == "set_music":
            d = {k: a[k] for k in ("on", "volume", "fade_in", "fade_out", "duck", "track") if k in a}
            if not d:
                skipped.append("set_music: nothing to change")
                continue
            for k in ("on", "duck"):
                if k in d:
                    d[k] = _b(d[k])
            d.setdefault("on", True)
            m = finish.save({"music": d})["music"]
            if m["on"]:
                changes.append(f"Music ON at {m['volume']:.0f}%, fade in {m['fade_in']:g}s, fade out "
                               f"{m['fade_out']:g}s" + (", lowered under the voice" if m["duck"] else ""))
                if not finish.pick_music(m):
                    skipped.append("Music is ON but no music file or folder is chosen yet. Pick one in the Director.")
            else:
                changes.append("Music OFF")
    return changes, skipped


# ---------------------------------------------------------------- brief / chat
def chat(message, opts, lib, log):
    message = (message or "").strip()
    if not message:
        return {"ok": False, "reply": "Type a message first."}
    if not ai.get_key():
        return {"ok": False, "reply": "No Gemini key saved yet. Add it in AI Settings first."}
    if not ai.load_cfg().get("enabled", True):
        return {"ok": False, "reply": "Cloud AI is switched off in AI Settings."}
    if not lib or not (lib["videos"] or lib["images"]):
        return {"ok": False, "reply": "Choose your clips folder first."}
    agent.live_start()
    try:
        out = _run(message, opts, lib, log)
    except Exception as e:
        agent.live_end(str(e)[:200])
        raise
    agent.live_end()
    return out


def _run(message, opts, lib, log):
    legacy_hash = project.script_hash(opts.get("script", ""))
    shash = project.project_hash(opts.get("script", ""), opts.get("clips_dir", ""), opts.get("audio", ""))
    state = project.load_for(shash, legacy_hash)
    tl = project.load_timeline(shash, legacy_hash)
    have_tl = bool(tl and tl.get("hash") in (shash, legacy_hash) and tl.get("lines"))

    if have_tl:
        agent.live_step(f"Reading your timeline ({len(tl['lines'])} lines)")
        rows = []
        for l in tl["lines"]:
            nums = ",".join(str(p["num"]) for p in l["pieces"])
            t = state["transitions"].get(str(l["i"]))
            rows.append(f'{l["i"]} | {agent._mmss(l["start"])}-{agent._mmss(l["end"])} | clips {nums} | '
                        f'{l["text"][:70]} | after: {t["type"] if t else "cut"}')
        timeline = "\n".join(rows)
    else:
        agent.live_step("No timeline built yet")
        timeline = "NO TIMELINE BUILT YET. Only captions and music actions are possible."

    agent.live_step(f"Reading {len(lib['videos']) + len(lib['images'])} clip descriptions")
    fin = finish.load()
    cur = {"captions": fin["captions"],
           "music": {k: fin["music"][k] for k in ("on", "volume", "fade_in", "fade_out", "duck", "track")},
           "music_file_chosen": bool(finish.pick_music(fin["music"]))}
    prompt = (
        f"TIMELINE (line | time | clips | text | transition after this line):\n{timeline}\n\n"
        f"CLIP LIBRARY (id: description | tags):\n{agent._catalog(lib)}\n\n"
        f"SAVED EDITING STYLE: {state.get('style') or '(none)'}\n"
        f"CURRENT CAPTIONS AND MUSIC SETTINGS: {json.dumps(cur)}\n"
        f"ALLOWED TRANSITIONS: cut, {', '.join(transitions.ALLOWED)}\n\n"
        f"USER BRIEF OR MESSAGE:\n{message[:6000]}\n\n"
        "ANSWER FORMAT (JSON only): "
        '{"reply":"short friendly answer in the user\'s language","actions":[...]}\n'
        "ACTIONS you may use:\n"
        '- {"op":"set_clips","line":10,"clips":[12,45]}  replace the clips of ONE line (library ids only)\n'
        '- {"op":"set_count","line":7,"count":2}  clips per line: fewer = slower, more = faster\n'
        '- {"op":"reset_lines","lines":[5,6]}  let the AI choose these lines again\n'
        '- {"op":"set_transition","lines":[3,8],"type":"slideleft","dur":0.4}  transition at the cut AFTER each '
        'listed line. Use type "cut" to remove. Group lines by type.\n'
        '- {"op":"set_style","text":"..."}  remember the editing style\n'
        '- {"op":"set_captions","on":true,"font":"Poppins","size":5.5,"pos":"bottom","color":"#FFFFFF",'
        '"outline":"#000000","words":5,"upper":false,"box":false}  send only the fields to change. '
        "fonts: " + FONT_LIST + ". size = percent of video height (3 to 9, normal 5 to 6). words = words per "
        "caption (2 to 10). pos = bottom, middle or top. Colours are hex like #FFFFFF.\n"
        '- {"op":"set_music","on":true,"volume":12,"fade_in":2,"fade_out":3,"duck":true,"track":""}  '
        "background music. volume = percent 0 to 100 (normally 8 to 15). duck = lower music while the voice "
        "speaks. track = optional word that must be in the music file name.\n"
        "RULES:\n"
        "- Captions and music stay OFF unless the brief asks for them. If it says no captions or no music, "
        "send on:false.\n"
        "- Touch clips only if the brief asks. Touch only the lines named. Convert times like 0:30-0:45 to line "
        "numbers using the timeline.\n"
        "- Avoid repeating a clip in neighbouring lines; match the meaning of the line text.\n"
        "- Clips already fade in and out: prefer cut, slides and wipes; fade or dissolve rarely; durations 0.2 to 0.6.\n"
        "- For a style request, put transitions only where the topic changes (10 to 25 percent of cuts for "
        "energetic styles, fewer for calm ones) and also use set_style.\n"
        "- If the user only asks a question, return no actions.")

    wrote = {"v": False}

    def on_text(full):
        if not wrote["v"]:
            wrote["v"] = True
            agent.live_step("Writing the answer")
        agent.live_reply(full)

    client = ai.Client(log, None, min_gap=2)
    data = client.ask_stream([{"text": prompt}], system=agent.SYSTEM, temperature=0.3,
                             on_thought=agent.live_thought, on_text=on_text, on_status=agent.live_step)
    if not isinstance(data, dict):
        return {"ok": False, "reply": "The AI answer was not understandable. Please try again."}
    agent.live_step("Checking every line and clip number")
    actions = [a for a in (data.get("actions") or []) if isinstance(a, dict)]
    actions = agent.requested_transition_actions(message, tl["lines"] if have_tl else [], actions)
    out = {"ok": True, "reply": str(data.get("reply") or "Done.").strip(), "changes": [],
           "skipped": [], "changed": False, "propose_script": False}
    edits = [a for a in actions if a.get("op") in agent.EDIT_OPS]
    fins = [a for a in actions if a.get("op") in FINISH_OPS]
    if edits and not have_tl:
        out["skipped"].append("Build the timeline first, then ask again.")
        edits = []
    if fins:
        agent.live_step("Setting captions and music")
        fc, fs = apply_finish(fins)
        out["changes"] += fc
        out["skipped"] += fs
    if edits:
        agent.live_step("Applying changes")
        project.pin(state, tl["lines"])
        state["hash"] = shash
        before = project.snapshot(state)
        changes, skipped = agent.apply(edits, tl["lines"], lib, state)
        out["changes"] += changes
        out["skipped"] += skipped
        if changes:
            project.push_history(state, before, message[:60])
            project.save(state)
            out["changed"] = True
    log.info(f"Director: {len(out['changes'])} changes, {len(out['skipped'])} skipped")
    return out


# ---------------------------------------------------------------- Api methods
def director_load(self):
    return load()


def director_save(self, d):
    return save(d)


def director_stamps_info(self, text):
    try:
        return {"count": len(parse_stamps(text))}
    except Exception:
        return {"count": 0}


def director_pick_stamps(self):
    return self._dlg(types=("Subtitles or text (*.srt;*.txt)", "All files (*.*)"))


def director_chat(self, message, opts):
    try:
        lib = self._get_lib(opts.get("clips_dir", ""))
        return chat(message, opts, lib, self._log)
    except ai.AIError as e:
        self._log.error(f"Director failed: {e}")
        return {"ok": False, "reply": "Gemini problem: " + str(e)[:200]}
    except Exception as e:
        self._log.error(f"Director failed: {e}")
        return {"ok": False, "reply": "Something went wrong: " + str(e)[:200]}


def install(api_class):
    api_class.director_load = director_load
    api_class.director_save = director_save
    api_class.director_stamps_info = director_stamps_info
    api_class.director_pick_stamps = director_pick_stamps
    api_class.director_chat = director_chat
