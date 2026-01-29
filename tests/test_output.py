"""Tests for output formatting module."""

import pytest
import json
import os

from bodega.output import (
    Colors,
    colorize,
    status_color,
    priority_color,
    type_color,
    format_table,
    format_compact,
    format_ids,
    format_json,
    format_ticket_detail,
    format_tickets,
    ticket_to_dict,
)
from bodega.models.ticket import Ticket, TicketStatus, TicketType
from bodega.config import BodegaConfig
from bodega.utils import now_utc


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_tickets():
    """Create sample tickets for testing."""
    return [
        Ticket(
            id="bg-abc123",
            title="Fix login bug",
            description="Users cannot log in",
            type=TicketType.BUG,
            status=TicketStatus.OPEN,
            priority=1,
            tags=["urgent"],
        ),
        Ticket(
            id="bg-def456",
            title="Add new feature",
            description="Implement dark mode",
            type=TicketType.FEATURE,
            status=TicketStatus.IN_PROGRESS,
            priority=2,
            assignee="alice",
        ),
        Ticket(
            id="bg-ghi789",
            title="Update documentation",
            type=TicketType.TASK,
            status=TicketStatus.CLOSED,
            priority=3,
        ),
    ]


@pytest.fixture
def config():
    """Create a default config for testing."""
    return BodegaConfig()


# ============================================================================
# Color Tests
# ============================================================================

def test_colors_enabled_with_tty(monkeypatch):
    """Test that colors are enabled when stdout is a TTY and NO_COLOR is not set."""
    # Mock isatty to return True
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    # Ensure NO_COLOR is not set
    monkeypatch.delenv("NO_COLOR", raising=False)

    assert Colors.enabled()


def test_colors_disabled_with_no_color(monkeypatch):
    """Test that colors are disabled when NO_COLOR is set."""
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    monkeypatch.setenv("NO_COLOR", "1")

    assert not Colors.enabled()


def test_colors_disabled_without_tty(monkeypatch):
    """Test that colors are disabled when stdout is not a TTY."""
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)
    monkeypatch.delenv("NO_COLOR", raising=False)

    assert not Colors.enabled()


def test_colorize_with_colors_enabled(monkeypatch):
    """Test colorize when colors are enabled."""
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    monkeypatch.delenv("NO_COLOR", raising=False)

    result = colorize("test", Colors.RED)
    assert result == f"{Colors.RED}test{Colors.RESET}"


def test_colorize_with_colors_disabled(monkeypatch):
    """Test colorize when colors are disabled."""
    monkeypatch.setenv("NO_COLOR", "1")

    result = colorize("test", Colors.RED)
    assert result == "test"


def test_status_color():
    """Test status color mapping."""
    assert status_color(TicketStatus.OPEN) == Colors.YELLOW
    assert status_color(TicketStatus.IN_PROGRESS) == Colors.BLUE
    assert status_color(TicketStatus.CLOSED) == Colors.GREEN


def test_priority_color():
    """Test priority color mapping."""
    assert priority_color(0) == Colors.RED + Colors.BOLD
    assert priority_color(1) == Colors.RED
    assert priority_color(2) == ""
    assert priority_color(3) == Colors.DIM
    assert priority_color(4) == Colors.DIM


def test_type_color():
    """Test type color mapping."""
    assert type_color(TicketType.BUG) == Colors.RED
    assert type_color(TicketType.FEATURE) == Colors.GREEN
    assert type_color(TicketType.TASK) == Colors.BLUE
    assert type_color(TicketType.EPIC) == Colors.MAGENTA
    assert type_color(TicketType.CHORE) == Colors.DIM


# ============================================================================
# Table Format Tests
# ============================================================================

def test_format_table_basic(sample_tickets, config, monkeypatch):
    """Test basic table formatting."""
    monkeypatch.setenv("NO_COLOR", "1")  # Disable colors for easier testing

    output = format_table(sample_tickets, config)

    # Check that all ticket IDs are present
    assert "bg-abc123" in output
    assert "bg-def456" in output
    assert "bg-ghi789" in output

    # Check that headers are present
    assert "ID" in output
    assert "TYPE" in output
    assert "STATUS" in output
    assert "TITLE" in output

    # Check that ticket data is present
    assert "bug" in output
    assert "feature" in output
    assert "Fix login bug" in output


def test_format_table_no_header(sample_tickets, config, monkeypatch):
    """Test table formatting without header."""
    monkeypatch.setenv("NO_COLOR", "1")

    output = format_table(sample_tickets, config, show_header=False)

    # Should not have header keywords at the start
    lines = output.split("\n")
    assert not lines[0].startswith("ID")


def test_format_table_empty(config):
    """Test table formatting with empty ticket list."""
    output = format_table([], config)
    assert "No tickets found" in output


def test_format_table_long_title(config, monkeypatch):
    """Test that long titles are truncated."""
    monkeypatch.setenv("NO_COLOR", "1")

    long_title = "A" * 100
    ticket = Ticket(
        id="bg-test",
        title=long_title,
        type=TicketType.TASK,
        status=TicketStatus.OPEN,
        priority=2,
    )

    output = format_table([ticket], config)

    # Title should be truncated with "..."
    assert "..." in output
    # Full title should not be present
    assert long_title not in output


# ============================================================================
# Compact Format Tests
# ============================================================================

def test_format_compact_basic(sample_tickets, config, monkeypatch):
    """Test compact formatting."""
    monkeypatch.setenv("NO_COLOR", "1")

    output = format_compact(sample_tickets, config)

    # Check format: ID [type/priority] Title
    assert "bg-abc123" in output
    assert "[bug/1]" in output
    assert "Fix login bug" in output

    assert "bg-def456" in output
    assert "[feature/2]" in output
    assert "Add new feature" in output


def test_format_compact_empty(config):
    """Test compact formatting with empty list."""
    output = format_compact([], config)
    assert "No tickets found" in output


# ============================================================================
# IDs Format Tests
# ============================================================================

def test_format_ids_basic(sample_tickets, config):
    """Test IDs-only formatting."""
    output = format_ids(sample_tickets, config)

    lines = output.split("\n")
    assert len(lines) == 3
    assert "bg-abc123" in lines
    assert "bg-def456" in lines
    assert "bg-ghi789" in lines


def test_format_ids_empty(config):
    """Test IDs formatting with empty list."""
    output = format_ids([], config)
    assert output == ""


# ============================================================================
# JSON Format Tests
# ============================================================================

def test_format_json_basic(sample_tickets, config):
    """Test JSON formatting."""
    output = format_json(sample_tickets, config)

    # Parse JSON to verify it's valid
    data = json.loads(output)

    assert len(data) == 3
    assert data[0]["id"] == "bg-abc123"
    assert data[0]["title"] == "Fix login bug"
    assert data[0]["type"] == "bug"
    assert data[0]["status"] == "open"
    assert data[0]["priority"] == 1


def test_format_json_pretty(sample_tickets, config):
    """Test pretty JSON formatting."""
    output = format_json(sample_tickets, config, pretty=True)

    # Pretty JSON should have indentation
    assert "  " in output or "\n" in output

    data = json.loads(output)
    assert len(data) == 3


def test_format_json_not_pretty(sample_tickets, config):
    """Test compact JSON formatting."""
    output = format_json(sample_tickets, config, pretty=False)

    # Should be valid JSON
    data = json.loads(output)
    assert len(data) == 3


def test_ticket_to_dict_complete():
    """Test ticket_to_dict with all fields populated."""
    now = now_utc()
    ticket = Ticket(
        id="bg-test",
        title="Test ticket",
        description="Test description",
        design="Test design",
        acceptance_criteria="Must work",
        notes=["Note 1", "Note 2"],
        type=TicketType.FEATURE,
        status=TicketStatus.IN_PROGRESS,
        priority=1,
        assignee="alice",
        tags=["tag1", "tag2"],
        deps=["bg-dep1"],
        links=["https://example.com"],
        parent="bg-parent",
        external_ref="JIRA-123",
        created=now,
        updated=now,
    )

    result = ticket_to_dict(ticket)

    assert result["id"] == "bg-test"
    assert result["title"] == "Test ticket"
    assert result["description"] == "Test description"
    assert result["design"] == "Test design"
    assert result["acceptance_criteria"] == "Must work"
    assert result["notes"] == ["Note 1", "Note 2"]
    assert result["type"] == "feature"
    assert result["status"] == "in-progress"
    assert result["priority"] == 1
    assert result["assignee"] == "alice"
    assert result["tags"] == ["tag1", "tag2"]
    assert result["deps"] == ["bg-dep1"]
    assert result["links"] == ["https://example.com"]
    assert result["parent"] == "bg-parent"
    assert result["external_ref"] == "JIRA-123"
    assert result["created"] == now.isoformat()
    assert result["updated"] == now.isoformat()


# ============================================================================
# Ticket Detail Format Tests
# ============================================================================

def test_format_ticket_detail_basic(config, monkeypatch):
    """Test detailed ticket formatting."""
    monkeypatch.setenv("NO_COLOR", "1")

    ticket = Ticket(
        id="bg-test",
        title="Test ticket",
        description="Test description",
        type=TicketType.BUG,
        status=TicketStatus.OPEN,
        priority=1,
        assignee="alice",
        tags=["urgent", "security"],
    )

    output = format_ticket_detail(ticket, config)

    # Check metadata
    assert "bg-test" in output
    assert "Test ticket" in output
    assert "Type:" in output
    assert "bug" in output
    assert "Status:" in output
    assert "open" in output
    assert "Priority: 1" in output
    assert "Assignee: alice" in output
    assert "Tags:" in output
    assert "urgent" in output

    # Check content
    assert "## Description" in output
    assert "Test description" in output


def test_format_ticket_detail_complete(config, monkeypatch):
    """Test detailed formatting with all fields."""
    monkeypatch.setenv("NO_COLOR", "1")

    ticket = Ticket(
        id="bg-complete",
        title="Complete ticket",
        description="Full description",
        design="Design notes",
        acceptance_criteria="Must pass all tests",
        notes=["Note 1", "Note 2"],
        type=TicketType.FEATURE,
        status=TicketStatus.IN_PROGRESS,
        priority=2,
        assignee="bob",
        tags=["frontend"],
        deps=["bg-dep1", "bg-dep2"],
        links=["https://example.com"],
        parent="bg-parent",
        external_ref="JIRA-456",
    )

    output = format_ticket_detail(ticket, config)

    # Check all sections are present
    assert "## Description" in output
    assert "Full description" in output
    assert "## Design" in output
    assert "Design notes" in output
    assert "## Acceptance Criteria" in output
    assert "Must pass all tests" in output
    assert "## Notes" in output
    assert "- Note 1" in output
    assert "- Note 2" in output

    # Check metadata
    assert "Blocked by: bg-dep1, bg-dep2" in output
    assert "Linked to:  https://example.com" in output
    assert "Parent:   bg-parent" in output
    assert "External: JIRA-456" in output


# ============================================================================
# Format Dispatcher Tests
# ============================================================================

def test_format_tickets_table(sample_tickets, config, monkeypatch):
    """Test format_tickets with table format."""
    monkeypatch.setenv("NO_COLOR", "1")

    output = format_tickets(sample_tickets, config, fmt="table")
    assert "ID" in output  # Header
    assert "bg-abc123" in output


def test_format_tickets_compact(sample_tickets, config, monkeypatch):
    """Test format_tickets with compact format."""
    monkeypatch.setenv("NO_COLOR", "1")

    output = format_tickets(sample_tickets, config, fmt="compact")
    assert "[bug/1]" in output


def test_format_tickets_ids(sample_tickets, config):
    """Test format_tickets with IDs format."""
    output = format_tickets(sample_tickets, config, fmt="ids")
    assert "bg-abc123" in output
    assert "bg-def456" in output


def test_format_tickets_json(sample_tickets, config):
    """Test format_tickets with JSON format."""
    output = format_tickets(sample_tickets, config, fmt="json")
    data = json.loads(output)
    assert len(data) == 3


def test_format_tickets_default_from_config(sample_tickets, monkeypatch):
    """Test that format_tickets uses config.list_format by default."""
    monkeypatch.setenv("NO_COLOR", "1")

    config = BodegaConfig(list_format="compact")
    output = format_tickets(sample_tickets, config)

    # Should use compact format
    assert "[bug/1]" in output


def test_format_tickets_invalid_format_defaults_to_table(sample_tickets, config, monkeypatch):
    """Test that invalid format defaults to table."""
    monkeypatch.setenv("NO_COLOR", "1")

    output = format_tickets(sample_tickets, config, fmt="invalid")

    # Should fall back to table format
    assert "ID" in output


# ============================================================================
# Integration Tests
# ============================================================================

def test_colors_in_output(sample_tickets, config, monkeypatch):
    """Test that colors are actually applied when enabled."""
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    monkeypatch.delenv("NO_COLOR", raising=False)

    output = format_table(sample_tickets, config)

    # Should contain ANSI escape codes
    assert "\033[" in output


def test_no_colors_in_output(sample_tickets, config, monkeypatch):
    """Test that no colors are applied when disabled."""
    monkeypatch.setenv("NO_COLOR", "1")

    output = format_table(sample_tickets, config)

    # Should not contain ANSI escape codes
    assert "\033[" not in output
