"""Tests for CLI base structure."""

from pathlib import Path
import subprocess

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
        "import", "sync",
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


def test_init_reset(runner):
    """Test that init --reset reinitializes existing repo."""
    with runner.isolated_filesystem():
        Path(".bodega").mkdir()
        result = runner.invoke(main, ["init", "--reset"])

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


def test_init_adopts_cloned_repo_direct_mode(runner):
    """Test that init adopts a cloned repository in direct mode (no worktree)."""
    with runner.isolated_filesystem():
        # Simulate a cloned repository with .bodega and config (direct mode)
        subprocess.run(["git", "init"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], check=True, capture_output=True)

        # Create .bodega with config (simulating cloned state)
        Path(".bodega").mkdir()
        config_content = """# Bodega configuration
defaults:
  type: task
  priority: 2

git:
  branch: ""
"""
        Path(".bodega/config.yaml").write_text(config_content)

        # Run init without --reset (should adopt existing config)
        result = runner.invoke(main, ["init"])

        assert result.exit_code == 0
        assert "Found existing bodega repository" in result.output
        assert "Tickets are stored in .bodega/ on current branch" in result.output
        assert "Repository ready to use" in result.output
        # Should NOT say "Initialized" since it's adopting
        assert "Initialized bodega repository" not in result.output


def test_init_adopts_cloned_repo_worktree_mode(runner):
    """Test that init adopts a cloned repository with worktree mode."""
    with runner.isolated_filesystem():
        # Set up git repository
        subprocess.run(["git", "init"], check=True, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "main"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], check=True, capture_output=True)

        # Create initial commit (required for worktree)
        Path("README.md").write_text("# Test")
        subprocess.run(["git", "add", "README.md"], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], check=True, capture_output=True)

        # Create bodega branch with tickets (simulating remote state)
        subprocess.run(["git", "checkout", "-b", "bodega"], check=True, capture_output=True)
        Path(".bodega").mkdir()
        Path(".bodega/config.yaml").write_text("""# Bodega configuration
git:
  branch: bodega
""")
        subprocess.run(["git", "add", ".bodega"], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add bodega config"], check=True, capture_output=True)

        # Switch back to main branch
        subprocess.run(["git", "checkout", "main"], check=True, capture_output=True)

        # Create .bodega with config on main (simulating cloned state where .bodega is on main but worktree doesn't exist)
        Path(".bodega").mkdir()
        Path(".bodega/config.yaml").write_text("""# Bodega configuration
git:
  branch: bodega
""")

        # Run init (should set up worktree from existing branch)
        result = runner.invoke(main, ["init"])

        assert result.exit_code == 0
        assert "Found existing bodega repository" in result.output
        assert "Setting up worktree for branch 'bodega'" in result.output
        assert "Created git worktree on branch 'bodega'" in result.output
        assert Path(".bodega/worktree").is_dir()


def test_init_with_existing_config_without_reset_fails_only_dir(runner):
    """Test that init without config.yaml still requires --reset."""
    with runner.isolated_filesystem():
        # Create only .bodega directory without config.yaml
        Path(".bodega").mkdir()

        result = runner.invoke(main, ["init"])

        # Should fail because .bodega exists but no config
        assert result.exit_code == 1
        assert "already exists" in result.output


def test_init_reset_overwrites_existing_config(runner):
    """Test that init --reset overwrites existing configuration."""
    with runner.isolated_filesystem():
        # Create existing .bodega with custom config
        Path(".bodega").mkdir()
        Path(".bodega/config.yaml").write_text("""# Custom config
defaults:
  priority: 0
id_prefix: custom
""")

        # Read original config to confirm it has custom values
        original_config = Path(".bodega/config.yaml").read_text()
        assert "id_prefix: custom" in original_config
        assert "priority: 0" in original_config

        # Run init with --reset
        result = runner.invoke(main, ["init", "--reset"])

        assert result.exit_code == 0
        assert "Initialized bodega repository" in result.output

        # Config should be overwritten - custom values should be gone
        config_content = Path(".bodega/config.yaml").read_text()
        assert "id_prefix: custom" not in config_content
        assert "priority: 0" not in config_content
        # Should have default values (priority: 2, branch: '')
        assert "priority: 2" in config_content
        assert "branch: ''" in config_content or 'branch: ""' in config_content


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
