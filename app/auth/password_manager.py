"""Bcrypt password hashing and verification."""

import bcrypt


def hash_password(password: str) -> str:
    """Hash a password with bcrypt (cost factor 12)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def hash_pin(pin: str) -> str:
    """Hash a 4-digit PIN with bcrypt."""
    return hash_password(pin)


def verify_pin(pin: str, hashed: str) -> bool:
    """Verify a PIN against a bcrypt hash."""
    return verify_password(pin, hashed)
