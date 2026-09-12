import hmac
import hashlib
import time
import uuid
import socket
import logging
from typing import Dict, Any, Optional

try:
    from app.config import settings
except ImportError:
    from .config import settings

logger = logging.getLogger("washqueue-qr")

def get_lan_ip() -> str:
    """Auto-detect the primary local IP address of this machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't actually send traffic, just queries the OS routing table
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def get_secret_key() -> str:
    """Returns the secret key used for HMAC signing (derived from admin PIN / salt)."""
    base_secret = getattr(settings, "secret_key", None) or settings.admin_pin or "washqueue-secret-salt-2026"
    return hashlib.sha256(base_secret.encode()).hexdigest()

def generate_registration_token(hostel_id: str = "block-b", ttl_seconds: int = 60) -> Dict[str, Any]:
    """
    Generates a cryptographically signed HMAC registration token with a rotation TTL.
    """
    secret = get_secret_key()
    now = int(time.time())
    nonce = uuid.uuid4().hex[:12]
    payload = f"{hostel_id}:{now}:{nonce}"
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()[:24]
    token = f"{hostel_id}.{now}.{nonce}.{signature}"

    return {
        "token": token,
        "hostel_id": hostel_id,
        "created_at": now,
        "expires_at": now + ttl_seconds,
        "ttl_seconds": ttl_seconds
    }

def verify_registration_token(token: str, max_age_seconds: int = 360) -> Dict[str, Any]:
    """
    Validates a registration token signature and ensures it was generated within max_age_seconds.
    Default max_age_seconds is 360 (60s rotation + 5 minute student form-filling grace window).
    """
    if not token or not isinstance(token, str):
        return {"valid": False, "error": "Missing or invalid token format"}

    parts = token.strip().split(".")
    if len(parts) != 4:
        return {"valid": False, "error": "Malformed token structure"}

    hostel_id, ts_str, nonce, signature = parts

    try:
        ts = int(ts_str)
    except ValueError:
        return {"valid": False, "error": "Invalid token timestamp"}

    # Verify signature
    secret = get_secret_key()
    payload = f"{hostel_id}:{ts}:{nonce}"
    expected_sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()[:24]

    if not hmac.compare_digest(signature, expected_sig):
        return {"valid": False, "error": "Invalid token cryptographic signature"}

    # Verify expiration (rotation period + grace period)
    age = time.time() - ts
    if age < -10:
        return {"valid": False, "error": "Token timestamp is in the future"}
    if age > max_age_seconds:
        return {
            "valid": False,
            "error": f"Registration session expired ({int(age)}s old). Please scan the live hostel QR again."
        }

    return {
        "valid": True,
        "hostel_id": hostel_id,
        "age_seconds": int(age),
        "remaining_seconds": max(0, int(max_age_seconds - age))
    }
