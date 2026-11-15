"""MalixAris Video Maker - desktop window. Made by MalixAris & Usman Mughal."""
import os, sys, json, threading, subprocess, traceback, pathlib

ROOT = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
os.environ["PATH"] = os.path.join(ROOT, "tools", "ffmpeg", "bin") + os.pathsep + os.environ["PATH"]
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
DATA = os.path.join(ROOT, "data")
os.makedirs(DATA, exist_ok=True)

import webview
import engine
import ai
import scanner
import project
import agent

VERSION = "3.2 (MalixAris Studio — Timeline, Transitions & Playback Fixes)"


class Api:
    def __init__(self):
        self._log = engine.Log()
        self._ctl = engine.Ctl()
        self._lib = None
        self._libkey = None
        self._window = None
        self._s = {"running": False, "stage": "Idle", "progress": 0, "job": 0, "result": None, "error": None,
                   "scan_done": 0, "scan_error": None, "scan_summary": None}

    # ---- info / settings
    def get_info(self):
        return {"version": VERSION, "authors": "MalixAris & Usman Mughal", "system": engine.sysreport()}

    def load_settings(self):
        try:
            with open(os.path.join(DATA, "settings.json"), encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_settings(self, d):
        with open(os.path.join(DATA, "settings.json"), "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        return True

    # ---- dialogs
    def _dlg(self, folder=False, types=()):
        FD = getattr(webview, "FileDialog", None)
        if FD:
            mode = FD.FOLDER if folder else FD.OPEN
        else:
            mode = webview.FOLDER_DIALOG if folder else webview.OPEN_DIALOG
        r = self._window.create_file_dialog(mode, allow_multiple=False, file_types=types)
        return r[0] if r else ""

    def pick_folder(self):
        return self._dlg(folder=True)

    def pick_audio(self):
        return self._dlg(types=("Audio files (*.mp3;*.wav;*.m4a;*.aac;*.flac;*.ogg;*.opus;*.mp4)", "All files (*.*)"))

    def pick_text(self):
        return self._dlg(types=("Text files (*.txt)", "All files (*.*)"))

    def read_text(self, path):
        for enc in ("utf-8-sig", "utf-16", "cp1252"):
            try:
                with open(path, encoding=enc) as f:
                    return f.read()
            except Exception:
                continue
        return ""

    # ---- library / inspect
    def _get_lib(self, folder, force=False):
        if not folder or not os.path.isdir(folder):
            return None
        if force or self._lib is None or self._libkey != folder:
            self._lib = engine.scan_library(folder, self._log)
            self._libkey = folder
        return self._lib

    def inspect(self, opts, force=False):
        try:
            return engine.inspect(opts, self._get_lib(opts.get("clips_dir", ""), force))
        except Exception as e:
            self._log.error(f"Inspect failed: {e}")
            return {"ok": False, "error": str(e)}

    # ---- AI settings (Part 2A)
    def ai_status(self):
        cfg = ai.load_cfg()
        if cfg.get("model") != "gemini-3.6-flash":
            cfg = ai.save_cfg({"model": "gemini-3.6-flash"})
        return {"has_key": bool(ai.get_key()), "enabled": cfg.get("enabled", True),
                "model": "gemini-3.6-flash", "active_model": "gemini-3.6-flash",
                "models": ["gemini-3.6-flash"]}

    def ai_save_key(self, key):
        ai.set_key(key)
        ai.save_cfg({"enabled": True})
        self._log.info("Gemini key saved on this PC")
        return True

    def ai_remove_key(self):
        ai.remove_key()
        self._log.info("Gemini key removed")
        return True

    def ai_set(self, d):
        upd = {}
        if "enabled" in d:
            upd["enabled"] = bool(d["enabled"])
        if "model" in d:
            upd["model"] = "gemini-3.6-flash"
        ai.save_cfg(upd)
        return True

    def ai_test(self):
        try:
            key = ai.get_key()
            if not key:
                return {"ok": False, "error": "No key saved yet"}
            ai.save_cfg({"model": "gemini-3.6-flash"})
            c = ai.Client(self._log, None, min_gap=0)
            c.ask([{"text": 'Reply with this JSON: {"reply":"ok"}'}], tries=3)
            ai.save_cfg({"active_model": c.active, "models_cache": [c.active]})
            self._log.info(f"Gemini connected, pinned model: {c.active}")
            return {"ok": True, "model": c.active, "models": [c.active]}
        except ai.AIError as e:
            self._log.error(f"Gemini test failed: {e}")
            return {"ok": False, "error": str(e)[:220]}
        except Exception as e:
            self._log.error(f"Gemini test failed: {e}")
            return {"ok": False, "error": str(e)[:220]}

    def get_library(self):
        if not self._lib:
            return []
        store = scanner.load_library()
        out = []
        for kind, d in (("video", self._lib["videos"]), ("image", self._lib["images"])):
            for num in sorted(d):
                e = store.get(("v" if kind == "video" else "i") + str(num), {})
                th = e.get("thumb", "")
                out.append({"num": num, "kind": kind, "desc": e.get("desc", ""), "tags": e.get("tags", []),
                            "thumb": th if th and os.path.exists(th) else ""})
        return out

    def _scan_worker(self, opts):
        try:
            lib = self._get_lib(opts.get("clips_dir", ""), force=True)
            if not lib or not (lib["videos"] or lib["images"]):
                raise RuntimeError("Choose a clips folder with videos first (Project page)")
            use_ai = bool(ai.get_key()) and ai.load_cfg().get("enabled", True)
            if not use_ai:
                self._log.warn("No Gemini key or AI is switched off - only thumbnails will be made")
            self._s["scan_summary"] = scanner.scan(lib, self._log, self._report, self._ctl, use_ai)
        except engine.Cancelled:
            self._log.warn("Scan stopped by user (progress is saved, press Scan again to continue)")
            self._s["stage"] = "Cancelled"
        except Exception as e:
            self._log.error(str(e))
            self._s["scan_error"] = str(e)[:250]
            self._s["stage"] = "Error"
        finally:
            self._s["running"] = False
            self._s["scan_done"] += 1

    def start_scan(self, opts):
        if self._s["running"]:
            return {"ok": False, "error": "A job is already running"}
        self._s.update(running=True, stage="Scanning clips", progress=0, scan_error=None, scan_summary=None)
        threading.Thread(target=self._scan_worker, args=(opts,), daemon=True).start()
        return {"ok": True}

    # ---- AI agent (Part 2B)
    def agent_chat(self, message, opts):
        try:
            lib = self._get_lib(opts.get("clips_dir", ""))
            return agent.chat(message, opts, lib, self._log)
        except ai.AIError as e:
            self._log.error(f"Agent failed: {e}")
            return {"ok": False, "reply": "Gemini problem: " + str(e)[:200]}
        except Exception as e:
            self._log.error(f"Agent failed: {e} {traceback.format_exc()[-400:]}")
            return {"ok": False, "reply": "Something went wrong: " + str(e)[:200]}

    def agent_undo(self, opts=None):
        shash = project.project_hash((opts or {}).get("script", ""), (opts or {}).get("clips_dir", ""), (opts or {}).get("audio", "")) if opts else None
        legacy = project.script_hash((opts or {}).get("script", "")) if opts else None
        label = project.undo(shash, legacy)
        if label is None:
            return {"ok": False}
        self._log.info(f"Undone: {label}")
        return {"ok": True, "label": label}

    def agent_info(self, opts=None):
        shash = project.project_hash((opts or {}).get("script", ""), (opts or {}).get("clips_dir", ""), (opts or {}).get("audio", "")) if opts else None
        legacy = project.script_hash((opts or {}).get("script", "")) if opts else None
        s = project.load_for(shash, legacy) if shash else project.load()
        return {"history": [h["label"] for h in s["history"]][-6:], "style": s.get("style", ""),
                "edited_lines": len(s.get("overrides", {})), "transitions": len(s.get("transitions", {}))}

    def agent_reset(self, opts=None):
        shash = project.project_hash((opts or {}).get("script", ""), (opts or {}).get("clips_dir", ""), (opts or {}).get("audio", "")) if opts else None
        legacy = project.script_hash((opts or {}).get("script", "")) if opts else None
        project.reset_all(shash, legacy)
        self._log.info("All agent edits cleared (Undo can bring them back)")
        return True

    # ---- named project manager
    def list_projects(self):
        return project.list_named_projects()

    def create_project(self, name, opts=None):
        try:
            row = project.create_named_project(name, opts or {})
            self._log.info(f"Created project: {row['name']}")
            return {"ok": True, "project": row}
        except Exception as e:
            self._log.error(f"Could not create project: {e}")
            return {"ok": False, "error": str(e)}

    def save_project(self, opts, project_id="", name=""):
        try:
            row = project.save_named_project(opts or {}, project_id, name)
            self._log.info(f"Saved project: {row['name']}")
            return {"ok": True, "project": row}
        except Exception as e:
            self._log.error(f"Could not save project: {e}")
            return {"ok": False, "error": str(e)}

    def load_project(self, project_id):
        try:
            row = project.load_named_project(project_id)
            return {"ok": bool(row), "project": row} if row else {"ok": False, "error": "Project not found"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def rename_project(self, project_id, name):
        return {"ok": project.rename_named_project(project_id, name)}

    def duplicate_project(self, project_id):
        row = project.duplicate_named_project(project_id)
        return {"ok": bool(row), "project": row} if row else {"ok": False, "error": "Project not found"}

    def delete_project(self, project_id):
        return {"ok": project.delete_named_project(project_id)}

    # ---- job control
    def _report(self, stage, pct):
        self._s["stage"] = stage
        self._s["progress"] = round(pct, 1)

    def _worker(self, opts, do_render):
        try:
            lib = self._get_lib(opts.get("clips_dir", ""), force=True)
            res = engine.run_job(opts, do_render, self._log, self._report, self._ctl, lib)
            if isinstance(res, dict) and res.get("output"):
                try:
                    res["output_uri"] = pathlib.Path(res["output"]).resolve().as_uri()
                except Exception:
                    res["output_uri"] = ""
            self._s["result"] = res
        except engine.Cancelled:
            self._log.warn("Cancelled by user")
            self._s["stage"] = "Cancelled"
        except Exception as e:
            self._log.error(str(e))
            self._log.error(traceback.format_exc()[-800:])
            self._s["error"] = str(e)
            self._s["stage"] = "Error"
        finally:
            self._s["running"] = False

    def start(self, opts, do_render=True):
        if self._s["running"]:
            return {"ok": False, "error": "A job is already running"}
        self._s.update(running=True, stage="Starting", progress=0, result=None, error=None, job=self._s["job"] + 1)
        threading.Thread(target=self._worker, args=(opts, bool(do_render)), daemon=True).start()
        return {"ok": True}

    def cancel(self):
        self._ctl.stop()
        return True

    def get_state(self, log_index=0):
        logs, idx = self._log.since(log_index)
        d = dict(self._s)
        d["logs"], d["log_index"] = logs, idx
        return d

    def list_outputs(self):
        """Return previously rendered MP4 projects so users can replay old exports."""
        rows = []
        try:
            for name in os.listdir(engine.OUT):
                path = os.path.abspath(os.path.join(engine.OUT, name))
                if not name.lower().endswith((".mp4", ".mov", ".mkv", ".webm")) or not os.path.isfile(path):
                    continue
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                duration = 0  # browser reads the actual duration when playback starts
                try:
                    uri = pathlib.Path(path).resolve().as_uri()
                except Exception:
                    uri = ""
                rows.append({"name": name, "path": path, "uri": uri, "size": st.st_size,
                             "modified": st.st_mtime, "duration": round(duration, 2)})
        except Exception as e:
            self._log.warn(f"Could not list rendered projects: {e}")
        rows.sort(key=lambda x: x["modified"], reverse=True)
        return rows

    def output_uri(self, path):
        try:
            p = pathlib.Path(str(path or "")).resolve()
            return p.as_uri() if p.is_file() else ""
        except Exception:
            return ""

    def open_output(self, path=""):
        try:
            if path and os.path.exists(path):
                subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
            else:
                os.startfile(engine.OUT)
        except Exception as e:
            self._log.error(f"Cannot open folder: {e}")
        return True


if __name__ == "__main__":
    api = Api()
    import part2c
    part2c.install(Api)
    import finish
    finish.install(Api)
    import director
    director.install(Api)
    import polish
    polish.install(Api)
    import voicecmd
    voicecmd.install(Api)
    window = webview.create_window("MalixAris Studio", os.path.join(ROOT, "web", "index.html"),
                                   js_api=api, width=1480, height=940, min_size=(1120, 720),
                                   background_color="#0d0e14")
    api._window = window
    try:
        webview.start(gui="edgechromium")
    except Exception as e:
        print("Could not start the app window:", e)
        print("Install Microsoft Edge WebView2 Runtime from https://developer.microsoft.com/microsoft-edge/webview2/")
        sys.exit(1)