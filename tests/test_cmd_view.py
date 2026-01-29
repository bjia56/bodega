"""Tests for view commands (show, edit, note)."""

import pytest
from pathlib import Path
import json
import os

from bodega.cli import main
from bodega.storage import TicketStorage
from bodega.models.ticket import Ticket, TicketType, TicketStatus


# ============================================================================
# Show Command Tests
# ============================================================================

def test_show_displays_ticket(runner, temp_repo_with_ticket):
    """Test that show displays ticket details."""
    ticket_id = temp_repo_with_ticket

    result = runner.invoke(main, ["show", ticket_id])

    assert result.exit_code == 0
    assert ticket_id in result.output
    assert "Test ticket" in result.output
    assert "Status:" in result.output
    assert "Type:" in result.output


def test_show_with_partial_id(runner, temp_repo_with_ticket):
    """Test that show works with partial ID."""
    ticket_id = temp_repo_with_ticket
    partial_id = ticket_id[:5]  # Use first 5 chars

    result = runner.invoke(main, ["show", partial_id])

    assert result.exit_code == 0
    assert ticket_id in result.output


def test_show_json_format(runner, temp_repo_with_ticket):
    """Test that show --json outputs valid JSON."""
    ticket_id = temp_repo_with_ticket

    result = runner.invoke(main, ["show", "--json", ticket_id])

    assert result.exit_code == 0

    # Parse JSON
    data = json.loads(result.output)
    assert data["id"] == ticket_id
    assert data["title"] == "Test ticket"
    assert data["type"] == "task"
    assert data["priority"] == 2


def test_show_raw_format(runner, temp_repo_with_ticket):
    """Test that show --raw outputs raw markdown."""
    ticket_id = temp_repo_with_ticket

    result = runner.invoke(main, ["show", "--raw", ticket_id])

    assert result.exit_code == 0
    # Should contain YAML frontmatter
    assert "---" in result.output
    assert "title: Test ticket" in result.output
    assert "type: task" in result.output


def test_show_displays_all_fields(runner, temp_repo_with_ticket):
    """Test that show displays all ticket fields."""
    ticket_id = temp_repo_with_ticket

    result = runner.invoke(main, ["show", ticket_id])

    assert result.exit_code == 0
    assert "task" in result.output.lower()
    assert "priority: 2" in result.output.lower()


def test_show_displays_description(runner, temp_repo_with_ticket):
    """Test that show displays description section."""
    ticket_id = temp_repo_with_ticket

    result = runner.invoke(main, ["show", ticket_id])

    assert result.exit_code == 0
    assert "Description" in result.output
    assert "Test description" in result.output


def test_show_not_found(runner, temp_repo):
    """Test that show fails for non-existent ticket."""
    result = runner.invoke(main, ["show", "bg-notfound"])

    assert result.exit_code == 1
    assert "Error" in result.output


def test_show_requires_id(runner, temp_repo):
    """Test that show requires a ticket ID."""
    result = runner.invoke(main, ["show"])

    assert result.exit_code == 2
    assert "Missing argument" in result.output


def test_show_fails_without_repo(runner):
    """Test that show fails when not in a repository."""
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["show", "bg-test"])

        assert result.exit_code == 1
        assert "Not in a bodega repository" in result.output


# ============================================================================
# Note Command Tests
# ============================================================================

def test_note_adds_note(runner, temp_repo_with_ticket):
    """Test that note adds a note to a ticket."""
    ticket_id = temp_repo_with_ticket

    result = runner.invoke(main, ["note", ticket_id, "This is a test note"])

    assert result.exit_code == 0
    assert "Added note" in result.output
    assert ticket_id in result.output


def test_note_appears_in_show(runner, temp_repo_with_ticket):
    """Test that added note appears when showing ticket."""
    ticket_id = temp_repo_with_ticket

    # Add note
    result = runner.invoke(main, ["note", ticket_id, "Test note content"])
    assert result.exit_code == 0

    # Show ticket
    result = runner.invoke(main, ["show", ticket_id])
    assert "Test note content" in result.output
    assert "Notes" in result.output


def test_note_appears_in_json(runner, temp_repo_with_ticket):
    """Test that added note appears in JSON output."""
    ticket_id = temp_repo_with_ticket

    # Add note
    result = runner.invoke(main, ["note", ticket_id, "JSON test note"])
    assert result.exit_code == 0

    # Get JSON
    result = runner.invoke(main, ["show", "--json", ticket_id])
    data = json.loads(result.output)

    assert any("JSON test note" in note for note in data["notes"])


def test_note_has_timestamp(runner, temp_repo_with_ticket):
    """Test that note includes timestamp."""
    ticket_id = temp_repo_with_ticket

    result = runner.invoke(main, ["note", ticket_id, "Timestamped note"])
    assert result.exit_code == 0

    # Show ticket
    result = runner.invoke(main, ["show", ticket_id])

    # Should contain a timestamp pattern (YYYY-MM-DD HH:MM)
    assert "Timestamped note" in result.output
    # Note should be in format: "YYYY-MM-DD HH:MM: Timestamped note"
    import re
    timestamp_pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:.*Timestamped note'
    assert re.search(timestamp_pattern, result.output)


def test_note_multiple_notes(runner, temp_repo_with_ticket):
    """Test adding multiple notes."""
    ticket_id = temp_repo_with_ticket

    # Add first note
    result = runner.invoke(main, ["note", ticket_id, "First note"])
    assert result.exit_code == 0

    # Add second note
    result = runner.invoke(main, ["note", ticket_id, "Second note"])
    assert result.exit_code == 0

    # Both should appear
    result = runner.invoke(main, ["show", "--json", ticket_id])
    data = json.loads(result.output)

    assert len(data["notes"]) >= 2
    note_texts = " ".join(data["notes"])
    assert "First note" in note_texts
    assert "Second note" in note_texts


def test_note_with_partial_id(runner, temp_repo_with_ticket):
    """Test that note works with partial ID."""
    ticket_id = temp_repo_with_ticket
    partial_id = ticket_id[:5]

    result = runner.invoke(main, ["note", partial_id, "Partial ID note"])

    assert result.exit_code == 0


def test_note_not_found(runner, temp_repo):
    """Test that note fails for non-existent ticket."""
    result = runner.invoke(main, ["note", "bg-notfound", "Test note"])

    assert result.exit_code == 1
    assert "Error" in result.output


def test_note_requires_text(runner, temp_repo_with_ticket):
    """Test that note requires text argument."""
    ticket_id = temp_repo_with_ticket

    result = runner.invoke(main, ["note", ticket_id])

    assert result.exit_code == 2
    assert "Missing argument" in result.output


def test_note_fails_without_repo(runner):
    """Test that note fails when not in a repository."""
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["note", "bg-test", "Test note"])

        assert result.exit_code == 1
        assert "Not in a bodega repository" in result.output


# ============================================================================
# Edit Command Tests
# ============================================================================

def test_edit_requires_id(runner, temp_repo):
    """Test that edit requires a ticket ID."""
    result = runner.invoke(main, ["edit"])

    assert result.exit_code == 2
    assert "Missing argument" in result.output


def test_edit_not_found(runner, temp_repo):
    """Test that edit fails for non-existent ticket."""
    # Set a mock editor that won't actually run
    result = runner.invoke(main, ["edit", "bg-notfound"])

    assert result.exit_code == 1
    assert "Error" in result.output


def test_edit_fails_without_repo(runner):
    """Test that edit fails when not in a repository."""
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["edit", "bg-test"])

        assert result.exit_code == 1
        assert "Not in a bodega repository" in result.output


# Note: Full edit command testing with actual editor is difficult in unit tests
# as it requires interactive editor. These tests cover the basic error cases.


# ============================================================================
# Integration Tests
# ============================================================================

def test_show_note_integration(runner, temp_repo):
    """Test full flow: create, note, show."""
    # Create ticket
    result = runner.invoke(main, ["create", "Integration test ticket"])
    ticket_id = result.output.strip()

    # Add note
    result = runner.invoke(main, ["note", ticket_id, "Integration note"])
    assert result.exit_code == 0

    # Show and verify
    result = runner.invoke(main, ["show", ticket_id])
    assert "Integration test ticket" in result.output
    assert "Integration note" in result.output


def test_json_output_serializable(runner, temp_repo_with_ticket):
    """Test that JSON output is fully serializable."""
    ticket_id = temp_repo_with_ticket

    # Add a note to test note serialization
    runner.invoke(main, ["note", ticket_id, "Serialization test"])

    result = runner.invoke(main, ["show", "--json", ticket_id])

    # Should be valid JSON
    data = json.loads(result.output)

    # Re-serialize to ensure all fields are JSON-serializable
    json_str = json.dumps(data)
    assert json_str is not None
    assert len(json_str) > 0


def test_raw_output_is_valid_markdown(runner, temp_repo_with_ticket):
    """Test that raw output is valid markdown with frontmatter."""
    ticket_id = temp_repo_with_ticket

    result = runner.invoke(main, ["show", "--raw", ticket_id])

    lines = result.output.split("\n")

    # Should start with frontmatter delimiter
    assert lines[0] == "---"

    # Should have closing frontmatter delimiter
    assert "---" in lines[1:]

    # Should contain required frontmatter fields
    output_text = result.output
    assert "id:" in output_text
    assert "title:" in output_text
    assert "type:" in output_text
    assert "status:" in output_text
