"""MalixAris Video Maker - AI agent: chat edits + editing style (Part 2B + 2C)."""
import json, re, time, threading
import ai, scanner, project, transitions, fastai

EDIT_OPS = {"set_clips", "set_count", "reset_lines", "set_transition", "set_style"}

SYSTEM = ("You are the editing agent inside a video tool. You change an existing timeline by returning "
          "structured actions. Never invent clip ids or line numbers. Answer with JSON only.")

# ---------------------------------------------------------------- live status (for the thinking card)
LIVE = {"id": 0, "active": False, "steps": [], "thoughts": "", "reply": "",
        "t0": 0.0, "dur": 0.0, "error": ""}
_lock = threading.Lock()


def live_start():
    with _lock:
        LIVE.update(id=LIVE["id"] + 1, active=True, steps=[], thoughts="", reply="",
                    t0=time.time(), dur=0.0, error="")


def live_step(t):
    with _lock:
        if not LIVE["steps"] or LIVE["steps"][-1] != t:
            LIVE["steps"].append(t)


def live_thought(t):
    with _lock:
        LIVE["thoughts"] = (LIVE["thoughts"] + t)[-3000:]


def live_reply(full):
    m = re.search(r'"reply"\s*:\s*"((?:[^"\\]|\\.)*)', full)
    if m:
        s = m.group(1)
        try:
            s = json.loads('"' + s + '"')
        except Exception:
            pass
        with _lock:
            LIVE["reply"] = s


def live_end(error=""):
    with _lock:
        LIVE["dur"] = time.time() - LIVE["t0"]
        LIVE["active"] = False
        LIVE["error"] = error


def live_get():
    with _lock:
        d = dict(LIVE)
        d["steps"] = list(LIVE["steps"])
        d["elapsed"] = (time.time() - LIVE["t0"]) if LIVE["active"] else LIVE["dur"]
        return d


# ---------------------------------------------------------------- helpers
def _ints(v):
    out = []
    for x in (v if isinstance(v, list) else [v]):
        try:
            out.append(int(x))
        except Exception:
            pass
    return out


def _catalog(lib):
    store = scanner.load_library()
    rows = []
    for kind, d in (("v", lib["videos"]), ("i", lib["images"])):
        for n in sorted(d):
            e = store.get(f"{kind}{n}", {})
            if e.get("desc"):
                rows.append(f"{n}: {e['desc'][:80]} | {', '.join(e.get('tags', [])[:4])}")
            else:
                rows.append(f"{n}:")
    return "\n".join(rows)


def _mmss(t):
    return f"{int(t // 60)}:{int(t % 60):02d}"


def _span(nums):
    nums = sorted(set(nums))
    return ", ".join(str(n) for n in nums[:12]) + (" ..." if len(nums) > 12 else "")


def requested_transition_actions(message, tl_lines, actions):
    """Guarantee a real transition action when the user explicitly requests effects."""
    text = (message or "").lower()
    asks = bool(
        re.search(r"\b(transitions?|transition effects?|effects between clips)\b", text)
        and re.search(r"\b(add|apply|put|use|include|insert|make|give|create|want|need|some|few)\b", text)
    )
    removes = bool(
        re.search(r"\b(no transitions?|remove|delete|disable|without|turn off|hard cuts only)\b", text)
        or re.search(r"\b(don't|do not|never|not)\b.{0,24}\btransitions?\b", text)
    )
    boundaries = [int(l["i"]) for l in (tl_lines or [])[:-1] if l.get("pieces")]
    valid_ai_transition = any(
        a.get("op") == "set_transition"
        and transitions.clean_type(a.get("type")) not in (None, "cut")
        and any(x in boundaries for x in _ints(a.get("lines")))
        for a in actions
    )
    if not asks or removes or valid_ai_transition or not boundaries:
        return actions

    # Remove malformed/last-line transition actions before adding deterministic ones.
    actions = [a for a in actions if a.get("op") != "set_transition"]
    if "dip to black" in text or "fade to black" in text or "black" in text:
        kind = "fadeblack"
    elif "white" in text:
        kind = "fadewhite"
    elif "wipe" in text:
        kind = "wipeleft"
    elif "slide" in text:
        kind = "slideleft"
    elif "zoom" in text:
        kind = "zoomin"
    elif "fade" in text or "dissolve" in text:
        kind = "dissolve"
    else:
        kind = "dissolve"

    # A few well-spaced boundaries; never attach an effect after the final line.
    count = max(1, min(5, round(len(boundaries) * 0.25)))
    if count == 1:
        chosen = [boundaries[len(boundaries) // 2]]
    else:
        indices = sorted(set(round((i + 1) * (len(boundaries) - 1) / (count + 1)) for i in range(count)))
        chosen = [boundaries[i] for i in indices]
    if not chosen:
        chosen = [boundaries[0]]
    actions.append({"op": "set_transition", "lines": chosen, "type": kind, "dur": 0.45})
    return actions


def apply(actions, tl_lines, lib, state):
    valid = {l["i"] for l in tl_lines}
    ov, tr = state["overrides"], state["transitions"]
    changes, skipped = [], []
    for a in actions:
        op = a.get("op")
        if op == "set_clips":
            ln = _ints(a.get("line"))
            ln = ln[0] if ln else None
            if ln not in valid:
                skipped.append(f"set_clips: line {a.get('line')} does not exist")
                continue
            nums = []
            for n in _ints(a.get("clips")):
                if (n in lib["videos"] or n in lib["images"]) and n not in nums:
                    nums.append(n)
            nums = nums[:8]
            if not nums:
                skipped.append(f"Line {ln}: none of the suggested clips exist in your folder")
                continue
            ov[str(ln)] = {"refs": [["video" if n in lib["videos"] else "image", n] for n in nums]}
            changes.append(f"Line {ln}: clips " + ", ".join(f"{n:03d}" for n in nums))
        elif op == "set_count":
            ln = _ints(a.get("line"))
            ln = ln[0] if ln else None
            c = _ints(a.get("count"))
            if ln not in valid or not c:
                skipped.append("set_count: invalid line or number")
                continue
            c = max(1, min(8, c[0]))
            ov.setdefault(str(ln), {"refs": []})["count"] = c
            changes.append(f"Line {ln}: {c} clip(s) (fewer clips = slower, more clips = faster)")
        elif op == "reset_lines":
            done = [i for i in _ints(a.get("lines")) if i in valid]
            for i in done:
                ov.pop(str(i), None)
            if done:
                changes.append(f"Line(s) {_span(done)}: clips chosen again automatically")
            else:
                skipped.append("reset_lines: no valid lines")
        elif op == "set_transition":
            boundary_valid = {l["i"] for l in tl_lines[:-1] if l.get("pieces")}
            done = [i for i in _ints(a.get("lines")) if i in boundary_valid]
            t = transitions.clean_type(a.get("type"))
            if t is None:
                skipped.append(f"Unknown transition '{a.get('type')}'")
                continue
            try:
                dur = max(0.15, min(0.8, float(a.get("dur", 0.4))))
            except Exception:
                dur = 0.4
            if not done:
                skipped.append("set_transition: no valid lines")
                continue
            for i in done:
                if t == "cut":
                    tr.pop(str(i), None)
                else:
                    tr[str(i)] = {"type": t, "dur": dur}
            changes.append(f"Cut after line(s) {_span(done)}: {'hard cut' if t == 'cut' else t + ' ' + str(dur) + 's'}")
        elif op == "set_style":
            state["style"] = str(a.get("text", ""))[:400]
            changes.append("Editing style saved")
    return changes, skipped


# ---------------------------------------------------------------- chat
def chat(message, opts, lib, log):
    message = (message or "").strip()
    if not message:
        return {"ok": False, "reply": "Type a message first."}
    if not ai.get_key():
        return {"ok": False, "reply": "No Gemini key saved yet. Add it in AI Settings first."}
    if not ai.load_cfg().get("enabled", True):
        return {"ok": False, "reply": "Cloud AI is switched off in AI Settings."}
    if not lib or not (lib["videos"] or lib["images"]):
        return {"ok": False, "reply": "Choose your clips folder on the Project page first."}
    live_start()
    try:
        out = _run(message, opts, lib, log)
    except Exception as e:
        live_end(str(e)[:200])
        raise
    live_end()
    return out


def _run(message, opts, lib, log):
    legacy_hash = project.script_hash(opts.get("script", ""))
    shash = project.project_hash(opts.get("script", ""), opts.get("clips_dir", ""), opts.get("audio", ""))
    state = project.load_for(shash, legacy_hash)
    tl = project.load_timeline(shash, legacy_hash)
    have_tl = bool(tl and tl.get("hash") in (shash, legacy_hash) and tl.get("lines"))

    if have_tl:
        live_step(f"Reading your timeline ({len(tl['lines'])} lines)")
        rows = []
        for l in tl["lines"]:
            nums = ",".join(str(p["num"]) for p in l["pieces"])
            t = state["transitions"].get(str(l["i"]))
            rows.append(f'{l["i"]} | {_mmss(l["start"])}-{_mmss(l["end"])} | clips {nums} | '
                        f'{l["text"][:70]} | after: {t["type"] if t else "cut"}')
        timeline = "\n".join(rows)
    else:
        live_step("No timeline built yet")
        timeline = "NO TIMELINE BUILT YET. Only reply in words, or use propose_script."

    live_step(f"Reading {len(lib['videos']) + len(lib['images'])} clip descriptions")
    prompt = (
        f"TIMELINE (line | time | clips | text | transition after this line):\n{timeline}\n\n"
        f"CLIP LIBRARY (id: description | tags):\n{_catalog(lib)}\n\n"
        f"SAVED EDITING STYLE: {state.get('style') or '(none)'}\n"
        f"ALLOWED TRANSITIONS: cut, {', '.join(transitions.ALLOWED)}\n\n"
        f"USER MESSAGE:\n{message[:6000]}\n\n"
        "ANSWER FORMAT (JSON only): "
        '{"reply":"short friendly answer in the user\'s language","actions":[...]}\n'
        "ACTIONS you may use:\n"
        '- {"op":"set_clips","line":10,"clips":[12,45]}  replace the clips of ONE line (use library ids only; '
        "one action per line; clips in the order they should play)\n"
        '- {"op":"set_count","line":7,"count":2}  how many clips fill the line: fewer = slower motion, more = faster\n'
        '- {"op":"reset_lines","lines":[5,6]}  let the AI choose these lines again from scratch\n'
        '- {"op":"set_transition","lines":[3,8],"type":"slideleft","dur":0.4}  transition at the cut AFTER each '
        'listed line (between that line and the next). Use type "cut" to remove. Group lines by type.\n'
        '- {"op":"set_style","text":"..."}  remember the editing style the user describes\n'
        '- {"op":"propose_script"}  ONLY when the message is a pasted script, not an instruction\n'
        "RULES:\n"
        "- Touch only the lines the user names. Convert times like 0:30-0:45 to line numbers using the timeline.\n"
        "- Avoid repeating a clip in neighbouring lines; match the meaning of the line text.\n"
        "- Clips already fade in and out by themselves: prefer cut, slides and wipes; use fade or dissolve rarely; "
        "durations 0.2 to 0.6.\n"
        "- When asked to add transitions, always return at least one valid set_transition action.\n"
        "- For a style request, put transitions only where the topic changes (about 10 to 25 percent of cuts for "
        "energetic styles, fewer for calm ones) and also use set_style.\n"
        "- If the user only asks a question, return no actions.")

    wrote = {"v": False}

    def on_text(full):
        if not wrote["v"]:
            wrote["v"] = True
            live_step("Writing the answer")
        live_reply(full)

    client = ai.Client(log, None, min_gap=2)
    data = client.ask_stream([{"text": prompt}], system=SYSTEM, temperature=0.3,
                             on_thought=live_thought, on_text=on_text, on_status=live_step)
    if not isinstance(data, dict):
        return {"ok": False, "reply": "The AI answer was not understandable. Please try again."}
    live_step("Checking every line and clip number")
    actions = [a for a in (data.get("actions") or []) if isinstance(a, dict)]
    actions = requested_transition_actions(message, tl["lines"] if have_tl else [], actions)
    out = {"ok": True, "reply": str(data.get("reply") or "Done.").strip(),
           "changes": [], "skipped": [], "changed": False,
           "propose_script": any(a.get("op") == "propose_script" for a in actions)}
    edits = [a for a in actions if a.get("op") in EDIT_OPS]
    if edits and not have_tl:
        out["skipped"].append("Build the timeline first (Project page, Build timeline), then ask again.")
        edits = []
    if edits:
        live_step("Applying changes")
        project.pin(state, tl["lines"])
        state["hash"] = shash
        before = project.snapshot(state)
        changes, skipped = apply(edits, tl["lines"], lib, state)
        out["changes"], out["skipped"] = changes, out["skipped"] + skipped
        if changes:
            project.push_history(state, before, message[:60])
            project.save(state)
            out["changed"] = True
    log.info(f"Agent: {len(out['changes'])} changes, {len(out['skipped'])} skipped")
    return out
