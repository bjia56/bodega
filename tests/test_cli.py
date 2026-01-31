"""Tests for CLI base structure."""

from pathlib import Path

from bodega.cli import main
from bodega import __version__


# ============================================================================
# Basic CLI Tests
# ============================================================================

def test_version(runner):
    """Test --version flag."""
    result = runner.invoke(main, ["--version"])

    assert result.exit_code == 0
    assert __version__ in result.output


def test_help(runner):
    """Test --help flag."""
    result = runner.invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "Bodega" in result.output
    assert "Git-native issue tracking" in result.output


def test_main_without_args(runner):
    """Test running main command without arguments."""
    result = runner.invoke(main, [])

    # Should show help or usage when no command given
    assert result.exit_code == 2


def test_debug_flag(runner):
    """Test --debug flag is recognized."""
    result = runner.invoke(main, ["--debug", "--help"])

    # Should not error out
    assert result.exit_code == 0


# ============================================================================
# Command Registration Tests
# ============================================================================

def test_init_command_registered(runner):
    """Test that init command is registered."""
    result = runner.invoke(main, ["init", "--help"])

    assert result.exit_code == 0
    assert "init" in result.output.lower()


def test_create_command_registered(runner):
    """Test that create command is registered."""
    result = runner.invoke(main, ["create", "--help"])

    assert result.exit_code == 0
    assert "create" in result.output.lower()


def test_list_command_registered(runner):
    """Test that list command is registered."""
    result = runner.invoke(main, ["list", "--help"])

    assert result.exit_code == 0
    assert "list" in result.output.lower()


def test_show_command_registered(runner):
    """Test that show command is registered."""
    result = runner.invoke(main, ["show", "--help"])

    assert result.exit_code == 0
    assert "show" in result.output.lower()


def test_start_command_registered(runner):
    """Test that start command is registered."""
    result = runner.invoke(main, ["start", "--help"])

    assert result.exit_code == 0
    assert "start" in result.output.lower()


def test_close_command_registered(runner):
    """Test that close command is registered."""
    result = runner.invoke(main, ["close", "--help"])

    assert result.exit_code == 0
    assert "close" in result.output.lower()


def test_tree_command_registered(runner):
    """Test that tree command is registered."""
    result = runner.invoke(main, ["tree", "--help"])

    assert result.exit_code == 0
    assert "tree" in result.output.lower()


# ============================================================================
# Context and Repository Tests
# ============================================================================

def test_not_in_repo_fails_for_list(runner):
    """Test that commands requiring repo fail when not in one."""
    with runner.isolated_filesystem():
        # Don't create a repo, just try to list
        result = runner.invoke(main, ["list"])
        print(result.output)

        assert result.exit_code == 1
        assert "Not in a bodega repository" in result.output
        assert "bodega init" in result.output


def test_not_in_repo_fails_for_show(runner):
    """Test that show command fails when not in repo."""
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["show", "bg-test"])

        assert result.exit_code == 1
        assert "Not in a bodega repository" in result.output


def test_init_works_without_repo(runner):
    """Test that init command works even when not in a repo."""
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init", "--help"])

        # Should show help successfully
        assert result.exit_code == 0


# ============================================================================
# Filter Options Tests
# ============================================================================

def test_list_with_status_filter(runner, temp_repo):
    """Test that list command accepts --status filter."""
    result = runner.invoke(main, ["list", "--status", "open"])

    # Should not error on the option itself
    assert "--status" not in result.output or "Error" not in result.output


def test_list_with_type_filter(runner, temp_repo):
    """Test that list command accepts --type filter."""
    result = runner.invoke(main, ["list", "--type", "bug"])

    # Should not error on the option itself
    assert "--type" not in result.output or "Error" not in result.output


def test_list_with_priority_filter(runner, temp_repo):
    """Test that list command accepts --priority filter."""
    result = runner.invoke(main, ["list", "--priority", "1"])

    # Should not error on the option itself
    assert "--priority" not in result.output or "Error" not in result.output


# ============================================================================
# Format Option Tests
# ============================================================================

def test_list_with_table_format(runner, temp_repo):
    """Test that list command accepts --format table."""
    result = runner.invoke(main, ["list", "--format", "table"])

    # Should accept the format option
    assert result.exit_code != 2  # Not a usage error


def test_list_with_compact_format(runner, temp_repo):
    """Test that list command accepts --format compact."""
    result = runner.invoke(main, ["list", "--format", "compact"])

    assert result.exit_code != 2


def test_list_with_ids_format(runner, temp_repo):
    """Test that list command accepts --format ids."""
    result = runner.invoke(main, ["list", "--format", "ids"])

    assert result.exit_code != 2


def test_list_with_json_format(runner, temp_repo):
    """Test that list command accepts --format json."""
    result = runner.invoke(main, ["list", "--format", "json"])

    assert result.exit_code != 2


def test_list_with_invalid_format(runner, temp_repo):
    """Test that list command rejects invalid format."""
    result = runner.invoke(main, ["list", "--format", "invalid"])

    # Should be a usage error
    assert result.exit_code == 2
    assert "Invalid value" in result.output or "invalid" in result.output


# ============================================================================
# Ticket ID Argument Tests
# ============================================================================

def test_show_requires_ticket_id(runner, temp_repo):
    """Test that show command requires a ticket ID."""
    result = runner.invoke(main, ["show"])

    # Should be a usage error
    assert result.exit_code == 2
    assert "Missing argument" in result.output or "ID" in result.output


def test_start_requires_ticket_id(runner, temp_repo):
    """Test that start command requires a ticket ID."""
    result = runner.invoke(main, ["start"])

    assert result.exit_code == 2
    assert "Missing argument" in result.output or "ID" in result.output


def test_close_requires_ticket_id(runner, temp_repo):
    """Test that close command requires a ticket ID."""
    result = runner.invoke(main, ["close"])

    assert result.exit_code == 2
    assert "Missing argument" in result.output or "ID" in result.output


# ============================================================================
# Create Command Tests
# ============================================================================

def test_create_accepts_options(runner, temp_repo):
    """Test that create command accepts various options."""
    result = runner.invoke(main, [
        "create",
        "Test ticket",
        "--type", "bug",
        "--priority", "1",
        "--assignee", "alice",
        "--tag", "urgent",
        "--tag", "security",
    ])

    # Should accept all these options without usage error
    assert result.exit_code != 2


# ============================================================================
# Dependency Command Tests
# ============================================================================

def test_dep_requires_two_ids(runner, temp_repo):
    """Test that dep command requires two ticket IDs."""
    result = runner.invoke(main, ["dep"])

    assert result.exit_code == 2
    assert "Missing argument" in result.output


def test_dep_accepts_two_ids(runner, temp_repo):
    """Test that dep command accepts two IDs."""
    result = runner.invoke(main, ["dep", "bg-aaa", "bg-bbb"])

    # Should not be a usage error
    assert result.exit_code != 2


def test_tree_works_without_id(runner, temp_repo):
    """Test that tree command works without an ID."""
    result = runner.invoke(main, ["tree"])

    # Should not be a usage error (ID is optional)
    assert result.exit_code != 2


def test_tree_accepts_optional_id(runner, temp_repo):
    """Test that tree command accepts an optional ID."""
    result = runner.invoke(main, ["tree", "bg-aaa"])

    # Should not be a usage error
    assert result.exit_code != 2


# ============================================================================
# Integration Tests
# ============================================================================

def test_command_help_available_for_all(runner):
    """Test that --help works for all commands."""
    commands = [
        "init", "create", "list", "show", "edit", "note",
        "start", "close", "reopen", "status",
        "ready", "blocked", "closed", "query",
        "dep", "undep", "link", "unlink", "tree", "cycle",
        "transfer", "sync", "sync-status",
    ]

    for cmd in commands:
        result = runner.invoke(main, [cmd, "--help"])
        assert result.exit_code == 0, f"Help failed for command: {cmd}"
        assert "help" in result.output.lower() or "usage" in result.output.lower()


# ============================================================================
# Init Command Tests
# ============================================================================

def test_init_creates_directory(runner):
    """Test that init creates .bodega directory and config."""
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init"])

        assert result.exit_code == 0
        assert Path(".bodega").is_dir()
        assert Path(".bodega/config.yaml").is_file()
        assert "Initialized bodega repository" in result.output


def test_init_fails_if_exists(runner):
    """Test that init fails if .bodega already exists."""
    with runner.isolated_filesystem():
        Path(".bodega").mkdir()
        result = runner.invoke(main, ["init"])

        assert result.exit_code == 1
        assert "already exists" in result.output


def test_init_force(runner):
    """Test that init --force reinitializes existing repo."""
    with runner.isolated_filesystem():
        Path(".bodega").mkdir()
        result = runner.invoke(main, ["init", "--force"])

        assert result.exit_code == 0
        assert Path(".bodega/config.yaml").is_file()
        assert "Initialized bodega repository" in result.output


def test_init_with_path(runner):
    """Test that init works with specified path."""
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init", "subdir"])

        assert result.exit_code == 0
        assert Path("subdir/.bodega").is_dir()
        assert Path("subdir/.bodega/config.yaml").is_file()


def test_init_with_relative_path(runner):
    """Test that init works with relative path."""
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init", "./myproject"])

        assert result.exit_code == 0
        assert Path("myproject/.bodega").is_dir()
        assert Path("myproject/.bodega/config.yaml").is_file()


def test_init_creates_parents(runner):
    """Test that init creates parent directories if needed."""
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init", "parent/child/repo"])

        assert result.exit_code == 0
        assert Path("parent/child/repo/.bodega").is_dir()
        assert Path("parent/child/repo/.bodega/config.yaml").is_file()


def test_init_output_message(runner):
    """Test that init outputs correct message with path."""
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init"])

        assert result.exit_code == 0
        # Should show the absolute path to .bodega
        assert "Initialized bodega repository" in result.output
        assert ".bodega" in result.output
