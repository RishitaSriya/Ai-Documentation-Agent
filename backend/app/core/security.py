"""Security utilities including webhook signature verification and secret masking."""

import hmac
import hashlib
from typing import Optional


def verify_github_signature(payload_body: bytes, secret: str, signature_header: Optional[str]) -> bool:
    """Verify GitHub webhook payload against the secret using HMAC-SHA256."""
    if not signature_header or not secret:
        return False

    prefix = "sha256="
    if not signature_header.startswith(prefix):
        return False

    expected_signature = signature_header[len(prefix):]
    mac = hmac.new(secret.encode("utf-8"), msg=payload_body, digestmod=hashlib.sha256)
    computed_signature = mac.hexdigest()

    return hmac.compare_digest(computed_signature, expected_signature)


def mask_secret(secret: Optional[str], visible_chars: int = 4) -> str:
    """Mask sensitive credentials for safe logging and response display."""
    if not secret:
        return ""
    if len(secret) <= visible_chars:
        return "***"
    return f"{secret[:visible_chars]}...{'*' * 6}"
