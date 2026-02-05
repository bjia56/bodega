import pytest
import subprocess
from datetime import datetime, UTC
from pathlib import Path
from bodega.utils import (
    generate_id,
    is_valid_id,
    resolve_id,
    now_utc,
    format_datetime,
    parse_datetime,
    format_iso,
    get_git_user,
    find_repo_root,
    find_bodega_dir,
    get_git_remote_url,
    get_project_identifier,
    find_offline_store,
)
from bodega.errors import TicketNotFoundError, AmbiguousIDError


# ============================================================================
# ID Generation and Validation Tests
# ============================================================================


def test_generate_id():
    """Test that generate_id produces unique IDs with correct format."""
    id1 = generate_id()
    id2 = generate_id()

    # IDs should be unique
    assert id1 != id2

    # Should start with default prefix
    assert id1.startswith("bg-")
    assert id2.startswith("bg-")

    # Length should be "bg-" (3 chars) + 6 hex chars = 9
    assert len(id1) == 9
    assert len(id2) == 9

    # Should match valid ID pattern
    assert is_valid_id(id1)
    assert is_valid_id(id2)


def test_generate_id_custom_prefix():
    """Test generating IDs with custom prefix."""
    id1 = generate_id("proj")
    id2 = generate_id("feature")

    assert id1.startswith("proj-")
    assert id2.startswith("feature-")
    assert len(id1) == 11  # "proj-" + 6 chars
    assert len(id2) == 14  # "feature-" + 6 chars


def test_is_valid_id():
    """Test ID validation."""
    # Valid IDs
    assert is_valid_id("bg-abc123")
    assert is_valid_id("bg-abcdef")
    assert is_valid_id("bg-000000")
    assert is_valid_id("feature-xyz123")
    assert is_valid_id("proj-def456")
    assert is_valid_id("f-abc123")  # single letter prefix
    assert is_valid_id("p1-abc123")  # prefix with number after letter
    assert is_valid_id("proj2-def456")  # prefix with alphanumeric

    # Invalid IDs
    assert not is_valid_id("BG-abc123")  # uppercase prefix
    assert not is_valid_id("bg-ABC123")  # uppercase hex
    assert not is_valid_id("bg_abc123")  # underscore
    assert not is_valid_id("abc123")  # no prefix
    assert not is_valid_id("bg-")  # no hex part
    assert not is_valid_id("")  # empty string
    assert not is_valid_id("1bg-abc123")  # prefix starts with number
    assert not is_valid_id("2-abc123")  # prefix is only a number
    assert not is_valid_id("-abc123")  # no prefix


# ============================================================================
# Partial ID Matching Tests
# ============================================================================


def test_resolve_id_exact():
    """Test exact ID match."""
    ids = ["bg-abc123", "bg-def456"]
    assert resolve_id("bg-abc123", ids) == "bg-abc123"
    assert resolve_id("bg-def456", ids) == "bg-def456"


def test_resolve_id_partial():
    """Test partial ID matching."""
    ids = ["bg-abc123", "bg-def456"]

    # Prefix matches
    assert resolve_id("bg-abc", ids) == "bg-abc123"
    assert resolve_id("bg-def", ids) == "bg-def456"

    # Even shorter prefixes
    assert resolve_id("bg-a", ids) == "bg-abc123"
    assert resolve_id("bg-d", ids) == "bg-def456"


def test_resolve_id_ambiguous():
    """Test that ambiguous partial IDs raise AmbiguousIDError."""
    ids = ["bg-abc123", "bg-abc456"]

    with pytest.raises(AmbiguousIDError, match="Ambiguous"):
        resolve_id("bg-abc", ids)

    with pytest.raises(AmbiguousIDError, match="Ambiguous"):
        resolve_id("bg-a", ids)


def test_resolve_id_not_found():
    """Test that non-matching IDs raise TicketNotFoundError."""
    ids = ["bg-abc123", "bg-def456"]

    with pytest.raises(TicketNotFoundError, match="No ticket found"):
        resolve_id("bg-xyz", ids)

    with pytest.raises(TicketNotFoundError, match="No ticket found"):
        resolve_id("proj-abc", ids)


def test_resolve_id_empty_list():
    """Test resolving ID with empty list."""
    with pytest.raises(TicketNotFoundError, match="No ticket found"):
        resolve_id("bg-abc123", [])


# ============================================================================
# Date/Time Utilities Tests
# ============================================================================


def test_now_utc():
    """Test that now_utc returns a UTC datetime."""
    dt = now_utc()

    assert dt.tzinfo == UTC
    assert isinstance(dt, datetime)

    # Should be close to current time (within 1 second)
    diff = datetime.now(UTC) - dt
    assert abs(diff.total_seconds()) < 1


def test_format_datetime():
    """Test datetime formatting."""
    dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)

    # Default format
    formatted = format_datetime(dt)
    assert "2024-01-15" in formatted
    assert ":" in formatted  # Has time component

    # Custom format
    formatted_custom = format_datetime(dt, "%Y/%m/%d")
    assert formatted_custom == "2024/01/15"


def test_format_datetime_with_timezone():
    """Test that format_datetime converts to local timezone."""
    # Create a UTC datetime
    dt_utc = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

    # Format it - it should convert to local time
    formatted = format_datetime(dt_utc)

    # We can't assert the exact value since it depends on the system timezone,
    # but we can verify it's a valid formatted string
    assert isinstance(formatted, str)
    assert len(formatted) > 0


def test_parse_datetime_with_timezone():
    """Test parsing ISO datetime string with timezone."""
    # With timezone
    s = "2024-01-15T12:00:00+00:00"
    dt = parse_datetime(s)

    assert dt.year == 2024
    assert dt.month == 1
    assert dt.day == 15
    assert dt.hour == 12
    assert dt.minute == 0
    assert dt.second == 0
    assert dt.tzinfo == UTC


def test_parse_datetime_naive():
    """Test parsing naive datetime string (assumes UTC)."""
    s = "2024-01-15T12:00:00"
    dt = parse_datetime(s)

    assert dt.year == 2024
    assert dt.month == 1
    assert dt.day == 15
    assert dt.hour == 12
    assert dt.tzinfo == UTC


def test_parse_datetime_different_timezone():
    """Test parsing datetime with non-UTC timezone."""
    # Create a datetime in EST (UTC-5)
    s = "2024-01-15T12:00:00-05:00"
    dt = parse_datetime(s)

    # Should be converted to UTC
    assert dt.tzinfo == UTC
    # 12:00 EST = 17:00 UTC
    assert dt.hour == 17


def test_format_iso():
    """Test ISO format output."""
    dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
    iso_str = format_iso(dt)

    assert iso_str == "2024-01-15T12:00:00+00:00"


def test_datetime_roundtrip():
    """Test that datetime can be formatted and parsed back."""
    original = datetime(2024, 1, 15, 12, 30, 45, tzinfo=UTC)

    # Format to ISO
    iso_str = format_iso(original)

    # Parse back
    parsed = parse_datetime(iso_str)

    assert parsed == original


# ============================================================================
# Git Utilities Tests
# ============================================================================


def test_get_git_user():
    """Test getting git user name."""
    user = get_git_user()

    # Could be None if not in a git repo or not configured
    # Could be a string if configured
    assert user is None or isinstance(user, str)

    # If it's a string, it should not be empty
    if user is not None:
        assert len(user) > 0


def test_find_repo_root():
    """Test finding git repository root."""
    root = find_repo_root()

    # Could be None if not in a git repo
    # Could be a string path if in a repo
    assert root is None or isinstance(root, str)

    # If it's a string, it should be an absolute path
    if root is not None:
        assert len(root) > 0
        # Should be an absolute path
        assert Path(root).is_absolute()


# ============================================================================
# File Path Utilities Tests
# ============================================================================


def test_find_bodega_dir(tmp_path):
    """Test finding .bodega directory."""
    # Create .bodega directory
    bodega = tmp_path / ".bodega"
    bodega.mkdir()

    # Create nested subdirectories
    subdir = tmp_path / "src" / "module"
    subdir.mkdir(parents=True)

    # Should find .bodega from subdirectory
    found = find_bodega_dir(subdir)
    assert found == bodega


def test_find_bodega_dir_not_found(tmp_path):
    """Test when .bodega directory doesn't exist."""
    # Create a directory without .bodega
    subdir = tmp_path / "src"
    subdir.mkdir()

    # Should return None
    found = find_bodega_dir(subdir)
    assert found is None


def test_find_bodega_dir_current_dir(tmp_path):
    """Test finding .bodega in current directory."""
    bodega = tmp_path / ".bodega"
    bodega.mkdir()

    # Search from the directory containing .bodega
    found = find_bodega_dir(tmp_path)
    assert found == bodega


def test_find_bodega_dir_deeply_nested(tmp_path):
    """Test finding .bodega from deeply nested subdirectory."""
    # Create .bodega at root
    bodega = tmp_path / ".bodega"
    bodega.mkdir()

    # Create deeply nested structure
    deep = tmp_path / "a" / "b" / "c" / "d" / "e"
    deep.mkdir(parents=True)

    # Should still find it
    found = find_bodega_dir(deep)
    assert found == bodega


def test_find_bodega_dir_default_start():
    """Test finding .bodega with default start directory."""
    # This will search from current working directory
    # Result depends on whether we're in a bodega project
    found = find_bodega_dir()

    # Should either find it or return None
    assert found is None or isinstance(found, Path)


# ============================================================================
# Project Identifier Tests
# ============================================================================


def test_get_git_remote_url_with_git(tmp_path):
    """Test getting git remote URL from a git repository with remote."""
    # Create a git repo with remote
    repo = tmp_path / "repo"
    repo.mkdir()

    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/user/repo.git"],
        cwd=repo,
        check=True,
        capture_output=True
    )

    url = get_git_remote_url(repo)
    assert url == "https://github.com/user/repo.git"


def test_get_git_remote_url_no_remote(tmp_path):
    """Test getting git remote URL from a git repository without remote."""
    # Create a git repo without remote
    repo = tmp_path / "repo"
    repo.mkdir()

    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)

    url = get_git_remote_url(repo)
    assert url is None


def test_get_git_remote_url_not_git_repo(tmp_path):
    """Test getting git remote URL from a non-git directory."""
    # Create a regular directory
    repo = tmp_path / "not-a-repo"
    repo.mkdir()

    url = get_git_remote_url(repo)
    assert url is None


def test_get_git_remote_url_nonexistent_path(tmp_path):
    """Test getting git remote URL from a nonexistent path."""
    nonexistent = tmp_path / "does-not-exist"

    url = get_git_remote_url(nonexistent)
    assert url is None


def test_get_project_identifier_with_git_remote(tmp_path):
    """Test project identifier generation for git repo with remote."""
    # Create a git repo with remote
    repo = tmp_path / "repo"
    repo.mkdir()

    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/user/myproject.git"],
        cwd=repo,
        check=True,
        capture_output=True
    )

    identifier = get_project_identifier(repo)

    # Should start with "git-"
    assert identifier.startswith("git-")
    # Should be "git-" + 12 hex chars
    assert len(identifier) == 16  # "git-" (4) + 12 hex chars
    # Should be lowercase alphanumeric + dash
    assert identifier.replace("-", "").replace("git", "").isalnum()


def test_get_project_identifier_without_git(tmp_path):
    """Test project identifier generation for non-git directory."""
    # Create a regular directory
    repo = tmp_path / "project"
    repo.mkdir()

    identifier = get_project_identifier(repo)

    # Should start with "path-"
    assert identifier.startswith("path-")
    # Should be "path-" + 12 hex chars
    assert len(identifier) == 17  # "path-" (5) + 12 hex chars
    # Should be lowercase alphanumeric + dash
    assert identifier.replace("-", "").replace("path", "").isalnum()


def test_get_project_identifier_stability_with_git(tmp_path):
    """Test that project identifier is stable for same git remote."""
    # Create a git repo with remote
    repo = tmp_path / "repo"
    repo.mkdir()

    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/user/stable.git"],
        cwd=repo,
        check=True,
        capture_output=True
    )

    # Should get same identifier multiple times
    id1 = get_project_identifier(repo)
    id2 = get_project_identifier(repo)
    id3 = get_project_identifier(repo)

    assert id1 == id2 == id3


def test_get_project_identifier_stability_without_git(tmp_path):
    """Test that project identifier is stable for same path."""
    # Create a regular directory
    repo = tmp_path / "project"
    repo.mkdir()

    # Should get same identifier multiple times
    id1 = get_project_identifier(repo)
    id2 = get_project_identifier(repo)
    id3 = get_project_identifier(repo)

    assert id1 == id2 == id3


def test_get_project_identifier_different_for_different_repos(tmp_path):
    """Test that different projects get different identifiers."""
    # Create two git repos with different remotes
    repo1 = tmp_path / "repo1"
    repo1.mkdir()
    subprocess.run(["git", "init"], cwd=repo1, check=True, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/user/project1.git"],
        cwd=repo1,
        check=True,
        capture_output=True
    )

    repo2 = tmp_path / "repo2"
    repo2.mkdir()
    subprocess.run(["git", "init"], cwd=repo2, check=True, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/user/project2.git"],
        cwd=repo2,
        check=True,
        capture_output=True
    )

    id1 = get_project_identifier(repo1)
    id2 = get_project_identifier(repo2)

    # Different repos should have different identifiers
    assert id1 != id2
    # Both should start with "git-"
    assert id1.startswith("git-")
    assert id2.startswith("git-")


def test_get_project_identifier_different_paths(tmp_path):
    """Test that different paths get different identifiers."""
    # Create two different directories
    dir1 = tmp_path / "project1"
    dir1.mkdir()

    dir2 = tmp_path / "project2"
    dir2.mkdir()

    id1 = get_project_identifier(dir1)
    id2 = get_project_identifier(dir2)

    # Different paths should have different identifiers
    assert id1 != id2
    # Both should start with "path-"
    assert id1.startswith("path-")
    assert id2.startswith("path-")


# ============================================================================
# Offline Store Discovery Tests
# ============================================================================


def test_find_offline_store_exists(tmp_path, monkeypatch):
    """Test finding an existing offline store."""
    # Create a project directory
    project = tmp_path / "project"
    project.mkdir()

    # Mock home directory
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr("bodega.utils.Path.home", lambda: home)

    # Get the identifier and create offline store
    identifier = get_project_identifier(project)
    offline_store = home / ".bodega" / identifier / ".bodega"
    offline_store.mkdir(parents=True)

    # Should find the offline store
    found = find_offline_store(project)
    assert found == offline_store


def test_find_offline_store_not_exists(tmp_path, monkeypatch):
    """Test when offline store doesn't exist."""
    # Create a project directory
    project = tmp_path / "project"
    project.mkdir()

    # Mock home directory
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr("bodega.utils.Path.home", lambda: home)

    # Don't create offline store

    # Should return None
    found = find_offline_store(project)
    assert found is None


def test_find_offline_store_with_git_repo(tmp_path, monkeypatch):
    """Test finding offline store for git repo."""
    # Create a git repo with remote
    project = tmp_path / "project"
    project.mkdir()

    subprocess.run(["git", "init"], cwd=project, check=True, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", "https://github.com/user/project.git"],
        cwd=project,
        check=True,
        capture_output=True
    )

    # Mock home directory
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr("bodega.utils.Path.home", lambda: home)

    # Create offline store based on git identifier
    identifier = get_project_identifier(project)
    offline_store = home / ".bodega" / identifier / ".bodega"
    offline_store.mkdir(parents=True)

    # Should find the offline store
    found = find_offline_store(project)
    assert found == offline_store
    # Should be based on git remote, not path
    assert identifier.startswith("git-")


def test_find_bodega_dir_with_offline_fallback(tmp_path, monkeypatch):
    """Test find_bodega_dir falls back to offline store when no local .bodega."""
    # Create a project directory without local .bodega
    project = tmp_path / "project"
    project.mkdir()

    # Mock home directory
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr("bodega.utils.Path.home", lambda: home)

    # Create offline store
    identifier = get_project_identifier(project)
    offline_store = home / ".bodega" / identifier / ".bodega"
    offline_store.mkdir(parents=True)

    # Should find offline store as fallback
    found = find_bodega_dir(project)
    assert found == offline_store


def test_find_bodega_dir_local_takes_precedence(tmp_path, monkeypatch):
    """Test that local .bodega takes precedence over offline store."""
    # Create a project directory with local .bodega
    project = tmp_path / "project"
    project.mkdir()
    local_bodega = project / ".bodega"
    local_bodega.mkdir()

    # Mock home directory
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr("bodega.utils.Path.home", lambda: home)

    # Create offline store too
    identifier = get_project_identifier(project)
    offline_store = home / ".bodega" / identifier / ".bodega"
    offline_store.mkdir(parents=True)

    # Should find local .bodega, not offline store
    found = find_bodega_dir(project)
    assert found == local_bodega
    assert found != offline_store


def test_find_bodega_dir_returns_none_when_neither_exists(tmp_path, monkeypatch):
    """Test that find_bodega_dir returns None when neither local nor offline exists."""
    # Create a project directory without any .bodega
    project = tmp_path / "project"
    project.mkdir()

    # Mock home directory
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr("bodega.utils.Path.home", lambda: home)

    # Don't create any .bodega directories

    # Should return None
    found = find_bodega_dir(project)
    assert found is None


def test_find_bodega_dir_searches_upward_before_offline(tmp_path, monkeypatch):
    """Test that find_bodega_dir searches upward before checking offline."""
    # Create parent directory with .bodega
    parent = tmp_path / "workspace"
    parent.mkdir()
    parent_bodega = parent / ".bodega"
    parent_bodega.mkdir()

    # Create nested project directory
    project = parent / "myproject" / "src"
    project.mkdir(parents=True)

    # Mock home directory
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr("bodega.utils.Path.home", lambda: home)

    # Create offline store for the nested path
    identifier = get_project_identifier(project)
    offline_store = home / ".bodega" / identifier / ".bodega"
    offline_store.mkdir(parents=True)

    # Should find parent's .bodega, not offline store
    found = find_bodega_dir(project)
    assert found == parent_bodega
    assert found != offline_store


def test_find_bodega_dir_skips_home_bodega_itself(tmp_path, monkeypatch):
    """Test that ~/.bodega itself is skipped during upward search."""
    # Mock home directory
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr("bodega.utils.Path.home", lambda: home)

    # Create ~/.bodega directory (but not a valid store inside it)
    home_bodega = home / ".bodega"
    home_bodega.mkdir()

    # Create a project directory inside ~/.bodega
    project = home_bodega / "some-identifier"
    project.mkdir()

    # Create the actual offline store
    offline_store = project / ".bodega"
    offline_store.mkdir()

    # When searching from inside the offline store, should find the offline store
    # not skip to ~/.bodega itself
    found = find_bodega_dir(project)
    assert found == offline_store
    assert found != home_bodega


def test_find_bodega_dir_from_inside_offline_store(tmp_path, monkeypatch):
    """Test find_bodega_dir when called from inside an offline store."""
    # Mock home directory
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr("bodega.utils.Path.home", lambda: home)

    # Create a real project elsewhere to get a proper identifier
    real_project = tmp_path / "workspace" / "myproject"
    real_project.mkdir(parents=True)

    # Create offline store for that project
    identifier = get_project_identifier(real_project)
    offline_store = home / ".bodega" / identifier / ".bodega"
    offline_store.mkdir(parents=True)

    # Call find_bodega_dir from inside the offline store
    # Should find the offline store, not ~/.bodega
    found = find_bodega_dir(offline_store)
    assert found == offline_store
