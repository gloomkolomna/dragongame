import os
import threading

_lock = threading.Lock()
_cache = {}
_reverse = {}


def enabled() -> bool:
    import config
    return getattr(config, "UPLOAD_CACHE_ENABLED", True)


def _key(filepath: str) -> str:
    return os.path.normpath(filepath)


def get(filepath: str) -> str:
    if not enabled():
        return ""
    try:
        st = os.stat(filepath)
    except OSError:
        return ""
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
    return key


def _forget(key: str) -> None:
    with _lock:
        entry = _cache.pop(key, None)
        if entry:
            _reverse.pop(entry[2], None)


def clear() -> None:
    with _lock:
        _cache.clear()
        _reverse.clear()
