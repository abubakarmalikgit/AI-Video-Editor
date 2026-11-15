"""MalixAris Video Maker - AI clip matching with rule checks (Part 2A)."""
import os, json
import ai, scanner

PLAN_PATH = os.path.join(ai.DATA, "last_plan.json")
BATCH = 25
RECENT = 8

SYSTEM = ("You are a professional video editor choosing b-roll clips to illustrate a voiceover. "
          "Match the MEANING and mood of each line. Answer with JSON only.")


def sequential(need, lib):
    nums = sorted(lib["videos"]) or sorted(lib["images"])
    out, ptr = {}, 0
    for ln in need:
        out[ln["idx"]] = [nums[(ptr + k) % len(nums)] for k in range(ln["n"])]
        ptr += ln["n"]
    return out


def _least_used(pool, usage, exclude, near):
    cands = [c for c in pool if c not in exclude]
    if not cands:
        return None
    return min(cands, key=lambda c: (usage.get(c, 0), abs(c - near)))


def _fix(raw, n, pool_ai, pool_all, usage, recent):
    """Rule checker: valid numbers only, no repeats inside a line, no recent reuse, exact count."""
    res = []
    for c in raw or []:
        try:
            c = int(c)
        except Exception:
            continue
        if c not in pool_all or c in res:
            continue
        if c in recent:
            sub = _least_used(pool_ai or pool_all, usage, set(res) | recent, c)
            if sub is not None:
                res.append(sub)
        else:
            res.append(c)
        if len(res) >= n:
            break
    near = res[-1] if res else 0
    while len(res) < n:
        c = _least_used(pool_all, usage, set(res) | recent, near)
        if c is None:
            c = _least_used(pool_all, usage, set(res), near)
        if c is None:
            c = sorted(pool_all)[len(res) % len(pool_all)]
        res.append(c)
        near = c
    return res[:n]


def match(need, lib, opts, log, report, ctl):
    cfg = ai.load_cfg()
    pool_all = set(lib["videos"]) or set(lib["images"])
    kind = "v" if lib["videos"] else "i"
    if not (cfg.get("enabled") and ai.get_key()):
        log.info("AI matching is off or no Gemini key is saved - clips are used in order")
        return sequential(need, lib)
    store = scanner.load_library()
    cat = {n: store[f"{kind}{n}"] for n in pool_all if store.get(f"{kind}{n}", {}).get("desc")}
    if len(cat) < max(3, int(len(pool_all) * 0.5)):
        log.warn("Most clips have no AI description yet. Open the Library page and press 'Scan clips' first. "
                 "Using clips in order for now.")
        return sequential(need, lib)
    if len(cat) < len(pool_all):
        log.warn(f"{len(pool_all) - len(cat)} clips have no description and are only used as fill-ins")
    catalog = "\n".join(f"{n}: {e['desc']} | {', '.join(e.get('tags', []))}" for n, e in sorted(cat.items()))
    client = ai.Client(log, ctl)
    usage, hist, picks, plan = {}, [], {}, []
    batches = [need[i:i + BATCH] for i in range(0, len(need), BATCH)]
    for bi, b in enumerate(batches):
        ctl.check()
        report(f"AI is choosing clips ({bi + 1}/{len(batches)})", 41 + bi / len(batches))
        recent = set().union(*hist[-RECENT:]) if hist else set()
        lines = "\n".join(f'{ln["idx"]} | {ln["dur"]}s | {ln["n"]} clip(s) | {ln["text"]}' for ln in b)
        prompt = (f"CLIP LIBRARY (id: description | tags):\n{catalog}\n\n"
                  f"CLIPS USED JUST BEFORE THIS BATCH (avoid): {sorted(recent)}\n\n"
                  f"LINES (idx | duration | clips needed | text):\n{lines}\n\n"
                  "RULES:\n"
                  "- For each line choose exactly the number of clips needed, using only ids from the library.\n"
                  "- Never use the same clip twice in one line; avoid clips used in the previous 8 lines.\n"
                  "- Prefer clips not used yet; reuse only if nothing else fits.\n"
                  "- For lines with several clips, order them so they follow the sentence.\n"
                  '- Return JSON only: {"lines":[{"idx":1,"clips":[12,45]}]}')
        ans = {}
        try:
            data = client.ask([{"text": prompt}], system=SYSTEM, temperature=0.4)
            rows = data.get("lines") if isinstance(data, dict) else data
            for r in rows or []:
                if isinstance(r, dict) and "idx" in r:
                    ans[int(r["idx"])] = r.get("clips")
        except ai.AIError as ex:
            log.error(f"AI matching request {bi + 1} failed: {str(ex)[:200]} - these lines use rotating clips")
        except (KeyError, ValueError, TypeError):
            log.error(f"AI matching request {bi + 1} gave an unreadable answer - these lines use rotating clips")
        for ln in b:
            chosen = _fix(ans.get(ln["idx"]), ln["n"], set(cat), pool_all, usage, recent)
            picks[ln["idx"]] = chosen
            for c in chosen:
                usage[c] = usage.get(c, 0) + 1
            hist.append(set(chosen))
            recent = set().union(*hist[-RECENT:])
            plan.append({"idx": ln["idx"], "text": ln["text"], "clips": chosen})
    try:
        with open(PLAN_PATH, "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=1)
    except Exception:
        pass
    again = sum(1 for v in usage.values() if v > 1)
    log.info(f"AI matching done: {len(usage)} different clips used, {again} used more than once")
    return picks