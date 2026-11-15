"""MalixAris Video Maker - Gemini connection (Part 2A)."""
import os, sys, re, json, time, base64
import urllib.request, urllib.error

ROOT = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
os.makedirs(DATA, exist_ok=True)
CFG_PATH = os.path.join(DATA, "ai_settings.json")
KEY_FILE = os.path.join(DATA, "gemini.key")
SERVICE, USER = "MalixAris", "gemini_api_key"
BASE = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_CFG = {"enabled": True, "model": "gemini-3.6-flash", "models_cache": [], "active_model": "gemini-3.6-flash"}


class AIError(Exception):
    def __init__(self, msg, status=0, retry=0):
        super().__init__(msg)
        self.status = status
        self.retry = retry


# ---------------------------------------------------------------- settings
def load_cfg():
    cfg = dict(DEFAULT_CFG)
    try:
        with open(CFG_PATH, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


def save_cfg(upd):
    cfg = load_cfg()
    cfg.update(upd)
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    return cfg


# ---------------------------------------------------------------- key storage
def get_key():
    try:
        import keyring
        k = keyring.get_password(SERVICE, USER)
        if k:
            return k
    except Exception:
        pass
    try:
        with open(KEY_FILE, "rb") as f:
            return base64.b64decode(f.read()).decode("utf-8").strip()
    except Exception:
        return ""


def set_key(key):
    key = key.strip()
    stored = False
    try:
        import keyring
        keyring.set_password(SERVICE, USER, key)
        stored = True
    except Exception:
        pass
    if not stored:
        with open(KEY_FILE, "wb") as f:
            f.write(base64.b64encode(key.encode("utf-8")))
    return True


def remove_key():
    try:
        import keyring
        keyring.delete_password(SERVICE, USER)
    except Exception:
        pass
    try:
        os.remove(KEY_FILE)
    except Exception:
        pass
    save_cfg({"active_model": "", "models_cache": []})


# ---------------------------------------------------------------- http
def _http(method, url, key, body=None, timeout=120):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json", "x-goog-api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        msg, retry = raw[:300], 0
        try:
            retry = float(e.headers.get("Retry-After", 0) or 0)
        except Exception:
            retry = 0
        try:
            j = json.loads(raw)
            msg = j["error"].get("message", msg)
            for d in j["error"].get("details", []):
                rd = d.get("retryDelay")
                if rd:
                    retry = float(str(rd).rstrip("s"))
        except Exception:
            pass
        raise AIError(msg, e.code, retry)
    except urllib.error.URLError as e:
        raise AIError(f"Network problem: {e.reason}")
    except Exception as e:
        raise AIError(str(e))


# ---------------------------------------------------------------- models
BAD = ("image", "tts", "live", "audio", "embed", "robotics", "computer", "learnlm",
       "gemma", "aqa", "imagen", "veo", "exp")


def list_models(key):
    out, token = [], ""
    while True:
        url = f"{BASE}/models?pageSize=100" + (f"&pageToken={token}" if token else "")
        j = _http("GET", url, key, timeout=30)
        for m in j.get("models", []):
            if "generateContent" in m.get("supportedGenerationMethods", []):
                out.append(m["name"].split("/")[-1])
        token = j.get("nextPageToken", "")
        if not token:
            break
    return out


def rank_models(names):
    scored = []
    for n in names:
        low = n.lower()
        if "flash" not in low or any(b in low for b in BAD):
            continue
        m = re.search(r"gemini-(\d+(?:\.\d+)?)", low)
        score = float(m.group(1)) if m else 0.0
        if "lite" in low:
            score -= 0.4
        if "preview" in low or "latest" in low:
            score -= 0.05
        scored.append((score, n))
    scored.sort(reverse=True)
    return [n for _, n in scored]


def generate(key, model, parts, system=None, temperature=0.3, timeout=60):
    body = {"contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"temperature": temperature, "responseMimeType": "application/json"}}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    j = _http("POST", f"{BASE}/models/{model}:generateContent", key, body, timeout)
    try:
        cand = j["candidates"][0]
        return "".join(p.get("text", "") for p in cand["content"]["parts"] if not p.get("thought"))
    except Exception:
        reason = j.get("promptFeedback", {}).get("blockReason", "empty answer")
        raise AIError(f"Gemini returned no text ({reason})")


def parse_json(text):
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    try:
        return json.loads(t)
    except Exception:
        m = re.search(r"[\[{].*[\]}]", t, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
        raise AIError("Gemini answer was not valid JSON")


# ---------------------------------------------------------------- client
class Client:
    """Throttled Gemini caller with retry, rate-limit waiting and model fallback."""

    def __init__(self, log, ctl=None, min_gap=6.5):
        self.log, self.ctl, self.min_gap = log, ctl, min_gap
        self.key = get_key()
        self.models = []
        self.active = ""
        self.last = 0.0

    def _sleep(self, sec):
        end = time.time() + sec
        while time.time() < end:
            if self.ctl:
                self.ctl.check()
            time.sleep(0.4)

    def _pick(self):
        # Product-wide fixed model: do not rotate to newer models after a rate limit.
        model = "gemini-3.6-flash"
        save_cfg({"model": model})
        self.models = [model]
        self.log.info("Gemini model pinned: " + model)

    def ask(self, parts, system=None, temperature=0.3, tries=6):
        if not self.key:
            raise AIError("No Gemini key saved")
        if not self.models:
            self._pick()
        mi, last = 0, None
        for attempt in range(tries + len(self.models)):
            self._sleep(self.min_gap - (time.time() - self.last))
            model = self.models[mi % len(self.models)]
            self.last = time.time()
            try:
                data = parse_json(generate(self.key, model, parts, system, temperature))
                self.active = model
                return data
            except AIError as e:
                last, msg = e, str(e)
                if e.status in (401, 403) or (e.status == 400 and "API key" in msg):
                    raise AIError("Gemini rejected the key: " + msg[:160], e.status)
                if e.status == 404 or (e.status == 429 and "limit: 0" in msg):
                    self.log.warn(f"Model {model} not usable ({e.status}) - trying the next one")
                    mi += 1
                    continue
                if e.status == 429:
                    wait = min(max(e.retry, 8 * (attempt + 1)), 75)
                    self.log.warn(f"Gemini rate limit - waiting {wait:.0f}s")
                    self._sleep(wait)
                    if attempt >= 2:
                        mi += 1
                    continue
                wait = 4 * (attempt + 1)
                self.log.warn(f"Gemini problem ({e.status}): {msg[:100]} - retry in {wait}s")
                self._sleep(wait)
                if e.status in (0, 500, 503):
                    mi += 1
        raise last or AIError("Gemini did not answer")