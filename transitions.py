"""MalixAris Video Maker - transitions that keep the audio sync exact (Part 2B)."""
import os, hashlib
import engine

ALLOWED = ["fade", "fadeblack", "fadewhite", "dissolve", "slideleft", "slideright", "slideup",
           "slidedown", "wipeleft", "wiperight", "wipeup", "wipedown", "circleopen", "circleclose",
           "zoomin", "smoothleft", "smoothright", "pixelize", "radial"]
ALIAS = {"crossfade": "fade", "dip": "fadeblack", "dipblack": "fadeblack", "dipwhite": "fadewhite",
         "hardcut": "cut", "none": "cut", "slide": "slideleft", "wipe": "wipeleft", "zoom": "zoomin",
         "circle": "circleopen"}


def clean_type(t):
    t = str(t or "cut").strip().lower().replace(" ", "").replace("_", "").replace("-", "")
    t = ALIAS.get(t, t)
    return t if (t == "cut" or t in ALLOWED) else None


def plan(pieces, fps, tmap, log):
    """Decide which piece boundaries get a transition. h = half length in frames."""
    out = []
    for k in range(len(pieces) - 1):
        a, b = pieces[k], pieces[k + 1]
        if a["line"] == b["line"]:
            continue
        t = (tmap or {}).get(str(a["line"]))
        if not t:
            continue
        name = clean_type(t.get("type"))
        if not name or name == "cut":
            continue
        try:
            dur = max(0.15, min(0.8, float(t.get("dur", 0.4))))
        except Exception:
            dur = 0.4
        if min(a["frames"], b["frames"]) / fps < 0.20:
            log.warn(f"Line {a['line']}: adjacent clips are too short for a visible transition")
            continue
        h = int(round(dur * fps / 2))
        h = min(h, a["frames"] // 3, b["frames"] // 3)
        if h < 2:
            continue
        out.append({"k": k, "line": a["line"], "name": name, "h": h})
    if out:
        log.info(f"Transition plan: {len(out)} visible effect(s) across {len(pieces)} clip pieces")
    return out


def _cmd(fa, fb, name, h, cfg, out, fallback):
    fps, n = cfg["fps"], 2 * h
    # Keep the frame-rate metadata intact. Re-applying setpts/settb here can
    # make some FFmpeg builds report an invalid 1/0 rate to xfade.
    norm = f"fps={fps}"
    tail = "format=yuv420p,setsar=1"
    if fallback:
        # Visible compatibility fallback for FFmpeg builds without xfade:
        # fade the outgoing half to black and fade the incoming half up.
        half = h / fps
        g = (f"[0:v]{norm},trim=end_frame={h},setpts=PTS-STARTPTS,"
             f"fade=t=out:st=0:d={half:.4f}:color=black,{tail}[a];"
             f"[1:v]{norm},trim=end_frame={h},setpts=PTS-STARTPTS,"
             f"fade=t=in:st=0:d={half:.4f}:color=black,{tail}[b];"
             f"[a][b]concat=n=2:v=1:a=0,setsar=1[v]")
    else:
        g = (f"[0:v]{norm},tpad=stop={h}:stop_mode=clone,{tail}[a];"
             f"[1:v]{norm},tpad=start={h}:start_mode=clone,{tail}[b];"
             f"[a][b]xfade=transition={name}:duration={n / fps:.4f}:offset=0,"
             f"format=yuv420p,setsar=1,tpad=stop=2:stop_mode=clone[v]")
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", fa, "-i", fb,
           "-filter_complex", g, "-map", "[v]", "-frames:v", str(n), "-an"]
    return cmd + engine.enc_args(cfg) + ["-pix_fmt", "yuv420p", "-r", str(fps), "-f", "mpegts", out]


def render_trans(fa, fb, name, h, cfg, ctl, log, problems=None):
    key = hashlib.sha1(f"{fa}|{fb}|{name}|{h}|{cfg['fps']}|t3".encode()).hexdigest()[:20]
    out = os.path.join(engine.CACHE, "t_" + key + ".ts")
    fallback_out = os.path.join(engine.CACHE, "tf_" + key + ".ts")
    if os.path.exists(out) and os.path.getsize(out) > 0:
        return out
    if os.path.exists(fallback_out) and os.path.getsize(fallback_out) > 0:
        if problems is not None:
            msg = f"Transition '{name}' used a fade-through-black fallback because FFmpeg could not render the requested effect"
            if msg not in problems: problems.append(msg)
        return fallback_out
    tmp = out + ".part"
    try:
        engine.run_ff(_cmd(fa, fb, name, h, cfg, tmp, False), ctl)
        os.replace(tmp, out)
        log.info(f"Transition rendered: {name} ({2 * h / cfg['fps']:.2f}s)")
        return out
    except engine.Cancelled:
        raise
    except Exception as e:
        try:
            if os.path.exists(tmp): os.remove(tmp)
        except OSError:
            pass
        msg = f"Transition '{name}' failed ({str(e)[:140]}); a fade-through-black fallback was rendered at this boundary"
        log.error(msg)
        if problems is not None: problems.append(msg)
        tmp_fb = fallback_out + ".part"
        engine.run_ff(_cmd(fa, fb, name, h, cfg, tmp_fb, True), ctl)
        os.replace(tmp_fb, fallback_out)
        return fallback_out


def build_segments(pieces, cfg, tplan, ctl, log, report, problems):
    fps = cfg["fps"]
    hin, hout, tinfo = {}, {}, {}
    for t in tplan:
        hout[t["k"]] = t["h"]
        hin[t["k"] + 1] = t["h"]
        tinfo[t["k"]] = t
    pcs = list(pieces)
    mains, last_good, total = {}, None, len(pcs)
    for k, p in enumerate(list(pcs)):
        ctl.check()
        report(f"Rendering clip {k + 1} of {total}", 42 + 48 * k / total)
        a, b = hin.get(k, 0), hout.get(k, 0)
        q = dict(p)
        q["skip"], q["take"] = a, p["frames"] - a - b
        try:
            mains[k] = engine.render_piece(q, cfg, ctl)
            last_good = p
        except engine.Cancelled:
            raise
        except Exception as ex:
            msg = f"Line {p['line']}: clip {p['num']:03d} failed to render ({str(ex)[:120]})"
            log.error(msg)
            problems.append(msg)
            if last_good is None:
                raise RuntimeError(msg)
            fix = engine.make_piece(last_good["asset"], p["frames"], fps)
            fix["line"] = p["line"]
            pcs[k] = fix
            q2 = dict(fix)
            q2["skip"], q2["take"] = a, p["frames"] - a - b
            mains[k] = engine.render_piece(q2, cfg, ctl)
            last_good = fix
            log.warn(f"Line {p['line']}: repeated previous clip {last_good['num']:03d} instead")
    trans = {}
    keys = sorted(tinfo)
    try:
        for i, k in enumerate(keys):
            ctl.check()
            report(f"Rendering transition {i + 1} of {len(keys)}", 90 + 5 * i / len(keys))
            t = tinfo[k]
            h = t["h"]
            a, b = dict(pcs[k]), dict(pcs[k + 1])
            a.update(skip=a["frames"] - h, take=h)
            b.update(skip=0, take=h)
            fa = engine.render_piece(a, cfg, ctl)
            fb = engine.render_piece(b, cfg, ctl)
            trans[k] = render_trans(fa, fb, t["name"], h, cfg, ctl, log, problems)
    except engine.Cancelled:
        raise
    except Exception as ex:
        msg = f"Transitions failed ({str(ex)[:150]}) - rendering the whole video with hard cuts instead"
        log.error(msg)
        problems.append(msg)
        return build_segments(pieces, cfg, [], ctl, log, report, problems)
    segs = []
    for k in range(len(pcs)):
        segs.append(mains[k])
        if k in trans:
            segs.append(trans[k])
    if tplan:
        rendered = sum(1 for k in keys if k in trans and os.path.basename(trans[k]).startswith("t_"))
        log.info(f"Transition render result: {len(trans)} boundaries processed")
    return segs