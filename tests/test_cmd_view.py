"""Tests for view commands (peek, adjust, note)."""

import pytest
from pathlib import Path
import json
import os

from bodega.cli import main
from bodega.storage import TicketStorage
from bodega.models.ticket import Ticket, TicketType, TicketStatus


# ============================================================================
# Peek Command Tests
# ============================================================================

def test_peek_displays_ticket(runner, temp_repo_with_ticket):
    """Test that peek displays ticket details."""
    ticket_id = temp_repo_with_ticket

    result = runner.invoke(main, ["peek", ticket_id])

    assert result.exit_code == 0
    assert ticket_id in result.output
    assert "Test ticket" in result.output
    assert "Status:" in result.output
    assert "Type:" in result.output


def test_peek_with_partial_id(runner, temp_repo_with_ticket):
    """Test that peek works with partial ID."""
    ticket_id = temp_repo_with_ticket
    partial_id = ticket_id[:5]  # Use first 5 chars

    result = runner.invoke(main, ["peek", partial_id])

    assert result.exit_code == 0
    assert ticket_id in result.output


def test_peek_json_format(runner, temp_repo_with_ticket):
    """Test that peek --json outputs valid JSON."""
    ticket_id = temp_repo_with_ticket

    result = runner.invoke(main, ["peek", "--json", ticket_id])

    assert result.exit_code == 0

    # Parse JSON
    data = json.loads(result.output)
    assert data["id"] == ticket_id
    assert data["title"] == "Test ticket"
    assert data["type"] == "task"
    assert data["priority"] == 2


def test_peek_raw_format(runner, temp_repo_with_ticket):
    """Test that peek --raw outputs raw markdown."""
    ticket_id = temp_repo_with_ticket

    result = runner.invoke(main, ["peek", "--raw", ticket_id])

    assert result.exit_code == 0
    # Should contain YAML frontmatter
    assert "---" in result.output
    assert "title: Test ticket" in result.output
    assert "type: task" in result.output


def test_peek_displays_all_fields(runner, temp_repo_with_ticket):
    """Test that peek displays all ticket fields."""
    ticket_id = temp_repo_with_ticket

    result = runner.invoke(main, ["peek", ticket_id])

    assert result.exit_code == 0
    assert "task" in result.output.lower()
    assert "priority: 2" in result.output.lower()


def test_peek_displays_description(runner, temp_repo_with_ticket):
    """Test that peek displays description section."""
    ticket_id = temp_repo_with_ticket

    result = runner.invoke(main, ["peek", ticket_id])

    assert result.exit_code == 0
    assert "Description" in result.output
    assert "Test description" in result.output


def test_peek_not_found(runner, temp_repo):
    """Test that peek fails for non-existent ticket."""
    result = runner.invoke(main, ["peek", "bg-notfound"])

    assert result.exit_code == 1
    assert "Error" in result.output


def test_peek_requires_id(runner, temp_repo):
    """Test that peek requires a ticket ID."""
    result = runner.invoke(main, ["peek"])

    assert result.exit_code == 2
    assert "Missing argument" in result.output


def test_peek_fails_without_repo(runner):
    """Test that peek fails when not in a repository."""
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["peek", "bg-test"])

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
    result = runner.invoke(main, ["peek", ticket_id])
    assert "Test note content" in result.output
    assert "Notes" in result.output


def test_note_appears_in_json(runner, temp_repo_with_ticket):
    """Test that added note appears in JSON output."""
    ticket_id = temp_repo_with_ticket

    # Add note
    result = runner.invoke(main, ["note", ticket_id, "JSON test note"])
    assert result.exit_code == 0

    # Get JSON
    result = runner.invoke(main, ["peek", "--json", ticket_id])
    data = json.loads(result.output)

    assert any("JSON test note" in note for note in data["notes"])


def test_note_has_timestamp(runner, temp_repo_with_ticket):
    """Test that note includes timestamp."""
    ticket_id = temp_repo_with_ticket

    result = runner.invoke(main, ["note", ticket_id, "Timestamped note"])
    assert result.exit_code == 0

    # Show ticket
    result = runner.invoke(main, ["peek", ticket_id])

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
    result = runner.invoke(main, ["peek", "--json", ticket_id])
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
# Adjust Command Tests
# ============================================================================

def test_adjust_requires_id(runner, temp_repo):
    """Test that adjust requires a ticket ID."""
    result = runner.invoke(main, ["adjust"])

    assert result.exit_code == 2
    assert "Missing argument" in result.output


def test_adjust_not_found(runner, temp_repo):
    """Test that adjust fails for non-existent ticket."""
    # Set a mock editor that won't actually run
    result = runner.invoke(main, ["adjust", "bg-notfound"])

    assert result.exit_code == 1
    assert "Error" in result.output


def test_adjust_fails_without_repo(runner):
    """Test that adjust fails when not in a repository."""
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["adjust", "bg-test"])

        assert result.exit_code == 1
        assert "Not in a bodega repository" in result.output


# Note: Full adjust command testing with actual editor is difficult in unit tests
# as it requires interactive editor. These tests cover the basic error cases.

def test_adjust_updates_title(runner, temp_repo_with_ticket):
    """Test that adjust --title updates ticket title."""
    ticket_id = temp_repo_with_ticket

    result = runner.invoke(main, ["adjust", ticket_id, "--title", "Updated title"])
    assert result.exit_code == 0
    assert "Updated" in result.output

    # Verify the change
    result = runner.invoke(main, ["peek", "--json", ticket_id])
    data = json.loads(result.output)
    assert data["title"] == "Updated title"


def test_adjust_updates_type(runner, temp_repo_with_ticket):
    """Test that adjust --type updates ticket type."""
    ticket_id = temp_repo_with_ticket

    result = runner.invoke(main, ["adjust", ticket_id, "--type", "bug"])
    assert result.exit_code == 0

    # Verify the change
    result = runner.invoke(main, ["peek", "--json", ticket_id])
    data = json.loads(result.output)
    assert data["type"] == "bug"


def test_adjust_updates_priority(runner, temp_repo_with_ticket):
    """Test that adjust --priority updates ticket priority."""
    ticket_id = temp_repo_with_ticket

    result = runner.invoke(main, ["adjust", ticket_id, "--priority", "1"])
    assert result.exit_code == 0

    # Verify the change
    result = runner.invoke(main, ["peek", "--json", ticket_id])
    data = json.loads(result.output)
    assert data["priority"] == 1


def test_adjust_updates_assignee(runner, temp_repo_with_ticket):
    """Test that adjust --assignee updates ticket assignee."""
    ticket_id = temp_repo_with_ticket

    result = runner.invoke(main, ["adjust", ticket_id, "--assignee", "John Doe"])
    assert result.exit_code == 0

    # Verify the change
    result = runner.invoke(main, ["peek", "--json", ticket_id])
    data = json.loads(result.output)
    assert data["assignee"] == "John Doe"


def test_adjust_adds_tags(runner, temp_repo_with_ticket):
    """Test that adjust --tag adds tags to ticket."""
    ticket_id = temp_repo_with_ticket

    result = runner.invoke(main, ["adjust", ticket_id, "--tag", "urgent", "--tag", "backend"])
    assert result.exit_code == 0

    # Verify the change
    result = runner.invoke(main, ["peek", "--json", ticket_id])
    data = json.loads(result.output)
    assert "urgent" in data["tags"]
    assert "backend" in data["tags"]


def test_adjust_removes_tags(runner, temp_repo_with_ticket):
    """Test that adjust --remove-tag removes tags from ticket."""
    ticket_id = temp_repo_with_ticket

    # First add some tags
    runner.invoke(main, ["adjust", ticket_id, "--tag", "urgent", "--tag", "backend"])

    # Then remove one
    result = runner.invoke(main, ["adjust", ticket_id, "--remove-tag", "urgent"])
    assert result.exit_code == 0

    # Verify the change
    result = runner.invoke(main, ["peek", "--json", ticket_id])
    data = json.loads(result.output)
    assert "urgent" not in data["tags"]
    assert "backend" in data["tags"]


def test_adjust_updates_description(runner, temp_repo_with_ticket):
    """Test that adjust --description updates ticket description."""
    ticket_id = temp_repo_with_ticket

    result = runner.invoke(main, ["adjust", ticket_id, "--description", "New description text"])
    assert result.exit_code == 0

    # Verify the change
    result = runner.invoke(main, ["peek", "--json", ticket_id])
    data = json.loads(result.output)
    assert data["description"] == "New description text"


def test_adjust_multiple_fields(runner, temp_repo_with_ticket):
    """Test that adjust can update multiple fields at once."""
    ticket_id = temp_repo_with_ticket

    result = runner.invoke(main, [
        "adjust", ticket_id,
        "--title", "Multi-update",
        "--type", "feature",
        "--priority", "0",
        "--tag", "critical"
    ])
    assert result.exit_code == 0

    # Verify all changes
    result = runner.invoke(main, ["peek", "--json", ticket_id])
    data = json.loads(result.output)
    assert data["title"] == "Multi-update"
    assert data["type"] == "feature"
    assert data["priority"] == 0
    assert "critical" in data["tags"]


def test_adjust_with_partial_id(runner, temp_repo_with_ticket):
    """Test that adjust works with partial ID."""
    ticket_id = temp_repo_with_ticket
    partial_id = ticket_id[:5]

    result = runner.invoke(main, ["adjust", partial_id, "--title", "Partial ID test"])
    assert result.exit_code == 0

    # Verify the change
    result = runner.invoke(main, ["peek", "--json", ticket_id])
    data = json.loads(result.output)
    assert data["title"] == "Partial ID test"


def test_adjust_duplicate_tag_not_added(runner, temp_repo_with_ticket):
    """Test that adding a duplicate tag doesn't create duplicates."""
    ticket_id = temp_repo_with_ticket

    # Add tag twice
    runner.invoke(main, ["adjust", ticket_id, "--tag", "urgent"])
    runner.invoke(main, ["adjust", ticket_id, "--tag", "urgent"])

    # Verify only one occurrence
    result = runner.invoke(main, ["peek", "--json", ticket_id])
    data = json.loads(result.output)
    assert data["tags"].count("urgent") == 1


# ============================================================================
# Integration Tests
# ============================================================================

def test_peek_note_integration(runner, temp_repo):
    """Test full flow: order, note, peek."""
    # Create ticket
    result = runner.invoke(main, ["order", "Integration test ticket"])
    ticket_id = result.output.strip()

    # Add note
    result = runner.invoke(main, ["note", ticket_id, "Integration note"])
    assert result.exit_code == 0

    # Show and verify
    result = runner.invoke(main, ["peek", ticket_id])
    assert "Integration test ticket" in result.output
    assert "Integration note" in result.output


def test_json_output_serializable(runner, temp_repo_with_ticket):
    """Test that JSON output is fully serializable."""
    ticket_id = temp_repo_with_ticket

    # Add a note to test note serialization
    runner.invoke(main, ["note", ticket_id, "Serialization test"])

    result = runner.invoke(main, ["peek", "--json", ticket_id])

    # Should be valid JSON
    data = json.loads(result.output)

    # Re-serialize to ensure all fields are JSON-serializable
    json_str = json.dumps(data)
    assert json_str is not None
    assert len(json_str) > 0


def test_raw_output_is_valid_markdown(runner, temp_repo_with_ticket):
    """Test that raw output is valid markdown with frontmatter."""
    ticket_id = temp_repo_with_ticket

    result = runner.invoke(main, ["peek", "--raw", ticket_id])

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
