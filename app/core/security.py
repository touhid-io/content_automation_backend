from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


def _build_fernet() -> Fernet:
    settings = get_settings()
    derived_key: bytes = hashlib.sha256(
        settings.encryption_secret_key.encode("utf-8")
    ).digest()
    fernet_key: bytes = base64.urlsafe_b64encode(derived_key)
    return Fernet(fernet_key)


def encrypt_token(value: str | None) -> str | None:
    if not value:
        return None
    fernet = _build_fernet()
    return fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_token(value: str | None) -> str | None:
    if not value:
        return None
    fernet = _build_fernet()
    try:
        return fernet.decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Invalid encrypted token or mismatched ENCRYPTION_SECRET_KEY.") from exc
