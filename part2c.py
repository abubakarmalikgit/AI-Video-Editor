"""MalixAris Part 2C: small helpers added to the Api class."""
from pathlib import Path
import sys

BASE = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
LOG_FILE = BASE / "logs" / "app.log"


def get_log_text(self, max_lines=400):
    try:
        if not LOG_FILE.exists():
            return {"ok": True, "text": "(log is empty)"}
        lines = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
        return {"ok": True, "text": "\n".join(lines[-int(max_lines):])}
    except Exception as e:
        return {"ok": False, "text": "", "error": str(e)}


def agent_live(self):
    try:
        import agent
        return agent.live_get()
    except Exception as e:
        return {"id": 0, "active": False, "error": str(e)}


def install(api_class):
    api_class.get_log_text = get_log_text
    api_class.agent_live = agent_live
