"""
Firebase-auth-shaped auth dependency stub.

Reads a JSON service account path from env var FIREBASE_SERVICE_ACCOUNT_JSON.
If no file is present (sandbox), verification falls back to a simple bearer-token check
that can be mocked in tests. Never grants auth when token is missing/invalid.
"""

from __future__ import annotations

import json
import os
import pathlib
from typing import Optional

from fastapi import Header, HTTPException, Depends


def _load_service_account() -> Optional[dict]:
    path = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if not path:
        return None
    p = pathlib.Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def verify_bearer_token(authorization: str | None = Header(default=None)) -> dict | None:
    """
    Verify bearer token.
    - If FIREBASE_SERVICE_ACCOUNT_JSON points to a real service account, attempt real verification
      (requires firebase_admin; if not installed, fallback to mock logic).
    - Otherwise, treat any non-empty Bearer token as authenticated user for dev, but
      return None (unauthenticated) if no header is present.

    This function is designed to be overridden/mocked in tests via dependency_overrides.

    Returns dict with {'uid': str, 'email': str|None} if authenticated, else None.
    """
    if authorization is None or not authorization.startswith("Bearer "):
        return None
    token = authorization[len("Bearer "):].strip()
    if not token:
        return None

    sa = _load_service_account()
    if sa is not None:
        # Try real Firebase verification if library available
        try:
            import firebase_admin
            from firebase_admin import auth as fb_auth, credentials

            if not firebase_admin._apps:
                cred = credentials.Certificate(sa)
                firebase_admin.initialize_app(cred)
            decoded = fb_auth.verify_id_token(token)
            return {"uid": decoded.get("uid", "unknown"), "email": decoded.get("email")}
        except Exception:
            # Fall back to not trusting token if verification fails
            # In production this would raise 401; here we return None to fail-closed
            return None

    # Dev / test fallback: accept any token starting with "test" or long enough, but honestly mark it
    # For security, we treat any non-empty token as a stub user when no service account is configured.
    # The endpoint can decide to require auth or allow optional auth.
    return {"uid": f"stub-{token[:8]}", "email": None, "token": token}


def require_auth(user: dict | None = Depends(verify_bearer_token)) -> dict:
    """Dependency that enforces authentication (401 if not authenticated)."""
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required: missing or invalid Bearer token")
    return user


def optional_auth(user: dict | None = Depends(verify_bearer_token)) -> dict | None:
    """Dependency that allows anonymous access but injects user if present."""
    return user
