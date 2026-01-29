"""Tests for git worktree functionality."""

import pytest
import subprocess
from pathlib import Path

from bodega.worktree import (
    init_worktree,
    ensure_worktree,
    auto_commit_ticket,
    has_uncommitted_changes,
    get_commits_ahead,
    get_sync_status,
    sync_branches,
    cleanup_worktree,
)
from bodega.storage import init_repository
from bodega.errors import StorageError


# ============================================================================
# Worktree Initialization Tests
# ============================================================================

def test_init_worktree_creates_structure(temp_git_repo):
    """Test that init_worktree creates expected directory structure."""
    bodega_dir = temp_git_repo / ".bodega"
    init_repository(temp_git_repo)

    worktree_bodega_dir = init_worktree(temp_git_repo, bodega_dir, "bodega")

    # Check directory structure
    assert (bodega_dir / ".gitignore").exists()
    assert (bodega_dir / "worktree").exists()
    assert (bodega_dir / "worktree" / ".bodega").exists()
    assert worktree_bodega_dir == bodega_dir / "worktree" / ".bodega"

    # Check .gitignore content
    gitignore_content = (bodega_dir / ".gitignore").read_text()
    assert "worktree/" in gitignore_content


def test_init_worktree_creates_branch(temp_git_repo):
    """Test that init_worktree creates bodega branch."""
    bodega_dir = temp_git_repo / ".bodega"
    init_repository(temp_git_repo)

    init_worktree(temp_git_repo, bodega_dir, "bodega")

    # Check that bodega branch exists
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "bodega"],
        cwd=temp_git_repo,
        capture_output=True
    )
    assert result.returncode == 0


def test_init_worktree_copies_config(temp_git_repo):
    """Test that init_worktree copies config to worktree."""
    bodega_dir = temp_git_repo / ".bodega"
    init_repository(temp_git_repo)

    # Check config exists in main .bodega
    assert (bodega_dir / "config.yaml").exists()

    worktree_bodega_dir = init_worktree(temp_git_repo, bodega_dir, "bodega")

    # Check config was copied to worktree
    assert (worktree_bodega_dir / "config.yaml").exists()

    # Content should match
    main_config = (bodega_dir / "config.yaml").read_text()
    worktree_config = (worktree_bodega_dir / "config.yaml").read_text()
    assert main_config == worktree_config


def test_init_worktree_creates_initial_commit(temp_git_repo):
    """Test that init_worktree creates an initial commit on bodega branch."""
    bodega_dir = temp_git_repo / ".bodega"
    init_repository(temp_git_repo)

    init_worktree(temp_git_repo, bodega_dir, "bodega")

    # Check for commit on bodega branch
    result = subprocess.run(
        ["git", "log", "--oneline", "bodega"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True
    )
    assert "Initialize bodega ticket tracking" in result.stdout


# ============================================================================
# Ensure Worktree Tests
# ============================================================================

def test_ensure_worktree_creates_if_missing(temp_git_repo):
    """Test that ensure_worktree creates worktree if it doesn't exist."""
    bodega_dir = temp_git_repo / ".bodega"
    init_repository(temp_git_repo)

    # Don't create worktree initially
    # ensure_worktree should create it
    worktree_bodega_dir = ensure_worktree(bodega_dir, "bodega")

    assert worktree_bodega_dir.exists()
    assert (bodega_dir / "worktree").exists()


def test_ensure_worktree_returns_existing(temp_git_repo):
    """Test that ensure_worktree returns existing worktree path."""
    bodega_dir = temp_git_repo / ".bodega"
    init_repository(temp_git_repo)

    # Create worktree
    worktree_dir1 = init_worktree(temp_git_repo, bodega_dir, "bodega")

    # Call ensure_worktree, should return same path
    worktree_dir2 = ensure_worktree(bodega_dir, "bodega")

    assert worktree_dir1 == worktree_dir2


def test_ensure_worktree_creates_bodega_dir_if_missing(temp_git_repo):
    """Test that ensure_worktree creates .bodega dir in worktree if missing."""
    bodega_dir = temp_git_repo / ".bodega"
    init_repository(temp_git_repo)

    # Create worktree
    init_worktree(temp_git_repo, bodega_dir, "bodega")

    # Remove .bodega directory from worktree
    import shutil
    shutil.rmtree(bodega_dir / "worktree" / ".bodega")

    # ensure_worktree should recreate it
    worktree_bodega_dir = ensure_worktree(bodega_dir, "bodega")

    assert worktree_bodega_dir.exists()


# ============================================================================
# Auto-commit Tests
# ============================================================================

def test_auto_commit_create_ticket(temp_git_repo):
    """Test auto-commit when creating a ticket."""
    bodega_dir = temp_git_repo / ".bodega"
    init_repository(temp_git_repo)
    worktree_bodega_dir = init_worktree(temp_git_repo, bodega_dir, "bodega")
    worktree_path = worktree_bodega_dir.parent

    # Create a ticket file
    ticket_file = worktree_bodega_dir / "bg-test123.md"
    ticket_file.write_text("# Test ticket")

    # Auto-commit
    commit_sha = auto_commit_ticket(
        worktree_path,
        ticket_file,
        operation="create",
        ticket_id="bg-test123",
        message="Test ticket title"
    )

    assert commit_sha is not None

    # Check commit message
    result = subprocess.run(
        ["git", "log", "-1", "--pretty=%B"],
        cwd=worktree_path,
        capture_output=True,
        text=True
    )
    assert "Create ticket bg-test123: Test ticket title" in result.stdout


def test_auto_commit_update_ticket(temp_git_repo):
    """Test auto-commit when updating a ticket."""
    bodega_dir = temp_git_repo / ".bodega"
    init_repository(temp_git_repo)
    worktree_bodega_dir = init_worktree(temp_git_repo, bodega_dir, "bodega")
    worktree_path = worktree_bodega_dir.parent

    # Create and commit initial ticket
    ticket_file = worktree_bodega_dir / "bg-test123.md"
    ticket_file.write_text("# Test ticket v1")
    auto_commit_ticket(worktree_path, ticket_file, "create", "bg-test123")

    # Update ticket
    ticket_file.write_text("# Test ticket v2")
    commit_sha = auto_commit_ticket(
        worktree_path,
        ticket_file,
        operation="update",
        ticket_id="bg-test123"
    )

    assert commit_sha is not None

    # Check commit message
    result = subprocess.run(
        ["git", "log", "-1", "--pretty=%B"],
        cwd=worktree_path,
        capture_output=True,
        text=True
    )
    assert "Update ticket bg-test123" in result.stdout


def test_auto_commit_delete_ticket(temp_git_repo):
    """Test auto-commit when deleting a ticket."""
    bodega_dir = temp_git_repo / ".bodega"
    init_repository(temp_git_repo)
    worktree_bodega_dir = init_worktree(temp_git_repo, bodega_dir, "bodega")
    worktree_path = worktree_bodega_dir.parent

    # Create and commit initial ticket
    ticket_file = worktree_bodega_dir / "bg-test123.md"
    ticket_file.write_text("# Test ticket")
    auto_commit_ticket(worktree_path, ticket_file, "create", "bg-test123")

    # Delete ticket
    ticket_file.unlink()
    commit_sha = auto_commit_ticket(
        worktree_path,
        ticket_file,
        operation="delete",
        ticket_id="bg-test123"
    )

    assert commit_sha is not None

    # Check commit message
    result = subprocess.run(
        ["git", "log", "-1", "--pretty=%B"],
        cwd=worktree_path,
        capture_output=True,
        text=True
    )
    assert "Delete ticket bg-test123" in result.stdout


def test_auto_commit_nothing_to_commit(temp_git_repo):
    """Test auto-commit when there are no changes returns None."""
    bodega_dir = temp_git_repo / ".bodega"
    init_repository(temp_git_repo)
    worktree_bodega_dir = init_worktree(temp_git_repo, bodega_dir, "bodega")
    worktree_path = worktree_bodega_dir.parent

    # Create and commit ticket
    ticket_file = worktree_bodega_dir / "bg-test123.md"
    ticket_file.write_text("# Test ticket")
    auto_commit_ticket(worktree_path, ticket_file, "create", "bg-test123")

    # Try to commit again without changes
    commit_sha = auto_commit_ticket(
        worktree_path,
        ticket_file,
        operation="update",
        ticket_id="bg-test123"
    )

    assert commit_sha is None


# ============================================================================
# Status Check Tests
# ============================================================================

def test_has_uncommitted_changes_empty(temp_git_repo):
    """Test has_uncommitted_changes returns False for clean repo."""
    bodega_dir = temp_git_repo / ".bodega"
    init_repository(temp_git_repo)
    init_worktree(temp_git_repo, bodega_dir, "bodega")

    # Commit initial worktree setup
    subprocess.run(
        ["git", "add", ".bodega/"],
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial bodega worktree setup"],
        check=True,
        capture_output=True
    )

    assert not has_uncommitted_changes(temp_git_repo, ".bodega")


def test_has_uncommitted_changes_with_changes(temp_git_repo):
    """Test has_uncommitted_changes returns True when there are changes."""
    bodega_dir = temp_git_repo / ".bodega"
    init_repository(temp_git_repo)
    init_worktree(temp_git_repo, bodega_dir, "bodega")

    # Commit initial worktree setup
    subprocess.run(
        ["git", "add", ".bodega/"],
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial bodega worktree setup"],
        check=True,
        capture_output=True
    )

    # Create a file in .bodega
    test_file = bodega_dir / "test.txt"
    test_file.write_text("test")

    assert has_uncommitted_changes(temp_git_repo, ".bodega")


def test_get_commits_ahead(temp_git_repo):
    """Test get_commits_ahead counts correctly."""
    bodega_dir = temp_git_repo / ".bodega"
    init_repository(temp_git_repo)
    worktree_bodega_dir = init_worktree(temp_git_repo, bodega_dir, "bodega")
    worktree_path = worktree_bodega_dir.parent

    # Commit initial worktree setup
    subprocess.run(
        ["git", "add", ".bodega/"],
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial bodega worktree setup"],
        check=True,
        capture_output=True
    )

    # Initially, bodega should be ahead of main by at least 1 commit
    commits_ahead = get_commits_ahead(temp_git_repo, "bodega", "main")
    initial_ahead = commits_ahead

    # Add a commit to bodega
    ticket_file = worktree_bodega_dir / "bg-test123.md"
    ticket_file.write_text("# Test")
    auto_commit_ticket(worktree_path, ticket_file, "create", "bg-test123")

    # bodega should be one more commit ahead
    commits_ahead = get_commits_ahead(temp_git_repo, "bodega", "main")
    assert commits_ahead == initial_ahead + 1


def test_get_sync_status(temp_git_repo):
    """Test get_sync_status returns correct status."""
    bodega_dir = temp_git_repo / ".bodega"
    init_repository(temp_git_repo)
    worktree_bodega_dir = init_worktree(temp_git_repo, bodega_dir, "bodega")
    worktree_path = worktree_bodega_dir.parent

    # Commit initial worktree setup
    subprocess.run(
        ["git", "add", ".bodega/"],
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial bodega worktree setup"],
        check=True,
        capture_output=True
    )

    status = get_sync_status(temp_git_repo, worktree_path, "main", "bodega")

    # Should have no uncommitted changes initially
    assert not status.uncommitted_in_main
    assert not status.uncommitted_in_worktree

    # bodega should be ahead
    assert status.commits_ahead_bodega > 0


# ============================================================================
# Sync Tests
# ============================================================================

def test_sync_branches_basic(temp_git_repo):
    """Test basic two-way sync between branches."""
    bodega_dir = temp_git_repo / ".bodega"
    init_repository(temp_git_repo)
    worktree_bodega_dir = init_worktree(temp_git_repo, bodega_dir, "bodega")
    worktree_path = worktree_bodega_dir.parent

    # Commit initial worktree setup
    subprocess.run(
        ["git", "add", ".bodega/"],
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial bodega worktree setup"],
        check=True,
        capture_output=True
    )

    # Create a ticket on bodega branch
    ticket_file = worktree_bodega_dir / "bg-test123.md"
    ticket_file.write_text("# Test ticket")
    auto_commit_ticket(worktree_path, ticket_file, "create", "bg-test123")

    # Sync
    result = sync_branches(temp_git_repo, worktree_path, "main", "bodega")

    assert result.commits_from_bodega > 0
    assert not result.had_conflicts


def test_sync_branches_with_uncommitted_main_fails(temp_git_repo):
    """Test that sync fails if main has uncommitted changes in .bodega."""
    bodega_dir = temp_git_repo / ".bodega"
    init_repository(temp_git_repo)
    worktree_bodega_dir = init_worktree(temp_git_repo, bodega_dir, "bodega")
    worktree_path = worktree_bodega_dir.parent

    # Commit initial worktree setup
    subprocess.run(
        ["git", "add", ".bodega/"],
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial bodega worktree setup"],
        check=True,
        capture_output=True
    )

    # Create uncommitted file in main's .bodega
    test_file = bodega_dir / "test.txt"
    test_file.write_text("uncommitted")

    # Sync should fail
    with pytest.raises(StorageError, match="Uncommitted changes"):
        sync_branches(temp_git_repo, worktree_path, "main", "bodega")


def test_sync_branches_auto_commits_worktree_changes(temp_git_repo):
    """Test that sync auto-commits uncommitted changes in worktree."""
    bodega_dir = temp_git_repo / ".bodega"
    init_repository(temp_git_repo)
    worktree_bodega_dir = init_worktree(temp_git_repo, bodega_dir, "bodega")
    worktree_path = worktree_bodega_dir.parent

    # Commit initial worktree setup
    subprocess.run(
        ["git", "add", ".bodega/"],
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial bodega worktree setup"],
        check=True,
        capture_output=True
    )

    # Create uncommitted file in worktree
    ticket_file = worktree_bodega_dir / "bg-test123.md"
    ticket_file.write_text("# Uncommitted ticket")

    # Sync should auto-commit it
    result = sync_branches(temp_git_repo, worktree_path, "main", "bodega")

    # Check that worktree is now clean
    assert not has_uncommitted_changes(worktree_path, ".bodega")


def test_sync_branches_skip_merge_to_main(temp_git_repo):
    """Test sync with skip_merge_to_main flag."""
    bodega_dir = temp_git_repo / ".bodega"
    init_repository(temp_git_repo)
    worktree_bodega_dir = init_worktree(temp_git_repo, bodega_dir, "bodega")
    worktree_path = worktree_bodega_dir.parent

    # Commit initial worktree setup
    subprocess.run(
        ["git", "add", ".bodega/"],
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial bodega worktree setup"],
        check=True,
        capture_output=True
    )

    # Create ticket on bodega
    ticket_file = worktree_bodega_dir / "bg-test123.md"
    ticket_file.write_text("# Test ticket")
    auto_commit_ticket(worktree_path, ticket_file, "create", "bg-test123")

    # Sync only main → bodega
    result = sync_branches(
        temp_git_repo,
        worktree_path,
        "main",
        "bodega",
        skip_merge_to_main=True
    )

    assert result.commits_from_bodega == 0
    assert result.files_changed == 0


# ============================================================================
# Cleanup Tests
# ============================================================================

def test_cleanup_worktree(temp_git_repo):
    """Test that cleanup_worktree removes worktree."""
    bodega_dir = temp_git_repo / ".bodega"
    init_repository(temp_git_repo)
    worktree_bodega_dir = init_worktree(temp_git_repo, bodega_dir, "bodega")
    worktree_path = worktree_bodega_dir.parent

    # Commit initial worktree setup
    subprocess.run(
        ["git", "add", ".bodega/"],
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial bodega worktree setup"],
        check=True,
        capture_output=True
    )

    assert worktree_path.exists()

    # Cleanup
    cleanup_worktree(worktree_path, temp_git_repo)

    assert not worktree_path.exists()


def test_cleanup_worktree_keeps_branch(temp_git_repo):
    """Test that cleanup_worktree keeps the bodega branch."""
    bodega_dir = temp_git_repo / ".bodega"
    init_repository(temp_git_repo)
    worktree_bodega_dir = init_worktree(temp_git_repo, bodega_dir, "bodega")
    worktree_path = worktree_bodega_dir.parent

    # Commit initial worktree setup
    subprocess.run(
        ["git", "add", ".bodega/"],
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial bodega worktree setup"],
        check=True,
        capture_output=True
    )

    # Cleanup
    cleanup_worktree(worktree_path, temp_git_repo)

    # Branch should still exist
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "bodega"],
        cwd=temp_git_repo,
        capture_output=True
    )
    assert result.returncode == 0
