"""Part 2C streaming client: pinned to Gemini 3.6 Flash with quota-aware retries."""
import json, time, random, threading, urllib.request, urllib.error
import ai

MODEL = "gemini-3.6-flash"
FIRST_BYTE_TIMEOUT = 120
_REQUEST_LOCK = threading.Lock()
_API_CALL_LOCK = threading.Lock()
_LAST_REQUEST = 0.0
_MIN_GLOBAL_GAP = 4.0


def _read_error(e):
    raw = e.read().decode("utf-8", "replace")
    msg, retry = raw[:400], 0.0
    try:
        retry = float(e.headers.get("Retry-After", 0) or 0)
    except Exception:
        retry = 0.0
    try:
        j = json.loads(raw)
        msg = j["error"].get("message", msg)
        for detail in j["error"].get("details", []):
            delay = detail.get("retryDelay")
            if delay:
                retry = float(str(delay).rstrip("s"))
    except Exception:
        pass
    return ai.AIError(msg, e.code, retry)


def _throttle():
    global _LAST_REQUEST
    with _REQUEST_LOCK:
        wait = _MIN_GLOBAL_GAP - (time.time() - _LAST_REQUEST)
        if wait > 0:
            time.sleep(wait)
        _LAST_REQUEST = time.time()


def stream_generate(key, model, parts, system, temperature, on_thought=None, on_text=None, thoughts=False):
    cfg = {"temperature": temperature, "responseMimeType": "application/json"}
    if thoughts:
        cfg["thinkingConfig"] = {"includeThoughts": True}
    body = {"contents": [{"role": "user", "parts": parts}], "generationConfig": cfg}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    url = f"{ai.BASE}/models/{model}:streamGenerateContent?alt=sse"
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", "x-goog-api-key": key})
    text = ""
    try:
        with urllib.request.urlopen(req, timeout=FIRST_BYTE_TIMEOUT) as r:
            for raw in r:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if not payload or payload == "[DONE]":
                    continue
                try:
                    j = json.loads(payload)
                    ps = j["candidates"][0]["content"]["parts"]
                except Exception:
                    continue
                for part in ps:
                    t = part.get("text", "")
                    if not t:
                        continue
                    if part.get("thought"):
                        if on_thought:
                            on_thought(t)
                    else:
                        text += t
                        if on_text:
                            on_text(text)
    except urllib.error.HTTPError as e:
        raise _read_error(e)
    except urllib.error.URLError as e:
        raise ai.AIError(f"Network problem: {e.reason}")
    except ai.AIError:
        raise
    except Exception as e:
        raise ai.AIError(str(e) or "The read operation timed out")
    if not text.strip():
        raise ai.AIError("Gemini returned no text")
    return text


def _pick(self):
    # User explicitly selected Gemini 3.6 Flash; never silently rotate to other models.
    ai.save_cfg({"model": MODEL})
    self.models = [MODEL]
    self.log.info("Gemini model pinned: " + MODEL)


def ask_stream(self, parts, system=None, temperature=0.3,
               on_thought=None, on_text=None, on_status=None):
    if not self.key:
        raise ai.AIError("No Gemini key saved")
    if not self.models:
        self._pick()
    last = None
    for attempt in range(5):
        if on_status:
            on_status(f"Gemini 3.6 Flash · attempt {attempt + 1}/5")
        try:
            with _API_CALL_LOCK:
                _throttle()
                txt = stream_generate(self.key, MODEL, parts, system, temperature,
                                      on_thought, on_text, False)
            data = ai.parse_json(txt)
            self.active = MODEL
            ai.save_cfg({"active_model": MODEL})
            return data
        except ai.AIError as e:
            last = e
            msg = str(e)
            if e.status in (401, 403) or (e.status == 400 and "API key" in msg):
                raise ai.AIError("Gemini rejected the key: " + msg[:180], e.status)
            if e.status == 404:
                raise ai.AIError(f"Gemini model {MODEL} is unavailable for this API key. Check model access.", 404)
            if e.status == 429:
                low = msg.lower()
                if any(token in low for token in ("limit: 0", "per_day", "daily limit", "quota exceeded", "resource_exhausted")):
                    raise ai.AIError("Gemini 3.6 Flash quota is exhausted for this API key. The app is pinned to 3.6 Flash; wait for the provider quota to reset or check the key's API limits.", 429, e.retry)
                delay = max(e.retry, min(180, 20 * (2 ** attempt))) + random.uniform(0.5, 2.0)
                self.log.warn(f"Gemini 3.6 Flash rate limit; waiting {delay:.0f}s before retry {attempt + 2}/5")
            elif e.status in (0, 500, 503):
                delay = min(45, 5 * (attempt + 1)) + random.uniform(0.2, 1.0)
                self.log.warn(f"Gemini 3.6 Flash temporary error ({e.status}); retrying in {delay:.0f}s: {msg[:100]}")
            else:
                raise
            if attempt == 4:
                break
            if on_status:
                on_status(f"Waiting {delay:.0f}s for Gemini 3.6 Flash")
            self._sleep(delay)
    raise last or ai.AIError("Gemini 3.6 Flash did not answer")


# Keep non-streaming library description calls on the same pinned model and use bounded retries.
_original_ask = ai.Client.ask

def ask_pinned(self, parts, system=None, temperature=0.3, tries=4):
    if not self.key:
        raise ai.AIError("No Gemini key saved")
    if not self.models:
        self._pick()
    last = None
    for attempt in range(min(5, max(1, tries))):
        try:
            with _API_CALL_LOCK:
                _throttle()
                data = ai.parse_json(ai.generate(self.key, MODEL, parts, system, temperature, timeout=FIRST_BYTE_TIMEOUT))
            self.active = MODEL
            ai.save_cfg({"active_model": MODEL})
            return data
        except ai.AIError as e:
            last = e
            if e.status in (401, 403, 404) or (e.status == 400 and "API key" in str(e)):
                raise
            if e.status == 429:
                low = str(e).lower()
                if any(token in low for token in ("limit: 0", "per_day", "daily limit", "quota exceeded", "resource_exhausted")):
                    raise ai.AIError("Gemini 3.6 Flash quota is exhausted for this API key. Wait for the provider quota to reset or check the key's API limits.", 429, e.retry)
                delay = max(e.retry, min(180, 20 * (2 ** attempt)))
            elif e.status in (0, 500, 503):
                delay = min(45, 5 * (attempt + 1))
            else:
                raise
            self.log.warn(f"Gemini 3.6 Flash request delayed; retrying in {delay:.0f}s")
            if attempt < min(5, max(1, tries)) - 1:
                self._sleep(delay)
    raise last or ai.AIError("Gemini 3.6 Flash did not answer")


ai.Client._pick = _pick
ai.Client.ask = ask_pinned
ai.Client.ask_stream = ask_stream
