"""Tests for push command."""

import subprocess

from bodega.cli import main
from bodega.storage import init_repository


# ============================================================================
# Push Command Tests
# ============================================================================

def test_push_command_requires_git_repo(runner):
    """Test that push fails if not in a git repository."""
    with runner.isolated_filesystem():
        init_repository()

        result = runner.invoke(main, ["push"])

        assert result.exit_code != 0
        assert "Not in a git repository" in result.output


def test_push_command_requires_bodega_init(runner, temp_git_repo):
    """Test that push fails if bodega not initialized."""
    result = runner.invoke(main, ["push"])

    assert result.exit_code != 0
    assert "Not in a bodega repository" in result.output


def test_push_command_dry_run(runner, temp_git_repo):
    """Test push --dry-run shows status without making changes."""
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
    result = runner.invoke(main, ["create", "Test ticket"])
    assert result.exit_code == 0

    # Dry run push
    result = runner.invoke(main, ["push", "--dry-run"])

    assert result.exit_code == 0
    assert "Push status:" in result.output
    assert "Local branch:" in result.output


def test_push_command_basic(runner, temp_git_repo_with_remote):
    """Test basic push command execution."""
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
    result = runner.invoke(main, ["create", "Test ticket"])
    assert result.exit_code == 0

    # Push
    result = runner.invoke(main, ["push"])

    assert result.exit_code == 0
    assert "Pushed" in result.output or "up-to-date" in result.output.lower()


def test_push_command_auto_commits(runner, temp_git_repo_with_remote):
    """Test that push auto-commits uncommitted changes."""
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

    # Create a ticket (this creates uncommitted changes in worktree)
    result = runner.invoke(main, ["create", "Test ticket"])
    assert result.exit_code == 0

    # Push should auto-commit
    result = runner.invoke(main, ["push"])

    assert result.exit_code == 0
    # Should mention auto-commit
    assert "Auto-committed" in result.output or "Pushed" in result.output


# ============================================================================
# Integration Tests
# ============================================================================

def test_full_workflow_create_and_push(runner, temp_git_repo_with_remote):
    """Test full workflow: init, create tickets, push."""
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
        result = runner.invoke(main, ["create", f"Ticket {i+1}"])
        assert result.exit_code == 0
        ticket_ids.append(result.output.strip())

    # 3. Push to remote
    result = runner.invoke(main, ["push"])
    assert result.exit_code == 0

    # 4. Verify remote has the changes
    worktree_path = temp_git_repo_with_remote / ".bodega" / "worktree"
    subprocess.run(
        ["git", "fetch", "origin", "bodega"],
        cwd=worktree_path,
        check=True,
        capture_output=True
    )

    # Check that origin/bodega exists
    result = subprocess.run(
        ["git", "rev-parse", "origin/bodega"],
        cwd=worktree_path,
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
