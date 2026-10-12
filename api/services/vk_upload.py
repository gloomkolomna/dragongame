import os
import json
import time
import random
import threading

_lock = threading.Lock()
_cache = {}
_reverse = {}
_negative = {}
_inflight = {}
_disk_loaded = False

DISK_CACHE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "var",
    "upload_cache.json",
)
NEGATIVE_TTL_SECONDS = 900

INTERACTIVE_BUDGET_SECONDS = 20.0
BACKGROUND_BUDGET_SECONDS = 60.0
INTERACTIVE_DELAYS = [1.5, 4.0, 8.0]
BACKGROUND_DELAYS = [2.0, 8.0, 20.0, 30.0]

_JPEG_MAGIC = b"\xff\xd8\xff"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def enabled() -> bool:
    import config
    return getattr(config, "UPLOAD_CACHE_ENABLED", True)


def _key(filepath: str) -> str:
    return os.path.normpath(os.path.abspath(filepath))


def _load_disk() -> None:
    global _disk_loaded
    if _disk_loaded:
        return
    _disk_loaded = True
    try:
        with open(DISK_CACHE_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError):
        return
    if isinstance(raw, dict):
        for k, v in raw.items():
            if isinstance(v, list) and len(v) == 3:
                _cache[k] = (int(v[0]), int(v[1]), v[2])
                _reverse[v[2]] = k


def _save_disk() -> None:
    try:
        os.makedirs(os.path.dirname(DISK_CACHE_PATH), exist_ok=True)
        tmp = DISK_CACHE_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({k: list(v) for k, v in _cache.items()}, f, ensure_ascii=False)
        os.replace(tmp, DISK_CACHE_PATH)
    except OSError:
        pass


def get(filepath: str) -> str:
    if not enabled():
        return ""
    try:
        st = os.stat(filepath)
    except OSError:
        return ""
    _load_disk()
    key = _key(filepath)
    with _lock:
        entry = _cache.get(key)
    if not entry:
        return ""
    mtime, size, attachment = entry
    if int(st.st_mtime) != mtime or st.st_size != size:
        _forget(key)
        return ""
    return attachment


def store(filepath: str, attachment: str) -> None:
    if not enabled() or not attachment:
        return
    try:
        st = os.stat(filepath)
    except OSError:
        return
    key = _key(filepath)
    with _lock:
        old = _cache.get(key)
        if old:
            _reverse.pop(old[2], None)
        _cache[key] = (int(st.st_mtime), st.st_size, attachment)
        _reverse[attachment] = key
    _save_disk()


def invalidate_by_attachment(attachment: str):
    if not enabled() or not attachment:
        return None
    with _lock:
        key = _reverse.get(attachment)
        if key:
            entry = _cache.get(key)
            if entry:
                _reverse.pop(entry[2], None)
            _cache.pop(key, None)
    if key:
        _save_disk()
    return key


def _forget(key: str) -> None:
    with _lock:
        entry = _cache.pop(key, None)
        if entry:
            _reverse.pop(entry[2], None)


def clear() -> None:
    global _disk_loaded
    with _lock:
        _cache.clear()
        _reverse.clear()
        _negative.clear()
    _disk_loaded = True
    try:
        os.remove(DISK_CACHE_PATH)
    except OSError:
        pass


def _negative_active(key: str) -> bool:
    now = time.time()
    with _lock:
        exp = _negative.get(key)
        if exp is None:
            return False
        if exp <= now:
            _negative.pop(key, None)
            return False
        return True


def _negative_put(key: str) -> None:
    with _lock:
        _negative[key] = time.time() + NEGATIVE_TTL_SECONDS


def sniff_image(filepath: str) -> tuple[str, str]:
    name = os.path.basename(filepath)
    ext = os.path.splitext(name)[1].lower()
    try:
        with open(filepath, "rb") as f:
            head = f.read(8)
    except OSError:
        head = b""
    if head.startswith(_JPEG_MAGIC):
        return "image.jpg", "image/jpeg"
    if head.startswith(_PNG_MAGIC):
        return "image.png", "image/png"
    mime = "application/octet-stream"
    if ext in (".jpg", ".jpeg"):
        mime = "image/jpeg"
    elif ext == ".png":
        mime = "image/png"
    return name or "image.jpg", mime


_session = None
_session_lock = threading.Lock()


def _http_session():
    global _session
    with _session_lock:
        if _session is None:
            import requests
            _session = requests.Session()
            _session.headers.pop("user-agent", None)
        return _session


def _http_post(upload_url: str, filepath: str, timeout):
    session = _http_session()
    filename, mime = sniff_image(filepath)
    with open(filepath, "rb") as f:
        resp = session.post(upload_url, files={"photo": (filename, f, mime)}, timeout=timeout)
    resp.raise_for_status()
    return resp


def _retryable_error(e) -> bool:
    import requests
    if isinstance(e, requests.exceptions.HTTPError):
        status = e.response.status_code if e.response is not None else 0
        return status >= 500 or status == 429
    if isinstance(e, (requests.exceptions.Timeout, requests.exceptions.ConnectionError)):
        return True
    code = getattr(e, "code", None)
    if isinstance(code, int) and code in (6, 9, 10):
        return True
    return False


def attachment_rejected(err) -> bool:
    code = getattr(err, "code", None)
    if not isinstance(code, int) or code not in (100, 13):
        return False
    text = str(err).lower()
    return "photo" in text or "attach" in text


def _describe_error(e) -> str:
    import requests
    body = ""
    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        body = f" | body={e.response.text[:500]}"
    return f"{type(e).__name__}: {e}{body}"


def _acquire_inflight(key: str):
    with _lock:
        ev = _inflight.get(key)
        if ev is None:
            ev = threading.Event()
            _inflight[key] = ev
            return ev, True
        return ev, False


def _release_inflight(key: str, ev) -> None:
    with _lock:
        _inflight.pop(key, None)
    ev.set()


def _upload_with_retries(vk, filepath: str, peer_id: int, budget: float, delays: list):
    started = time.monotonic()
    attempts_allowed = len(delays) + 1
    attempt = 0
    last_error = ""
    last_tb = ""
    while attempt < attempts_allowed:
        attempt += 1
        try:
            upload_url = vk.photos.getMessagesUploadServer(peer_id=peer_id)["upload_url"]
            resp = _http_post(upload_url, filepath, (5, 30))
            data = resp.json()
            if not (isinstance(data, dict) and data.get("photo")):
                raise RuntimeError(f"VK upload returned empty photo: {str(data)[:500]}")
            saved = vk.photos.saveMessagesPhoto(photo=data["photo"], server=data["server"], hash=data["hash"])[0]
            return f"photo{saved['owner_id']}_{saved['id']}", None, None
        except Exception as e:
            import traceback
            last_tb = traceback.format_exc()
            last_error = f"attempt {attempt}/{attempts_allowed}: {_describe_error(e)}"
            if attempt >= attempts_allowed or not _retryable_error(e):
                break
            if time.monotonic() - started > budget:
                break
            base = delays[attempt - 1]
            delay = base + random.uniform(0, base * 0.3)
            remaining = budget - (time.monotonic() - started)
            if delay > remaining:
                break
            time.sleep(delay)
    return "", last_error, last_tb


def upload_message_photo(vk, filepath: str, peer_id: int = 0, background: bool = False, log_error=None) -> str:
    if not filepath:
        return ""
    cached = get(filepath)
    if cached:
        return cached
    if not os.path.isfile(filepath):
        return ""
    key = _key(filepath)
    if _negative_active(key):
        return ""
    if background:
        budget, delays = BACKGROUND_BUDGET_SECONDS, BACKGROUND_DELAYS
    else:
        budget, delays = INTERACTIVE_BUDGET_SECONDS, INTERACTIVE_DELAYS
    ev, is_owner = _acquire_inflight(key)
    if not is_owner:
        ev.wait(budget)
        return get(filepath)
    try:
        attachment, error, tb = _upload_with_retries(vk, filepath, peer_id, budget, delays)
        if attachment:
            store(filepath, attachment)
            return attachment
        _negative_put(key)
        msg = f"Image upload failed: {error}"
        print(msg)
        if log_error:
            log_error(msg, tb or "")
        return ""
    finally:
        _release_inflight(key, ev)
