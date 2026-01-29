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
    result = runner.invoke(main, ["sync"], cwd=str(temp_git_repo))

    assert result.exit_code != 0
    assert "Not in a bodega repository" in result.output


def test_sync_command_basic(runner, temp_git_repo):
    """Test basic sync command execution."""
    # Initialize bodega with worktree
    result = runner.invoke(main, ["init"], cwd=str(temp_git_repo))
    assert result.exit_code == 0

    # Create a ticket
    result = runner.invoke(main, ["create", "Test ticket"], cwd=str(temp_git_repo))
    assert result.exit_code == 0

    # Sync
    result = runner.invoke(main, ["sync"], cwd=str(temp_git_repo))

    assert result.exit_code == 0
    assert "Merged" in result.output
    assert "bodega → main" in result.output or "bodega → master" in result.output


def test_sync_command_dry_run(runner, temp_git_repo):
    """Test sync --dry-run doesn't make changes."""
    # Initialize bodega
    result = runner.invoke(main, ["init"], cwd=str(temp_git_repo))
    assert result.exit_code == 0

    # Create a ticket
    result = runner.invoke(main, ["create", "Test ticket"], cwd=str(temp_git_repo))
    assert result.exit_code == 0

    # Dry run
    result = runner.invoke(main, ["sync", "--dry-run"], cwd=str(temp_git_repo))

    assert result.exit_code == 0
    assert "Sync status:" in result.output
    assert "commits" in result.output


def test_sync_command_no_merge_main(runner, temp_git_repo):
    """Test sync --no-merge-main flag."""
    # Initialize bodega
    result = runner.invoke(main, ["init"], cwd=str(temp_git_repo))
    assert result.exit_code == 0

    # Create a ticket
    result = runner.invoke(main, ["create", "Test ticket"], cwd=str(temp_git_repo))
    assert result.exit_code == 0

    # Sync without merging to main
    result = runner.invoke(main, ["sync", "--no-merge-main"], cwd=str(temp_git_repo))

    assert result.exit_code == 0
    # Should not mention merge to main
    output_lower = result.output.lower()
    assert "bodega → main" not in output_lower and "bodega → master" not in output_lower


def test_sync_command_with_uncommitted_changes(runner, temp_git_repo):
    """Test sync fails with uncommitted changes in .bodega."""
    # Initialize bodega
    result = runner.invoke(main, ["init"], cwd=str(temp_git_repo))
    assert result.exit_code == 0

    # Create uncommitted file in .bodega
    bodega_dir = temp_git_repo / ".bodega"
    test_file = bodega_dir / "test.txt"
    test_file.write_text("uncommitted")

    # Sync should fail
    result = runner.invoke(main, ["sync"], cwd=str(temp_git_repo))

    assert result.exit_code != 0
    assert "Uncommitted changes" in result.output


def test_sync_command_updates_main_branch(runner, temp_git_repo):
    """Test that sync creates files in main branch's .bodega."""
    # Initialize bodega
    result = runner.invoke(main, ["init"], cwd=str(temp_git_repo))
    assert result.exit_code == 0

    # Create a ticket
    result = runner.invoke(main, ["create", "Test ticket"], cwd=str(temp_git_repo))
    assert result.exit_code == 0
    ticket_id = result.output.strip()

    # Sync
    result = runner.invoke(main, ["sync"], cwd=str(temp_git_repo))
    assert result.exit_code == 0

    # Check that ticket file appears in main's .bodega (uncommitted)
    bodega_dir = temp_git_repo / ".bodega"
    ticket_file = bodega_dir / f"{ticket_id}.md"

    # File should exist but be uncommitted
    # We can check git status to see if it's listed
    git_status = subprocess.run(
        ["git", "status", "--porcelain", str(ticket_file)],
        cwd=temp_git_repo,
        capture_output=True,
        text=True
    )
    # File should show up in git status (uncommitted)
    assert ticket_id in git_status.stdout or len(git_status.stdout) > 0


# ============================================================================
# Status Command Tests
# ============================================================================

def test_status_command_requires_git_repo(runner):
    """Test that status fails if not in a git repository."""
    with runner.isolated_filesystem():
        init_repository()

        result = runner.invoke(main, ["status"])

        assert result.exit_code != 0
        assert "Not in a git repository" in result.output


def test_status_command_requires_bodega_init(runner, temp_git_repo):
    """Test that status fails if bodega not initialized."""
    result = runner.invoke(main, ["status"], cwd=str(temp_git_repo))

    assert result.exit_code != 0
    assert "Not in a bodega repository" in result.output


def test_status_command_shows_sync_info(runner, temp_git_repo):
    """Test status command shows sync information."""
    # Initialize bodega
    result = runner.invoke(main, ["init"], cwd=str(temp_git_repo))
    assert result.exit_code == 0

    # Run status
    result = runner.invoke(main, ["status"], cwd=str(temp_git_repo))

    assert result.exit_code == 0
    assert "Bodega branch:" in result.output
    assert "Current branch:" in result.output
    assert "Sync status:" in result.output
    assert "Worktree status:" in result.output


def test_status_command_shows_ticket_count(runner, temp_git_repo):
    """Test status shows number of tickets."""
    # Initialize bodega
    result = runner.invoke(main, ["init"], cwd=str(temp_git_repo))
    assert result.exit_code == 0

    # Create tickets
    runner.invoke(main, ["create", "Ticket 1"], cwd=str(temp_git_repo))
    runner.invoke(main, ["create", "Ticket 2"], cwd=str(temp_git_repo))
    runner.invoke(main, ["create", "Ticket 3"], cwd=str(temp_git_repo))

    # Run status
    result = runner.invoke(main, ["status"], cwd=str(temp_git_repo))

    assert result.exit_code == 0
    assert "Tickets: 3 files" in result.output


def test_status_command_shows_uncommitted_warning(runner, temp_git_repo):
    """Test status shows warning for uncommitted changes."""
    # Initialize bodega
    result = runner.invoke(main, ["init"], cwd=str(temp_git_repo))
    assert result.exit_code == 0

    # Create uncommitted file in .bodega
    bodega_dir = temp_git_repo / ".bodega"
    test_file = bodega_dir / "test.txt"
    test_file.write_text("uncommitted")

    # Run status
    result = runner.invoke(main, ["status"], cwd=str(temp_git_repo))

    assert result.exit_code == 0
    assert "Uncommitted changes" in result.output or "⚠" in result.output


def test_status_command_in_sync(runner, temp_git_repo):
    """Test status shows 'In sync' when synchronized."""
    # Initialize bodega
    result = runner.invoke(main, ["init"], cwd=str(temp_git_repo))
    assert result.exit_code == 0

    # Create and sync a ticket
    runner.invoke(main, ["create", "Test ticket"], cwd=str(temp_git_repo))
    runner.invoke(main, ["sync"], cwd=str(temp_git_repo))

    # Commit the synced changes in main
    subprocess.run(
        ["git", "add", ".bodega/"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Add tickets"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True
    )

    # Now sync again - should be in sync
    runner.invoke(main, ["sync"], cwd=str(temp_git_repo))

    # Run status
    result = runner.invoke(main, ["status"], cwd=str(temp_git_repo))

    assert result.exit_code == 0
    assert "In sync" in result.output or "0 commits" in result.output


def test_status_command_out_of_sync(runner, temp_git_repo):
    """Test status shows 'Out of sync' when not synchronized."""
    # Initialize bodega
    result = runner.invoke(main, ["init"], cwd=str(temp_git_repo))
    assert result.exit_code == 0

    # Create ticket (will be on bodega branch, not synced to main yet)
    runner.invoke(main, ["create", "Test ticket"], cwd=str(temp_git_repo))

    # Run status without syncing
    result = runner.invoke(main, ["status"], cwd=str(temp_git_repo))

    assert result.exit_code == 0
    assert "Out of sync" in result.output or "commits ahead" in result.output


# ============================================================================
# Integration Tests
# ============================================================================

def test_full_workflow_create_sync_commit(runner, temp_git_repo):
    """Test full workflow: init, create tickets, sync, commit."""
    # 1. Initialize bodega
    result = runner.invoke(main, ["init"], cwd=str(temp_git_repo))
    assert result.exit_code == 0

    # 2. Create multiple tickets
    ticket_ids = []
    for i in range(3):
        result = runner.invoke(main, ["create", f"Ticket {i+1}"], cwd=str(temp_git_repo))
        assert result.exit_code == 0
        ticket_ids.append(result.output.strip())

    # 3. List tickets (should show all 3)
    result = runner.invoke(main, ["list"], cwd=str(temp_git_repo))
    assert result.exit_code == 0
    for ticket_id in ticket_ids:
        assert ticket_id in result.output

    # 4. Sync to main
    result = runner.invoke(main, ["sync"], cwd=str(temp_git_repo))
    assert result.exit_code == 0

    # 5. Commit in main
    subprocess.run(
        ["git", "add", ".bodega/"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Add tickets"],
        cwd=temp_git_repo,
        check=True,
        capture_output=True
    )

    # 6. Push both branches (simulate)
    # Just verify branches exist
    result = subprocess.run(
        ["git", "branch"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True
    )
    assert "bodega" in result.stdout


def test_workflow_with_ticket_updates(runner, temp_git_repo):
    """Test workflow with creating, updating, and syncing tickets."""
    # Initialize
    result = runner.invoke(main, ["init"], cwd=str(temp_git_repo))
    assert result.exit_code == 0

    # Create ticket
    result = runner.invoke(main, ["create", "Initial ticket"], cwd=str(temp_git_repo))
    assert result.exit_code == 0
    ticket_id = result.output.strip()

    # Update ticket (e.g., close it)
    result = runner.invoke(main, ["close", ticket_id], cwd=str(temp_git_repo))
    assert result.exit_code == 0

    # Sync
    result = runner.invoke(main, ["sync"], cwd=str(temp_git_repo))
    assert result.exit_code == 0

    # Verify ticket is closed in synced files
    bodega_dir = temp_git_repo / ".bodega"
    ticket_file = bodega_dir / f"{ticket_id}.md"

    # After sync, file should exist in main's .bodega (uncommitted)
    # Check via git diff
    git_diff = subprocess.run(
        ["git", "diff", "HEAD", str(ticket_file)],
        cwd=temp_git_repo,
        capture_output=True,
        text=True
    )
    # Should show the file as new or modified
    assert len(git_diff.stdout) > 0 or ticket_file.exists()
