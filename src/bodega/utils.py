"""Utility functions."""

import uuid
import subprocess
import re
import hashlib
from typing import Optional
from datetime import datetime, UTC, timedelta
from pathlib import Path

from bodega.errors import TicketNotFoundError, AmbiguousIDError, BodegaError


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


id_pattern = re.compile(r'^[a-z][a-z0-9]*-[a-z0-9\.]+$')


def is_valid_id(id_str: str) -> bool:
    """
    Check if string is a valid ticket ID format.

    Prefix must start with a letter and can contain alphanumeric characters.

    Args:
        id_str: The string to validate

    Returns:
        True if the string matches the pattern ^[a-z][a-z0-9]*-[a-z0-9\\.]+$
    """
    return bool(id_pattern.match(id_str))


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


def parse_duration(duration_str: str) -> timedelta:
    """
    Parse a duration string into a timedelta.

    Supported formats:
    - Nd or Ndays: N days (e.g., 30d, 7days)
    - Nh or Nhours: N hours (e.g., 12h, 24hours)
    - Nm or Nminutes: N minutes (e.g., 30m, 45minutes)

    Args:
        duration_str: Duration string (e.g., "30d", "7days", "12h")

    Returns:
        timedelta representing the duration

    Raises:
        BodegaError: If the duration string is invalid
    """
    pattern = re.compile(r'^(\d+)(d|days|h|hours|m|minutes)$', re.IGNORECASE)
    match = pattern.match(duration_str.strip())

    if not match:
        raise BodegaError(
            f"Invalid duration format: '{duration_str}'. "
            "Expected format: <number><unit> where unit is d/days, h/hours, or m/minutes. "
            "Examples: 30d, 7days, 12h, 24hours"
        )

    value = int(match.group(1))
    unit = match.group(2).lower()

    if unit in ('d', 'days'):
        return timedelta(days=value)
    elif unit in ('h', 'hours'):
        return timedelta(hours=value)
    elif unit in ('m', 'minutes'):
        return timedelta(minutes=value)
    else:
        # Should never reach here due to regex, but just in case
        raise BodegaError(f"Unsupported duration unit: {unit}")


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


def get_git_remote_url(repo_path: Path) -> Optional[str]:
    """
    Get git remote origin URL for a repository.

    Safely retrieves the git remote origin URL from the specified repository
    path. Returns None if the path is not a git repository, has no remote
    configured, or if any errors occur.

    Args:
        repo_path: Path to the repository to check

    Returns:
        The git remote origin URL, or None if not found or on error

    Examples:
        >>> get_git_remote_url(Path("/path/to/repo"))
        'https://github.com/user/repo.git'
        >>> get_git_remote_url(Path("/not/a/repo"))
        None
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        return result.stdout.strip() or None
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return None


def get_project_identifier(path: Path) -> str:
    """
    Generate a unique project identifier for offline mode.

    The identifier is used as the directory name for offline ticket storage in
    ~/.bodega/<identifier>/. The function tries to create a stable identifier
    based on the git remote URL (if available), falling back to the absolute
    path if not in a git repository or if no remote is configured.

    Strategy:
    1. If git remote URL exists: hash it → "git-{first 12 chars of sha256}"
    2. Otherwise: hash absolute path → "path-{first 12 chars of sha256}"

    The identifier is sanitized to be filesystem-safe (lowercase, alphanumeric
    plus dash only).

    Args:
        path: Path to the project directory (typically the repo root or cwd)

    Returns:
        A sanitized identifier safe for use as a directory name
        Format: "git-{hash}" or "path-{hash}" where hash is 12 hex characters

    Examples:
        >>> get_project_identifier(Path("/path/to/git/repo"))
        'git-a1b2c3d4e5f6'
        >>> get_project_identifier(Path("/path/to/project"))
        'path-9f8e7d6c5b4a'
    """
    # Try to get git remote URL
    remote_url = get_git_remote_url(path)

    if remote_url:
        # Hash the git remote URL
        hash_input = remote_url.encode('utf-8')
        hash_hex = hashlib.sha256(hash_input).hexdigest()[:12]
        return f"git-{hash_hex}"
    else:
        # Fallback to hashing the absolute path
        abs_path = path.resolve()
        hash_input = str(abs_path).encode('utf-8')
        hash_hex = hashlib.sha256(hash_input).hexdigest()[:12]
        return f"path-{hash_hex}"


# ============================================================================
# File Path Utilities
# ============================================================================


def find_offline_store(project_path: Path) -> Optional[Path]:
    """
    Find offline ticket store for a project in ~/.bodega/<identifier>/.

    Attempts to locate an offline ticket store by generating a project
    identifier and checking if the corresponding directory exists under
    ~/.bodega/. This is used as a fallback when no local .bodega/ directory
    is found.

    Checks both the auto-generated identifier path and any custom name
    registered in the global offline stores mapping.

    Args:
        project_path: Path to the project directory (typically cwd or repo root)

    Returns:
        Path to .bodega directory in offline store, or None if not found

    Examples:
        >>> find_offline_store(Path("/path/to/project"))
        Path("/home/user/.bodega/git-a1b2c3d4e5f6/.bodega")
        >>> find_offline_store(Path("/nonexistent"))
        None
    """
    try:
        from bodega.config import get_offline_store_mapping

        # Get project identifier
        identifier = get_project_identifier(project_path)

        # First, check if there's a custom name in the mapping
        mapping = get_offline_store_mapping()
        if identifier in mapping:
            # Use the mapped name (could be custom name or same as identifier)
            mapped_name = mapping[identifier]
            offline_store = Path.home() / ".bodega" / mapped_name / ".bodega"
            if offline_store.is_dir():
                return offline_store

        # Fallback: check using the identifier directly
        offline_store = Path.home() / ".bodega" / identifier / ".bodega"
        if offline_store.is_dir():
            return offline_store

        return None
    except Exception:
        # Return None on any errors (e.g., permission issues, path problems)
        return None


def find_bodega_dir(start: Optional[Path] = None) -> Optional[Path]:
    """
    Find .bodega directory by searching up from start dir, with offline fallback.

    Searches for a local .bodega directory by walking up the directory tree
    from the start directory (similar to how git finds .git). If no local
    directory is found, falls back to checking for an offline store in
    ~/.bodega/<identifier>/.

    Precedence:
    1. Local .bodega/ directory (searched upwards from start, excluding ~/.bodega itself)
    2. Offline store at ~/.bodega/<identifier>/.bodega/
    3. None if neither exists

    Args:
        start: The directory to start searching from (default: current working directory)

    Returns:
        The path to the .bodega directory (local or offline), or None if not found
    """
    start = start or Path.cwd()
    current = start.resolve()
    home_bodega = Path.home() / ".bodega"

    # First, search up for local .bodega directory
    while current != current.parent:
        bodega_dir = current / ".bodega"
        # Skip ~/.bodega itself - it's not a valid ticket store
        # Only ~/.bodega/<identifier>/.bodega is valid for offline mode
        if bodega_dir.is_dir() and bodega_dir != home_bodega:
            return bodega_dir
        current = current.parent

    # Check root
    bodega_dir = current / ".bodega"
    if bodega_dir.is_dir() and bodega_dir != home_bodega:
        return bodega_dir

    # If no local .bodega found, check for offline store
    offline_store = find_offline_store(start)
    if offline_store:
        return offline_store

    return None
