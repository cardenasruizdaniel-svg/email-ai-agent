import os
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Active in-memory session tokens: token -> {user_id, username, role, assigned_stage, expires_at}
ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}

class AuthService:
    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """Hashes password using PBKDF2-HMAC-SHA256 with a unique cryptographic salt."""
        if not salt:
            salt = secrets.token_hex(16)
        pwd_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations=100_000
        ).hex()
        return pwd_hash, salt

    @staticmethod
    def verify_password(password: str, stored_hash: str, salt: str) -> bool:
        """Verifies if input password matches the stored PBKDF2 hash."""
        computed_hash, _ = AuthService.hash_password(password, salt)
        return secrets.compare_digest(computed_hash, stored_hash)

    @staticmethod
    def create_session(user: Any, duration_hours: int = 24) -> str:
        """Creates a session token for the user."""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=duration_hours)
        ACTIVE_SESSIONS[token] = {
            "user_id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "assigned_stage": user.assigned_stage,
            "expires_at": expires_at
        }
        return token

    @staticmethod
    def get_session(token: str) -> Optional[Dict[str, Any]]:
        """Retrieves and validates active session."""
        if not token or token not in ACTIVE_SESSIONS:
            return None
        session = ACTIVE_SESSIONS[token]
        if datetime.utcnow() > session["expires_at"]:
            del ACTIVE_SESSIONS[token]
            return None
        return session

    @staticmethod
    def destroy_session(token: str) -> bool:
        """Logs out user by invalidating the token."""
        if token in ACTIVE_SESSIONS:
            del ACTIVE_SESSIONS[token]
            return True
        return False
