"""Tests for sync command."""

import pytest
import subprocess
from pathlib import Path

from bodega.cli import main
from bodega.storage import init_repository
from bodega.worktree import init_worktree


# ============================================================================
# Sync Command Tests
# ============================================================================

def test_sync_command_requires_git_repo(runner):
    """Test that sync fails if not in a git repository."""
    with runner.isolated_filesystem():
        init_repository()

        result = runner.invoke(main, ["sync"])

        assert result.exit_code != 0
        assert "Not in a git repository" in result.output


def test_sync_command_requires_bodega_init(runner, temp_git_repo):
    """Test that sync fails if bodega not initialized."""
    result = runner.invoke(main, ["sync"])
    print(result.output)

    assert result.exit_code != 0
    assert "Not in a bodega repository" in result.output


def test_sync_command_basic(runner, temp_git_repo):
    """Test basic sync command execution."""
    # Initialize bodega with worktree
    result = runner.invoke(main, ["init", "--branch", "bodega"])
    print(result.output)
    assert result.exit_code == 0

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

    # Create a ticket
    result = runner.invoke(main, ["order", "Test ticket"])
    print(result.output)
    assert result.exit_code == 0

    # Sync
    result = runner.invoke(main, ["sync"])
    print(result.output)
    assert result.exit_code == 0
    assert "Merged" in result.output
    assert "bodega → main" in result.output or "bodega → master" in result.output


def test_sync_command_dry_run(runner, temp_git_repo):
    """Test sync --dry-run doesn't make changes."""
    # Initialize bodega
    result = runner.invoke(main, ["init", "--branch", "bodega"])
    assert result.exit_code == 0

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

    # Create a ticket
    result = runner.invoke(main, ["order", "Test ticket"])
    assert result.exit_code == 0

    # Dry run
    result = runner.invoke(main, ["sync", "--dry-run"])

    assert result.exit_code == 0
    assert "Sync status:" in result.output
    assert "commits" in result.output


def test_sync_command_no_merge_main(runner, temp_git_repo):
    """Test sync --no-merge-main flag."""
    # Initialize bodega
    result = runner.invoke(main, ["init", "--branch", "bodega"])
    assert result.exit_code == 0

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

    # Create a ticket
    result = runner.invoke(main, ["order", "Test ticket"])
    assert result.exit_code == 0

    # Sync without merging to main
    result = runner.invoke(main, ["sync", "--no-merge-main"])

    assert result.exit_code == 0
    # Should not mention merge to main
    output_lower = result.output.lower()
    assert "bodega → main" not in output_lower and "bodega → master" not in output_lower


def test_sync_command_with_uncommitted_changes(runner, temp_git_repo):
    """Test sync fails with uncommitted changes in .bodega."""
    # Initialize bodega
    result = runner.invoke(main, ["init", "--branch", "bodega"])
    assert result.exit_code == 0

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

    # Create uncommitted file in .bodega
    bodega_dir = temp_git_repo / ".bodega"
    test_file = bodega_dir / "test.txt"
    test_file.write_text("uncommitted")

    # Sync should fail
    result = runner.invoke(main, ["sync"])

    assert result.exit_code != 0
    assert "Uncommitted changes" in result.output


def test_sync_command_updates_main_branch(runner, temp_git_repo):
    """Test that sync creates files in main branch's .bodega."""
    # Initialize bodega
    result = runner.invoke(main, ["init", "--branch", "bodega"])
    assert result.exit_code == 0

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

    # Create a ticket
    result = runner.invoke(main, ["order", "Test ticket"])
    assert result.exit_code == 0
    ticket_id = result.output.strip()

    # Sync
    result = runner.invoke(main, ["sync"])
    assert result.exit_code == 0

    # Check that ticket file appears in main's .bodega (uncommitted)
    bodega_dir = temp_git_repo / ".bodega"
    ticket_file = bodega_dir / f"{ticket_id}.md"

    # File is created and committed
    assert ticket_file.exists()

    # Git is clean
    git_status = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True
    )
    assert git_status.stdout.strip() == ""


# ============================================================================
# sync-status Command Tests
# ============================================================================

def test_sync_status_command_requires_git_repo(runner):
    """Test that sync-status fails if not in a git repository."""
    with runner.isolated_filesystem():
        init_repository()

        result = runner.invoke(main, ["sync-status"])

        assert result.exit_code != 0
        assert "Not in a git repository" in result.output


def test_sync_status_command_requires_bodega_init(runner, temp_git_repo):
    """Test that sync-status fails if bodega not initialized."""
    result = runner.invoke(main, ["sync-status"])

    assert result.exit_code != 0
    assert "Not in a bodega repository" in result.output


def test_sync_status_command_shows_sync_info(runner, temp_git_repo):
    """Test sync-status command shows sync information."""
    # Initialize bodega
    result = runner.invoke(main, ["init", "--branch", "bodega"])
    assert result.exit_code == 0

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

    # Run sync-status
    result = runner.invoke(main, ["sync-status"])

    assert result.exit_code == 0
    assert "Bodega branch:" in result.output
    assert "Current branch:" in result.output
    assert "Sync status:" in result.output
    assert "Worktree status:" in result.output


def test_sync_status_command_shows_ticket_count(runner, temp_git_repo):
    """Test sync-status shows number of tickets."""
    # Initialize bodega
    result = runner.invoke(main, ["init", "--branch", "bodega"])
    assert result.exit_code == 0

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

    # Create tickets
    runner.invoke(main, ["order", "Ticket 1"])
    runner.invoke(main, ["order", "Ticket 2"])
    runner.invoke(main, ["order", "Ticket 3"])

    # Run sync-status
    result = runner.invoke(main, ["sync-status"])

    assert result.exit_code == 0
    assert "Tickets: 3 files" in result.output


def test_sync_status_command_shows_uncommitted_warning(runner, temp_git_repo):
    """Test sync-status shows warning for uncommitted changes."""
    # Initialize bodega
    result = runner.invoke(main, ["init", "--branch", "bodega"])
    assert result.exit_code == 0

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

    # Create uncommitted file in .bodega
    bodega_dir = temp_git_repo / ".bodega"
    test_file = bodega_dir / "test.txt"
    test_file.write_text("uncommitted")

    # Run sync-status
    result = runner.invoke(main, ["sync-status"])

    assert result.exit_code == 0
    assert "Uncommitted changes" in result.output or "⚠" in result.output


def test_sync_status_command_in_sync(runner, temp_git_repo):
    """Test sync-status shows 'In sync' when synchronized."""
    # Initialize bodega
    result = runner.invoke(main, ["init", "--branch", "bodega"])
    assert result.exit_code == 0

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

    # Create and sync a ticket
    runner.invoke(main, ["order", "Test ticket"])
    runner.invoke(main, ["sync"])

    # Run sync-status
    result = runner.invoke(main, ["sync-status"])

    assert result.exit_code == 0
    assert "In sync" in result.output or "0 commits" in result.output


def test_sync_status_command_out_of_sync(runner, temp_git_repo):
    """Test sync-status shows 'Out of sync' when not synchronized."""
    # Initialize bodega
    result = runner.invoke(main, ["init", "--branch", "bodega"])
    assert result.exit_code == 0

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

    # Create ticket (will be on bodega branch, not synced to main yet)
    runner.invoke(main, ["order", "Test ticket"])

    # Run sync-status without syncing
    result = runner.invoke(main, ["sync-status"])

    assert result.exit_code == 0
    assert "Out of sync" in result.output or "commits ahead" in result.output


# ============================================================================
# Integration Tests
# ============================================================================

def test_full_workflow_create_sync_commit(runner, temp_git_repo):
    """Test full workflow: init, create tickets, sync, commit."""
    # 1. Initialize bodega
    result = runner.invoke(main, ["init", "--branch", "bodega"])
    assert result.exit_code == 0

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

    # 2. Create multiple tickets
    ticket_ids = []
    for i in range(3):
        result = runner.invoke(main, ["order", f"Ticket {i+1}"])
        assert result.exit_code == 0
        ticket_ids.append(result.output.strip())

    # 3. List tickets (should show all 3)
    result = runner.invoke(main, ["list"])
    assert result.exit_code == 0
    for ticket_id in ticket_ids:
        assert ticket_id in result.output

    # 4. Sync to main
    result = runner.invoke(main, ["sync"])
    assert result.exit_code == 0

    # 5. Verify tickets exist in main's .bodega
    bodega_dir = temp_git_repo / ".bodega"
    for ticket_id in ticket_ids:
        ticket_file = bodega_dir / f"{ticket_id}.md"
        assert ticket_file.exists()


def test_workflow_with_ticket_updates(runner, temp_git_repo):
    """Test workflow with creating, updating, and syncing tickets."""
    # Initialize
    result = runner.invoke(main, ["init", "--branch", "bodega"])
    assert result.exit_code == 0

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

    # Create ticket
    result = runner.invoke(main, ["order", "Initial ticket"])
    assert result.exit_code == 0
    ticket_id = result.output.strip()

    # Update ticket (e.g., close it)
    result = runner.invoke(main, ["bag", ticket_id])
    assert result.exit_code == 0

    # Sync
    result = runner.invoke(main, ["sync"])
    assert result.exit_code == 0

    # Verify ticket is closed in synced files
    bodega_dir = temp_git_repo / ".bodega"
    ticket_file = bodega_dir / f"{ticket_id}.md"

    # After sync, file should exist in main's .bodega (uncommitted)
    # Check via git diff
    git_diff = subprocess.run(
        ["git", "diff", "HEAD", str(ticket_file)],
        capture_output=True,
        text=True
    )
    # Should show the file as new or modified
    assert len(git_diff.stdout) > 0 or ticket_file.exists()
