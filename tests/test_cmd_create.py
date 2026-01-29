"""Tests for create command."""

import pytest
from pathlib import Path
import json

from bodega.cli import main


# ============================================================================
# Basic Create Tests
# ============================================================================

def test_create_minimal(runner, temp_repo):
    """Test creating a ticket with just a title."""
    result = runner.invoke(main, ["create", "Test ticket"])

    assert result.exit_code == 0
    ticket_id = result.output.strip()
    assert ticket_id.startswith("bg-")


def test_create_with_type(runner, temp_repo):
    """Test creating a ticket with specific type."""
    result = runner.invoke(main, ["create", "-t", "bug", "Bug ticket"])

    assert result.exit_code == 0
    ticket_id = result.output.strip()

    # Verify ticket was created with correct type
    result = runner.invoke(main, ["show", ticket_id])
    assert "bug" in result.output.lower()


def test_create_with_priority(runner, temp_repo):
    """Test creating a ticket with specific priority."""
    result = runner.invoke(main, ["create", "-p", "1", "High priority ticket"])

    assert result.exit_code == 0
    ticket_id = result.output.strip()

    # Verify ticket was created
    result = runner.invoke(main, ["show", ticket_id])
    assert "priority: 1" in result.output.lower()


def test_create_with_assignee(runner, temp_repo):
    """Test creating a ticket with specific assignee."""
    result = runner.invoke(main, ["create", "-a", "alice", "Assigned ticket"])

    assert result.exit_code == 0
    ticket_id = result.output.strip()

    # Verify ticket was created
    result = runner.invoke(main, ["show", ticket_id])
    assert "alice" in result.output.lower()


def test_create_with_single_tag(runner, temp_repo):
    """Test creating a ticket with a single tag."""
    result = runner.invoke(main, ["create", "--tag", "urgent", "Tagged ticket"])

    assert result.exit_code == 0
    ticket_id = result.output.strip()

    # Verify ticket was created
    result = runner.invoke(main, ["show", ticket_id])
    assert "urgent" in result.output.lower()


def test_create_with_multiple_tags(runner, temp_repo):
    """Test creating a ticket with multiple tags."""
    result = runner.invoke(main, [
        "create",
        "--tag", "urgent",
        "--tag", "api",
        "--tag", "security",
        "Multi-tagged ticket"
    ])

    assert result.exit_code == 0
    ticket_id = result.output.strip()

    # Verify ticket was created with all tags
    result = runner.invoke(main, ["show", ticket_id])
    assert "urgent" in result.output.lower()
    assert "api" in result.output.lower()
    assert "security" in result.output.lower()


def test_create_with_description(runner, temp_repo):
    """Test creating a ticket with description."""
    result = runner.invoke(main, [
        "create",
        "--description", "This is the description",
        "Test ticket"
    ])

    assert result.exit_code == 0
    ticket_id = result.output.strip()

    # Verify ticket has description
    result = runner.invoke(main, ["show", ticket_id])
    assert "This is the description" in result.output


def test_create_with_parent(runner, temp_repo):
    """Test creating a ticket with parent."""
    # Create parent ticket first
    result = runner.invoke(main, ["create", "Parent ticket"])
    parent_id = result.output.strip()

    # Create child ticket
    result = runner.invoke(main, [
        "create",
        "--parent", parent_id,
        "Child ticket"
    ])

    assert result.exit_code == 0
    child_id = result.output.strip()

    # Verify parent was set
    result = runner.invoke(main, ["show", child_id])
    assert parent_id in result.output


def test_create_with_external_ref(runner, temp_repo):
    """Test creating a ticket with external reference."""
    result = runner.invoke(main, [
        "create",
        "-e", "JIRA-123",
        "Linked ticket"
    ])

    assert result.exit_code == 0
    ticket_id = result.output.strip()

    # Verify external ref was set
    result = runner.invoke(main, ["show", ticket_id])
    assert "JIRA-123" in result.output


def test_create_with_single_dep(runner, temp_repo):
    """Test creating a ticket with a dependency."""
    # Create dependency ticket first
    result = runner.invoke(main, ["create", "Dependency ticket"])
    dep_id = result.output.strip()

    # Create ticket with dependency
    result = runner.invoke(main, [
        "create",
        "-d", dep_id,
        "Dependent ticket"
    ])

    assert result.exit_code == 0


def test_create_with_multiple_deps(runner, temp_repo):
    """Test creating a ticket with multiple dependencies."""
    # Create dependency tickets first
    result = runner.invoke(main, ["create", "Dependency 1"])
    dep1_id = result.output.strip()

    result = runner.invoke(main, ["create", "Dependency 2"])
    dep2_id = result.output.strip()

    # Create ticket with multiple dependencies
    result = runner.invoke(main, [
        "create",
        "-d", dep1_id,
        "-d", dep2_id,
        "Dependent ticket"
    ])

    assert result.exit_code == 0
    ticket_id = result.output.strip()

    # Verify dependencies were set
    result = runner.invoke(main, ["show", ticket_id])
    assert dep1_id in result.output
    assert dep2_id in result.output


def test_create_with_all_options(runner, temp_repo):
    """Test creating a ticket with all options."""
    # Create dependency
    result = runner.invoke(main, ["create", "Dependency"])
    dep_id = result.output.strip()

    # Create parent
    result = runner.invoke(main, ["create", "Parent"])
    parent_id = result.output.strip()

    # Create ticket with all options
    result = runner.invoke(main, [
        "create",
        "-t", "bug",
        "-p", "1",
        "-a", "alice",
        "--tag", "urgent",
        "--tag", "api",
        "--parent", parent_id,
        "-e", "JIRA-123",
        "-d", dep_id,
        "--description", "This is the description",
        "Critical bug"
    ])

    assert result.exit_code == 0
    ticket_id = result.output.strip()
    assert ticket_id.startswith("bg-")


# ============================================================================
# Validation Tests
# ============================================================================

def test_create_warns_about_nonexistent_dep(runner, temp_repo):
    """Test that create warns about non-existent dependencies."""
    result = runner.invoke(main, [
        "create",
        "-d", "bg-nonexistent",
        "Test ticket"
    ])

    # Should still succeed but warn
    assert result.exit_code == 0
    assert "Warning" in result.output
    assert "does not exist" in result.output


def test_create_requires_title_or_no_args(runner, temp_repo):
    """Test that create requires either a title or no args for interactive."""
    # With title should work
    result = runner.invoke(main, ["create", "Test"])
    assert result.exit_code == 0

    # Without title should attempt interactive (will fail in test env)
    result = runner.invoke(main, ["create"])
    # Will fail because no editor available in test env
    assert result.exit_code != 0


def test_create_invalid_priority(runner, temp_repo):
    """Test that create rejects invalid priority."""
    result = runner.invoke(main, ["create", "-p", "5", "Test"])

    # Should fail with usage error
    assert result.exit_code == 2
    assert "Invalid value" in result.output or "out of range" in result.output


def test_create_invalid_type(runner, temp_repo):
    """Test that create rejects invalid type."""
    result = runner.invoke(main, ["create", "-t", "invalid", "Test"])

    # Should fail with usage error
    assert result.exit_code == 2
    assert "Invalid value" in result.output or "invalid" in result.output


# ============================================================================
# Default Value Tests
# ============================================================================

def test_create_uses_config_defaults(runner, temp_repo):
    """Test that create uses default values from config."""
    result = runner.invoke(main, ["create", "Test ticket"])

    assert result.exit_code == 0
    ticket_id = result.output.strip()

    # Verify default values were applied
    result = runner.invoke(main, ["show", ticket_id])
    # Should have default type (task) and priority (2)
    assert "task" in result.output.lower()
    assert "priority: 2" in result.output.lower()


# ============================================================================
# Error Handling Tests
# ============================================================================

def test_create_fails_without_repo(runner):
    """Test that create fails when not in a repository."""
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["create", "Test"])

        assert result.exit_code == 1
        assert "Not in a bodega repository" in result.output


def test_create_with_empty_title_fails(runner, temp_repo):
    """Test that create with empty string as title fails."""
    result = runner.invoke(main, ["create", ""])

    # Should fail because title is empty
    assert result.exit_code != 0


# ============================================================================
# Output Format Tests
# ============================================================================

def test_create_outputs_only_id(runner, temp_repo):
    """Test that create outputs only the ticket ID."""
    result = runner.invoke(main, ["create", "Test ticket"])

    assert result.exit_code == 0
    output = result.output.strip()

    # Output should be just the ID
    assert output.startswith("bg-")
    assert len(output.split("\n")) == 1  # Single line


def test_create_id_can_be_used_immediately(runner, temp_repo):
    """Test that created ticket can be accessed immediately."""
    # Create ticket
    result = runner.invoke(main, ["create", "Test ticket"])
    ticket_id = result.output.strip()

    # Show ticket immediately
    result = runner.invoke(main, ["show", ticket_id])

    assert result.exit_code == 0
    assert "Test ticket" in result.output
