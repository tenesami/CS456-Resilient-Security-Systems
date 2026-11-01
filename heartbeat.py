import hashlib
import hmac
import time
from typing import Optional


SECRET_ENV = "SERVICE_HEARTBEAT_SECRET"


def create_heartbeat(secret: str, sequence: int) -> bytes:
    """Sign a versioned heartbeat without transmitting the shared secret."""
    payload = f"HEARTBEAT:1:{sequence}:{int(time.time())}".encode("ascii")
    signature = hmac.new(
        secret.encode("ascii"), payload, hashlib.sha256
    ).hexdigest()
    return payload + b":" + signature.encode("ascii")


def verify_heartbeat(
    data: bytes, secret: str, last_sequence: int, max_age: float
) -> Optional[int]:
    """Return the sequence only for an authentic, fresh, unreplayed packet."""
    try:
        message, version, sequence_text, sent_at_text, signature = (
            data.decode("ascii").split(":")
        )
        if (
            message != "HEARTBEAT"
            or version != "1"
            or not sequence_text.isdecimal()
            or not sent_at_text.isdecimal()
        ):
            return None
        sequence = int(sequence_text)
        sent_at = int(sent_at_text)
    except (UnicodeDecodeError, ValueError):
        return None

    payload = data.rsplit(b":", 1)[0]
    expected = hmac.new(
        secret.encode("ascii"), payload, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    age = time.time() - sent_at
    if sequence <= last_sequence or not 0 <= age <= max_age:
        return None
    return sequence
