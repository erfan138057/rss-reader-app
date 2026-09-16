"""ai_pro.py — app-side client for Pro AI features.

The worker URL is NOT hardcoded here. It is read from the user's settings
("pro_worker_url") at runtime, which keeps the source tree free of any
endpoint or key. Free users never call this module.
"""
import httpx
import json

def _worker_url(settings: dict) -> str:
    """Worker address comes from user settings, not from code."""
    return (settings.get("pro_worker_url") or "").rstrip("/")

def ask(settings: dict, action: str, text: str, **extra) -> str:
    """Call the Pro worker. Raises RuntimeError if Pro is not available."""
    import license
    if not license.pro_actions_allowed(settings).get(action, False):
        raise RuntimeError("Pro license required")
    url = _worker_url(settings)
    if not url:
        raise RuntimeError("Pro worker not configured")
    payload = {"token": settings.get("pro_key", ""), "action": action, "text": text, **extra}
    r = httpx.post(url + "/ai", json=payload, timeout=30,
                   headers={"User-Agent": "RSSReaderPro/1.1.0"})
    data = r.json()
    if r.status_code != 200:
        raise RuntimeError(data.get("error") or f"worker error {r.status_code}")
    return data.get("result", "")

def summarize(settings: dict, text: str) -> str:
    return ask(settings, "summary", text)

def translate(settings: dict, text: str, to: str = "fa") -> str:
    return ask(settings, "translate", text, to=to)

def categorize(settings: dict, text: str) -> str:
    return ask(settings, "categorize", text)
