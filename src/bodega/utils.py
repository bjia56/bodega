"""Utility functions."""

import uuid
import subprocess
import re
from typing import Optional
from datetime import datetime, timezone, UTC
from pathlib import Path

from bodega.errors import TicketNotFoundError, AmbiguousIDError


# ============================================================================
# ID Generation and Validation
# ============================================================================

DEFAULT_PREFIX = "bg"


def generate_id(prefix: str = DEFAULT_PREFIX) -> str:
    """
    Generate a new ticket ID.

    Format: {prefix}-{6 hex chars}
    Example: bg-a1b2c3

    Args:
        prefix: The prefix for the ID (default: "bg")

    Returns:
        A new ticket ID in the format {prefix}-{6 hex chars}
    """
    hex_part = uuid.uuid4().hex[:6]
    return f"{prefix}-{hex_part}"


def is_valid_id(id_str: str) -> bool:
    """
    Check if string is a valid ticket ID format.

    Args:
        id_str: The string to validate

    Returns:
        True if the string matches the pattern ^[a-z]+-[a-f0-9]+$
    """
    return bool(re.match(r'^[a-z]+-[a-f0-9]+$', id_str))


def resolve_id(partial: str, all_ids: list[str]) -> str:
    """
    Resolve a partial ID to a full ID.

    Args:
        partial: Full or partial ticket ID
        all_ids: List of all known ticket IDs

    Returns:
        The matching full ID

    Raises:
        TicketNotFoundError: If no match found
        AmbiguousIDError: If multiple matches found
    """
    # Exact match
    if partial in all_ids:
        return partial

    # Prefix match
    matches = [id for id in all_ids if id.startswith(partial)]

    if len(matches) == 1:
        return matches[0]
    elif len(matches) == 0:
        raise TicketNotFoundError(f"No ticket found matching '{partial}'")
    else:
        raise AmbiguousIDError(
            f"Ambiguous ID '{partial}' matches: {', '.join(matches)}"
        )


# ============================================================================
# Date/Time Utilities
# ============================================================================


def now_utc() -> datetime:
    """
    Return current UTC datetime.

    Returns:
        Current datetime in UTC timezone
    """
    return datetime.now(UTC)


def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """
    Format datetime for display (converts to local time).

    Args:
        dt: The datetime to format
        fmt: The format string (default: "%Y-%m-%d %H:%M")

    Returns:
        Formatted datetime string in local timezone
    """
    local_dt = dt.astimezone()  # Convert to local timezone
    return local_dt.strftime(fmt)


def parse_datetime(s: str) -> datetime:
    """
    Parse ISO 8601 datetime string.

    Handles both timezone-aware and naive datetime strings.
    Returns as UTC datetime.

    Args:
        s: ISO 8601 datetime string

    Returns:
        datetime object in UTC timezone
    """
    dt = datetime.fromisoformat(s)

    # If naive, assume UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    else:
        # Convert to UTC if it has a different timezone
        dt = dt.astimezone(UTC)

    return dt


def format_iso(dt: datetime) -> str:
    """
    Format datetime as ISO 8601 string.

    Args:
        dt: The datetime to format

    Returns:
        ISO 8601 formatted string
    """
    return dt.isoformat()


# ============================================================================
# Git Utilities
# ============================================================================


def get_git_user() -> Optional[str]:
    """
    Get git user.name, or None if not configured.

    Returns:
        The git user name, or None if not configured or not in a git repo
    """
    try:
        result = subprocess.run(
            ["git", "config", "user.name"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip() or None
    except subprocess.CalledProcessError:
        return None


def find_repo_root() -> Optional[str]:
    """
    Find the git repository root, or None if not in a repo.

    Returns:
        The absolute path to the git repository root, or None if not in a git repo
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


# ============================================================================
# File Path Utilities
# ============================================================================


def find_bodega_dir(start: Optional[Path] = None) -> Optional[Path]:
    """
    Find .bodega directory by searching up from start dir.

    Similar to how git finds .git directory.

    Args:
        start: The directory to start searching from (default: current working directory)

    Returns:
        The path to the .bodega directory, or None if not found
    """
    start = start or Path.cwd()
    current = start.resolve()

    while current != current.parent:
        bodega_dir = current / ".bodega"
        if bodega_dir.is_dir():
            return bodega_dir
        current = current.parent

    # Check root
    bodega_dir = current / ".bodega"
    if bodega_dir.is_dir():
        return bodega_dir

    return None
