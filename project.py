"""Per-project agent edits, transitions, timeline snapshots and undo history."""
import os, json, time, copy, hashlib
import ai

DATA = ai.DATA
PATH = os.path.join(DATA, "project.json")  # legacy compatibility
TL_PATH = os.path.join(DATA, "last_timeline.json")
PROJECTS_DIR = os.path.join(DATA, "projects")
TIMELINES_DIR = os.path.join(DATA, "timelines")
os.makedirs(PROJECTS_DIR, exist_ok=True)
os.makedirs(TIMELINES_DIR, exist_ok=True)


def _read(p, default):
    try:
        with open(p, encoding="utf-8") as f:
            value = json.load(f)
            return value if isinstance(value, dict) else default
    except Exception:
        return default


def _write(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def script_hash(text):
    """Legacy script-only fingerprint used by Studio 3.0 projects."""
    return hashlib.sha1(" ".join((text or "").split()).encode("utf-8")).hexdigest()[:12]


def project_hash(script, clips_dir="", audio=""):
    """Stable identity for a production: script plus its source folder and voiceover."""
    def norm_path(value):
        value = str(value or "").strip()
        return os.path.normcase(os.path.abspath(value)) if value else ""
    payload = "\n".join((" ".join((script or "").split()), norm_path(clips_dir), norm_path(audio)))
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]


def _state_path(shash):
    return os.path.join(PROJECTS_DIR, str(shash) + ".json")


def _timeline_path(shash):
    return os.path.join(TIMELINES_DIR, str(shash) + ".json")


def _default(shash=""):
    return {"overrides": {}, "transitions": {}, "style": "", "hash": shash, "history": []}


def load():
    s = _default()
    s.update(_read(PATH, {}))
    return s


def load_for(shash, legacy_hash=None):
    """Load this production and preserve/migrate any Studio 3.0 single-project state."""
    saved = _read(_state_path(shash), None)
    if saved is not None:
        s = _default(shash); s.update(saved); s["hash"] = shash
        return s

    # A legacy state may have been left behind by a different project. Archive it
    # before any save can overwrite the old single-project file.
    legacy = _read(PATH, {})
    old_hash = str(legacy.get("hash") or "")
    if old_hash and old_hash not in (shash, legacy_hash):
        archived = _state_path(old_hash)
        if not os.path.exists(archived):
            _write(archived, legacy)

    # First look for an archived script-only state from an earlier update.
    if legacy_hash and legacy_hash != shash:
        archived = _read(_state_path(legacy_hash), None)
        if archived is not None:
            s = _default(shash); s.update(archived); s["hash"] = shash
            _write(_state_path(shash), s)
            return s

    if old_hash in (shash, legacy_hash):
        s = _default(shash); s.update(legacy); s["hash"] = shash
        _write(_state_path(shash), s)
        return s
    return _default(shash)


def save(state):
    shash = str(state.get("hash") or "")
    if shash:
        _write(_state_path(shash), state)
    _write(PATH, state)  # keeps older UI/API integrations working


def active_overrides(state, shash, log=None):
    if state.get("hash") != shash:
        return {}
    return state.get("overrides", {})


def active_transitions(state, shash):
    return state.get("transitions", {}) if state.get("hash") == shash else {}


def save_timeline(shash, lines):
    payload = {"hash": shash, "lines": lines, "saved_at": time.time()}
    _write(_timeline_path(shash), payload)
    _write(TL_PATH, payload)


def load_timeline(shash=None, legacy_hash=None):
    if shash:
        d = _read(_timeline_path(shash), None)
        if d is not None:
            return d
        if legacy_hash and legacy_hash != shash:
            old = _read(_timeline_path(legacy_hash), None)
            if old is not None:
                migrated = dict(old); migrated["hash"] = shash
                _write(_timeline_path(shash), migrated)
                return migrated
        legacy = _read(TL_PATH, None)
        if legacy and legacy.get("hash") in (shash, legacy_hash):
            migrated = dict(legacy); migrated["hash"] = shash
            _write(_timeline_path(shash), migrated)
            return migrated
        if legacy and legacy.get("hash"):
            archived = _timeline_path(legacy["hash"])
            if not os.path.exists(archived):
                _write(archived, legacy)
        return None
    return _read(TL_PATH, None)


def fresh_for(state, shash):
    """Switch the in-memory state to another script without deleting its old edits."""
    if state.get("hash") != shash:
        old = dict(state)
        if old.get("hash") and (old.get("overrides") or old.get("transitions") or old.get("history")):
            _write(_state_path(old["hash"]), old)
        state.clear()
        state.update(load_for(shash))
    return state


def pin(state, lines):
    ov = state.setdefault("overrides", {})
    for l in lines:
        k = str(l["i"])
        if k in ov:
            continue
        refs, seen = [], set()
        for p in l["pieces"]:
            t = (p["kind"], p["num"])
            if t not in seen:
                seen.add(t); refs.append([p["kind"], p["num"]])
        if refs:
            ov[k] = {"refs": refs}


def snapshot(state):
    return copy.deepcopy({k: state.get(k) for k in ("overrides", "transitions", "style", "hash")})


def push_history(state, snap, label):
    state.setdefault("history", []).append({"label": label, "time": time.strftime("%H:%M"), "snap": snap})
    del state["history"][:-30]


def undo(shash=None, legacy_hash=None):
    s = load_for(shash, legacy_hash) if shash else load()
    if not s.get("history"):
        return None
    h = s["history"].pop()
    s.update(h["snap"])
    save(s)
    return h["label"]


def reset_all(shash=None, legacy_hash=None):
    s = load_for(shash, legacy_hash) if shash else load()
    push_history(s, snapshot(s), "Reset all edits")
    s.update(overrides={}, transitions={}, style="")
    save(s)
    return s


# ------------------------------------------------------------------ named project library
NAMED_PATH = os.path.join(DATA, "named_projects.json")


def _named_rows():
    raw = _read(NAMED_PATH, {})
    rows = raw.get("projects", []) if isinstance(raw, dict) else []
    return rows if isinstance(rows, list) else []


def _save_named_rows(rows):
    _write(NAMED_PATH, {"version": 1, "projects": rows, "updated_at": time.time()})


def _project_summary(row):
    opts = row.get("opts", {}) or {}
    shash = str(row.get("hash") or "")
    timeline = load_timeline(shash) if shash else None
    lines = timeline.get("lines", []) if timeline else []
    return {
        "id": row.get("id", ""), "name": row.get("name", "Untitled Project"),
        "created_at": row.get("created_at", 0), "updated_at": row.get("updated_at", 0),
        "clips_dir": opts.get("clips_dir", ""), "audio": opts.get("audio", ""),
        "line_count": len(lines), "timeline_saved": bool(timeline),
        "hash": shash, "legacy": bool(row.get("legacy")),
        "output": row.get("output", "")
    }


def list_named_projects():
    """List named projects plus recoverable hash-based Studio 3.0/3.2 projects."""
    rows = _named_rows()
    known = {str(r.get("hash") or "") for r in rows}
    found = {}
    # Existing per-project agent state files are the most reliable source of old project IDs.
    try:
        for fn in os.listdir(PROJECTS_DIR):
            if fn.lower().endswith('.json'):
                h = fn[:-5]
                if h and h not in known:
                    found[h] = max(found.get(h, 0), os.path.getmtime(os.path.join(PROJECTS_DIR, fn)))
    except OSError:
        pass
    # Timeline-only projects are also recoverable and should not be hidden.
    try:
        for fn in os.listdir(TIMELINES_DIR):
            if fn.lower().endswith('.json'):
                h = fn[:-5]
                if h and h not in known:
                    found[h] = max(found.get(h, 0), os.path.getmtime(os.path.join(TIMELINES_DIR, fn)))
    except OSError:
        pass
    # Include the legacy single-project state if it has not yet been archived.
    legacy = _read(PATH, {})
    legacy_hash = str(legacy.get("hash") or "")
    if legacy_hash and legacy_hash not in known:
        try: found[legacy_hash] = max(found.get(legacy_hash, 0), os.path.getmtime(PATH))
        except OSError: found[legacy_hash] = time.time()
    for h, stamp in found.items():
        t = load_timeline(h)
        state = _read(_state_path(h), {})
        rows.append({
            "id": "legacy-" + h, "name": "Recovered Project " + h[:6],
            "created_at": stamp, "updated_at": stamp, "hash": h,
            "opts": {}, "legacy": True, "output": "",
            "legacy_state": state, "legacy_timeline": t
        })
    rows.sort(key=lambda r: float(r.get("updated_at", 0) or 0), reverse=True)
    return [_project_summary(r) for r in rows]


def create_named_project(name, opts=None):
    import uuid
    now = time.time()
    opts = dict(opts or {})
    shash = project_hash(opts.get("script", ""), opts.get("clips_dir", ""), opts.get("audio", ""))
    row = {"id": uuid.uuid4().hex, "name": str(name or "Untitled Project").strip()[:100] or "Untitled Project",
           "created_at": now, "updated_at": now, "hash": shash, "opts": opts, "legacy": False, "output": ""}
    rows = _named_rows(); rows.append(row); _save_named_rows(rows)
    # Ensure the project has a dedicated state file immediately.
    state = load_for(shash, script_hash(opts.get("script", "")))
    state["hash"] = shash; save(state)
    return _project_summary(row)


def save_named_project(opts, project_id="", name=""):
    import uuid
    opts = dict(opts or {})
    now = time.time()
    shash = project_hash(opts.get("script", ""), opts.get("clips_dir", ""), opts.get("audio", ""))
    rows = _named_rows()
    row = next((r for r in rows if str(r.get("id")) == str(project_id)), None) if project_id else None
    if row is None:
        row = {"id": uuid.uuid4().hex, "name": str(name or "Untitled Project").strip()[:100] or "Untitled Project",
               "created_at": now, "legacy": False, "output": ""}
        rows.append(row)
    old_hash = str(row.get("hash") or "")
    row.update({"name": str(name or row.get("name") or "Untitled Project").strip()[:100] or "Untitled Project",
                "updated_at": now, "hash": shash, "opts": opts, "legacy": False})
    # Keep old hash-based edit/timeline files intact if the script/folder/audio changed.
    if old_hash and old_hash != shash:
        old_state = _read(_state_path(old_hash), None)
        if old_state is not None:
            _write(_state_path(old_hash), old_state)
    state = load_for(shash, script_hash(opts.get("script", "")))
    state["hash"] = shash; save(state)
    _save_named_rows(rows)
    return _project_summary(row)


def load_named_project(project_id):
    rows = _named_rows()
    row = next((r for r in rows if str(r.get("id")) == str(project_id)), None)
    if row is None:
        # Recovered legacy projects carry no complete input settings. Their timeline and agent state remain accessible.
        h = str(project_id or "").removeprefix("legacy-")
        if not h:
            return None
        return {"id": "legacy-" + h, "name": "Recovered Project " + h[:6], "hash": h,
                "opts": {}, "timeline": load_timeline(h), "state": _read(_state_path(h), {}), "legacy": True}
    h = str(row.get("hash") or "")
    return {"id": row.get("id"), "name": row.get("name"), "hash": h,
            "opts": row.get("opts", {}) or {}, "timeline": load_timeline(h) if h else None,
            "state": _read(_state_path(h), {}) if h else {}, "legacy": bool(row.get("legacy")),
            "output": row.get("output", "")}


def rename_named_project(project_id, name):
    rows = _named_rows()
    row = next((r for r in rows if str(r.get("id")) == str(project_id)), None)
    if row is None:
        return False
    row["name"] = str(name or "Untitled Project").strip()[:100] or "Untitled Project"
    row["updated_at"] = time.time(); _save_named_rows(rows)
    return True


def duplicate_named_project(project_id):
    import uuid
    rows = _named_rows()
    row = next((r for r in rows if str(r.get("id")) == str(project_id)), None)
    if row is None:
        return None
    clone = dict(row); clone["id"] = uuid.uuid4().hex
    clone["name"] = (str(row.get("name") or "Project") + " Copy")[:100]
    clone["created_at"] = clone["updated_at"] = time.time()
    rows.append(clone); _save_named_rows(rows)
    return _project_summary(clone)


def delete_named_project(project_id):
    rows = _named_rows()
    kept = [r for r in rows if str(r.get("id")) != str(project_id)]
    if len(kept) == len(rows):
        return False
    _save_named_rows(kept)
    # Deliberately retain hash-based timelines and agent state as recoverable data.
    return True
