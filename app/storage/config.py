"""Storage backend selection based on configuration."""

from app.config import settings


def get_storage_backend() -> str:
    """Return 'spaces' if DO Spaces is configured, else 'local'."""
    if settings.use_spaces:
        return "spaces"
    return "local"
