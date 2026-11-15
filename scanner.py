"""MalixAris Video Maker - clip scanner: thumbnails + AI descriptions (Part 2A)."""
import os, json, base64, subprocess, threading
from concurrent.futures import ThreadPoolExecutor
import ai
from engine import NO_WINDOW

THUMBS = os.path.join(ai.DATA, "thumbs")
LIB_PATH = os.path.join(ai.DATA, "library.json")
os.makedirs(THUMBS, exist_ok=True)
_lock = threading.Lock()

SYSTEM = ("You catalogue short animated video clips for a professional video editor. "
          "Be concrete and visual. Answer with JSON only.")


def load_library():
    try:
        with open(LIB_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_library(store):
    with _lock:
        tmp = LIB_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(store, f, ensure_ascii=False, indent=1)
        os.replace(tmp, LIB_PATH)


def akey(a):
    return ("v" if a["kind"] == "video" else "i") + str(a["num"])


def sig(a):
    st = os.stat(a["path"])
    return f"{st.st_size}-{int(st.st_mtime)}"


def grab(path, t, width=448):
    cmd = ["ffmpeg", "-v", "error"]
    if t > 0:
        cmd += ["-ss", f"{t:.2f}"]
    cmd += ["-i", path, "-frames:v", "1", "-vf", f"scale={width}:-2", "-q:v", "4",
            "-f", "image2pipe", "-vcodec", "mjpeg", "-"]
    try:
        r = subprocess.run(cmd, capture_output=True, creationflags=NO_WINDOW, timeout=60)
        return r.stdout if r.returncode == 0 else b""
    except Exception:
        return b""


def get_frames(a):
    if a["kind"] == "image":
        f = grab(a["path"], 0)
        return [f] if f else []
    d = a.get("dur") or 5.0
    out = []
    for frac in (0.25, 0.5, 0.75):
        f = grab(a["path"], d * frac)
        if f:
            out.append(f)
    return out


def describe_batch(client, batch, frames):
    parts = [{"text": "Describe each clip below. Each clip is shown as 3 frames in time order."}]
    for a in batch:
        k = akey(a)
        parts.append({"text": f'Clip id "{k}":'})
        for fr in frames[k]:
            parts.append({"inline_data": {"mime_type": "image/jpeg",
                                          "data": base64.b64encode(fr).decode()}})
    parts.append({"text": 'Return JSON exactly like {"clips":[{"id":"v12","desc":"max 25 words: subject, '
                          'colors, motion or camera style","tags":["5 to 8 lowercase keywords"],'
                          '"mood":"one word"}]}. Use the ids given above. Describe only what you see.'})
    data = client.ask(parts, system=SYSTEM, temperature=0.2)
    items = data.get("clips") if isinstance(data, dict) else data
    out = {}
    for it in items or []:
        if isinstance(it, dict) and it.get("id"):
            out[str(it["id"]).strip()] = it
    return out


def scan(lib, log, report, ctl, use_ai):
    ctl.reset()
    store = load_library()
    assets = list(lib["videos"].values()) + list(lib["images"].values())
    todo = []
    for a in assets:
        e = store.get(akey(a))
        ok = (e and e.get("sig") == sig(a) and os.path.exists(e.get("thumb", ""))
              and (e.get("desc") or not use_ai))
        if not ok:
            todo.append(a)
    log.info(f"Scan: {len(assets)} clips, {len(todo)} need work (the rest are already done)")

    frames, done = {}, 0
    if todo:
        report("Reading frames from clips", 2)
        with ThreadPoolExecutor(3) as ex:
            for a, fr in ex.map(lambda x: (x, get_frames(x)), todo):
                ctl.check()
                k = akey(a)
                e = store.get(k)
                if not e or e.get("sig") != sig(a):
                    e = {"num": a["num"], "kind": a["kind"], "desc": "", "tags": [], "mood": ""}
                e["sig"] = sig(a)
                if fr:
                    tp = os.path.join(THUMBS, k + ".jpg")
                    with open(tp, "wb") as f:
                        f.write(fr[len(fr) // 2])
                    e["thumb"] = tp
                    frames[k] = fr
                else:
                    log.warn(f"Could not read any frame from clip {a['num']:03d}")
                store[k] = e
                done += 1
                report("Reading frames from clips", 2 + 18 * done / len(todo))
        save_library(store)

    failed = 0
    if use_ai:
        need = [a for a in todo if akey(a) in frames and not store[akey(a)].get("desc")]
        batches = [need[i:i + 4] for i in range(0, len(need), 4)]
        if batches:
            log.info(f"Gemini will describe {len(need)} clips in {len(batches)} requests "
                     f"(about {len(batches) * 8 // 60 + 1} min). You can stop and resume any time.")
        client = ai.Client(log, ctl)
        for bi, b in enumerate(batches):
            ctl.check()
            report(f"AI is watching clips ({bi + 1}/{len(batches)})", 20 + 78 * bi / len(batches))
            try:
                res = describe_batch(client, b, frames)
            except ai.AIError as ex:
                msg = str(ex)
                log.error(f"AI request {bi + 1} failed: {msg[:200]}")
                if ex.status in (401, 403) or "rejected the key" in msg:
                    raise RuntimeError(msg)
                failed += 1
                continue
            for a in b:
                k = akey(a)
                it = res.get(k)
                if not it:
                    log.warn(f"No description came back for clip {a['num']:03d} (will retry next scan)")
                    continue
                store[k]["desc"] = str(it.get("desc", ""))[:240]
                tags = it.get("tags", [])
                store[k]["tags"] = [str(t).lower() for t in tags][:10] if isinstance(tags, list) else []
                store[k]["mood"] = str(it.get("mood", ""))[:30]
            save_library(store)
    described = sum(1 for a in assets if store.get(akey(a), {}).get("desc"))
    report("Scan finished", 100)
    log.info(f"Scan finished: {described} of {len(assets)} clips described")
    return {"total": len(assets), "described": described, "failed": failed, "ai": bool(use_ai)}