# Task 03: Utility Functions

## Summary
Implement utility functions for ID generation, date handling, and git integration.

## Dependencies
- Task 01: Project Setup

## Requirements

### 1. ID Generation (`src/bodega/utils.py`)

```python
import uuid
from typing import Optional

DEFAULT_PREFIX = "bg"

def generate_id(prefix: str = DEFAULT_PREFIX) -> str:
    """
    Generate a new ticket ID.

    Format: {prefix}-{6 hex chars}
    Example: bg-a1b2c3
    """
    hex_part = uuid.uuid4().hex[:6]
    return f"{prefix}-{hex_part}"

def is_valid_id(id_str: str) -> bool:
    """Check if string is a valid ticket ID format."""
    import re
    return bool(re.match(r'^[a-z]+-[a-f0-9]+$', id_str))
```

### 2. Partial ID Matching

```python
def resolve_id(partial: str, all_ids: list[str]) -> str:
    """
    Resolve a partial ID to a full ID.

    Args:
        partial: Full or partial ticket ID
        all_ids: List of all known ticket IDs

    Returns:
        The matching full ID

    Raises:
        ValueError: If no match or ambiguous match
    """
    # Exact match
    if partial in all_ids:
        return partial

    # Prefix match
    matches = [id for id in all_ids if id.startswith(partial)]

    if len(matches) == 1:
        return matches[0]
    elif len(matches) == 0:
        raise ValueError(f"No ticket found matching '{partial}'")
    else:
        raise ValueError(
            f"Ambiguous ID '{partial}' matches: {', '.join(matches)}"
        )
```

### 3. Date/Time Utilities

```python
from datetime import datetime, timezone

def now_utc() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)

def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M") -> str:
    """Format datetime for display (converts to local time)."""
    local_dt = dt.astimezone()  # Convert to local timezone
    return local_dt.strftime(fmt)

def parse_datetime(s: str) -> datetime:
    """Parse ISO 8601 datetime string."""
    # Handle both with and without timezone
    # Return as UTC datetime
    ...

def format_iso(dt: datetime) -> str:
    """Format datetime as ISO 8601 string."""
    return dt.isoformat()
```

### 4. Git Utilities

```python
import subprocess
from typing import Optional

def get_git_user() -> Optional[str]:
    """Get git user.name, or None if not configured."""
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
    """Find the git repository root, or None if not in a repo."""
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
```

### 5. File Path Utilities

```python
from pathlib import Path

def find_bodega_dir(start: Optional[Path] = None) -> Optional[Path]:
    """
    Find .bodega directory by searching up from start dir.

    Similar to how git finds .git directory.
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
```

## Acceptance Criteria

- [ ] `generate_id()` produces IDs matching pattern `bg-[a-f0-9]{6}`
- [ ] `generate_id("proj")` produces IDs like `proj-a1b2c3`
- [ ] `is_valid_id()` correctly validates ID format
- [ ] `resolve_id()` handles exact, partial, ambiguous, and missing cases
- [ ] Date functions handle timezone conversion correctly
- [ ] `get_git_user()` returns None gracefully when not in git repo
- [ ] `find_bodega_dir()` searches up directory tree correctly

## Test Cases

```python
def test_generate_id():
    id1 = generate_id()
    id2 = generate_id()
    assert id1 != id2
    assert id1.startswith("bg-")
    assert len(id1) == 9  # "bg-" + 6 chars

def test_resolve_id_exact():
    ids = ["bg-abc123", "bg-def456"]
    assert resolve_id("bg-abc123", ids) == "bg-abc123"

def test_resolve_id_partial():
    ids = ["bg-abc123", "bg-def456"]
    assert resolve_id("bg-abc", ids) == "bg-abc123"
    assert resolve_id("abc", ids) == "bg-abc123"

def test_resolve_id_ambiguous():
    ids = ["bg-abc123", "bg-abc456"]
    with pytest.raises(ValueError, match="Ambiguous"):
        resolve_id("bg-abc", ids)

def test_find_bodega_dir(tmp_path):
    bodega = tmp_path / ".bodega"
    bodega.mkdir()
    subdir = tmp_path / "src" / "module"
    subdir.mkdir(parents=True)

    found = find_bodega_dir(subdir)
    assert found == bodega
```
