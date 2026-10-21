"""
Password check for destructive actions (overwriting metadata, deleting a trajectory). The password lives only in the
backend's environment (ADMIN_PASSWORD in backend/.env, loaded by app.database); without it these actions are refused.
"""
import hmac
import os
from typing import Optional

from fastapi import HTTPException


def require_admin_password(password: Optional[str]) -> None:
    """403 unless `password` equals ADMIN_PASSWORD (constant-time comparison)."""
    expected = os.getenv("ADMIN_PASSWORD")
    if not expected:
        raise HTTPException(status_code=403, detail="Protected action disabled: ADMIN_PASSWORD is not set on the server")
    if not password or not hmac.compare_digest(password.encode(), expected.encode()):
        raise HTTPException(status_code=403, detail="Wrong password")
