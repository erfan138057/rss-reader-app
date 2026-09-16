"""license.py — Pro licensing for RSS Reader Pro.

Design: no API endpoint, no plaintext key visible in the codebase.
- Buyer sends a Pro key (hex string) into settings.
- Keys are HMAC-SHA256 signed by the owner with a secret kept OUTSIDE the repo
  (owner's offline secret). This module only verifies.
- Optional online re-validation against a Cloudflare Worker is available for
  Pro builds, but the worker address is read from settings, never hardcoded.
"""
import hashlib
import hmac
import json
import base64
import os
import time

# Public verification material only. The signing SECRET must NEVER be shipped
# or committed — it lives on the owner's machine / a secure env var.
_SALT = b"RSSReaderPro.v1"

def _sign(payload: str, secret: str) -> str:
    return hmac.new(secret.encode(), _SALT + payload.encode(), hashlib.sha256).hexdigest()

def key_is_valid_format(key: str) -> bool:
    """A Pro key is: base64url(json{...})::hmac64hex"""
    if "::" not in key:
        return False
    payload, sig = key.split("::", 1)
    if len(sig) != 64:
        return False
    try:
        json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        return True
    except Exception:
        return False

def verify_key(key: str, secret: str | None = None) -> bool:
    """Offline check. `secret` is the owner's signing secret (env var in Pro builds)."""
    if not key_is_valid_format(key):
        return False
    payload, sig = key.split("::", 1)
    if secret is None:
        secret = os.environ.get("RSSPRO_SIGN_SECRET", "")
    if not secret:
        return False
    return hmac.compare_digest(sig, _sign(payload, secret))

def pro_enabled(settings: dict) -> bool:
    """Pro features are on when a valid license key exists in settings."""
    key = (settings.get("pro_key") or "").strip()
    if not key:
        return False
    return verify_key(key)

def pro_actions_allowed(settings: dict) -> dict:
    """Map of Pro feature flags. All False for free users."""
    on = pro_enabled(settings)
    return {
        "ai_summary": on,
        "ai_translate": on,
        "ai_categorize": on,
    }
