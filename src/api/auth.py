"""Optional Firebase Auth dependency for FastAPI."""

from typing import Optional

from fastapi import Header

from src.utils.firebase_admin import verify_id_token


async def get_current_user(
    authorization: Optional[str] = Header(None),
) -> Optional[dict]:
    """
    Extract and verify Firebase ID token from Authorization header.
    Returns user dict {uid, email} or None for anonymous requests.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        return None
    return verify_id_token(token)
