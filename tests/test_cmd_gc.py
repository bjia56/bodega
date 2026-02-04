"""Tests for gc command."""

import pytest
from datetime import timedelta

from bodega.cli import main
from bodega.models.ticket import Ticket, TicketStatus
from bodega.utils import now_utc, parse_duration
from bodega.errors import BodegaError, TicketNotFoundError


# ============================================================================
# Duration Parsing Tests
# ============================================================================

def test_parse_duration_days():
    """Test parsing days duration."""
    assert parse_duration("30d") == timedelta(days=30)
    assert parse_duration("7days") == timedelta(days=7)
    assert parse_duration("1d") == timedelta(days=1)


def test_parse_duration_hours():
    """Test parsing hours duration."""
    assert parse_duration("12h") == timedelta(hours=12)
    assert parse_duration("24hours") == timedelta(hours=24)
    assert parse_duration("1h") == timedelta(hours=1)


def test_parse_duration_minutes():
    """Test parsing minutes duration."""
    assert parse_duration("30m") == timedelta(minutes=30)
    assert parse_duration("45minutes") == timedelta(minutes=45)
    assert parse_duration("1m") == timedelta(minutes=1)


def test_parse_duration_case_insensitive():
    """Test that duration parsing is case-insensitive."""
    assert parse_duration("30D") == timedelta(days=30)
    assert parse_duration("12H") == timedelta(hours=12)
    assert parse_duration("30M") == timedelta(minutes=30)
    assert parse_duration("7DAYS") == timedelta(days=7)


def test_parse_duration_invalid_format():
    """Test that invalid duration format raises error."""
    with pytest.raises(BodegaError, match="Invalid duration format"):
        parse_duration("invalid")

    with pytest.raises(BodegaError, match="Invalid duration format"):
        parse_duration("30")

    with pytest.raises(BodegaError, match="Invalid duration format"):
        parse_duration("d30")

    with pytest.raises(BodegaError, match="Invalid duration format"):
        parse_duration("30x")


# ============================================================================
# GC Command Tests
# ============================================================================

def test_gc_no_tickets(runner, temp_repo):
    """Test gc with no tickets."""
    result = runner.invoke(main, ["gc"])
    assert result.exit_code == 0
    assert "No closed tickets" in result.output


def test_gc_dry_run(runner, storage):
    """Test gc with dry-run flag."""
    # Create old closed ticket
    old_ticket = Ticket(
        id="bg-old123",
        title="Old closed ticket",
        status=TicketStatus.CLOSED,
        created=now_utc() - timedelta(days=60),
        updated=now_utc() - timedelta(days=60)
    )
    storage.create(old_ticket, update_timestamp=False)

    # Create recent closed ticket
    recent_ticket = Ticket(
        id="bg-recent123",
        title="Recent closed ticket",
        status=TicketStatus.CLOSED,
        created=now_utc() - timedelta(days=10),
        updated=now_utc() - timedelta(days=10)
    )
    storage.create(recent_ticket, update_timestamp=False)

    # Run gc with dry-run
    result = runner.invoke(main, ["gc", "--dry-run"])
    assert result.exit_code == 0
    assert "bg-old123" in result.output
    assert "bg-recent123" not in result.output
    assert "would be deleted" in result.output

    # Verify tickets still exist
    assert storage.get("bg-old123")
    assert storage.get("bg-recent123")


def test_gc_deletes_old_tickets(runner, temp_repo, storage):
    """Test that gc deletes old closed tickets."""
    # Create old closed ticket
    old_ticket = Ticket(
        id="bg-old123",
        title="Old closed ticket",
        status=TicketStatus.CLOSED,
        created=now_utc() - timedelta(days=60),
        updated=now_utc() - timedelta(days=60)
    )
    storage.create(old_ticket, update_timestamp=False)

    # Create recent closed ticket
    recent_ticket = Ticket(
        id="bg-recent123",
        title="Recent closed ticket",
        status=TicketStatus.CLOSED,
        created=now_utc() - timedelta(days=10),
        updated=now_utc() - timedelta(days=10)
    )
    storage.create(recent_ticket, update_timestamp=False)

    # Create open ticket (should not be deleted regardless of age)
    open_ticket = Ticket(
        id="bg-open123",
        title="Old open ticket",
        status=TicketStatus.OPEN,
        created=now_utc() - timedelta(days=90),
        updated=now_utc() - timedelta(days=90)
    )
    storage.create(open_ticket, update_timestamp=False)

    # Run gc
    result = runner.invoke(main, ["gc"])
    assert result.exit_code == 0
    assert "Deleted 1 ticket(s)" in result.output

    # Verify old closed ticket was deleted
    with pytest.raises(TicketNotFoundError):
        storage.get("bg-old123")

    # Verify recent closed and open tickets still exist
    assert storage.get("bg-recent123")
    assert storage.get("bg-open123")


def test_gc_custom_age(runner, temp_repo, storage):
    """Test gc with custom age parameter."""
    # Create ticket closed 15 days ago
    ticket = Ticket(
        id="bg-test123",
        title="Test ticket",
        status=TicketStatus.CLOSED,
        created=now_utc() - timedelta(days=15),
        updated=now_utc() - timedelta(days=15)
    )
    storage.create(ticket, update_timestamp=False)

    # Should not be deleted with default 30d
    result = runner.invoke(main, ["gc"])
    assert result.exit_code == 0
    assert "No closed tickets" in result.output
    assert storage.get("bg-test123")

    # Should be deleted with 7d age
    result = runner.invoke(main, ["gc", "--age", "7d"])
    assert result.exit_code == 0
    assert "Deleted 1 ticket(s)" in result.output

    with pytest.raises(TicketNotFoundError):
        storage.get("bg-test123")


def test_gc_custom_age_hours(runner, temp_repo, storage):
    """Test gc with age specified in hours."""
    # Create ticket closed 25 hours ago
    ticket = Ticket(
        id="bg-test123",
        title="Test ticket",
        status=TicketStatus.CLOSED,
        created=now_utc() - timedelta(hours=25),
        updated=now_utc() - timedelta(hours=25)
    )
    storage.create(ticket, update_timestamp=False)

    # Should not be deleted with 48h age
    result = runner.invoke(main, ["gc", "--age", "48h"])
    assert result.exit_code == 0
    assert "No closed tickets" in result.output

    # Should be deleted with 12h age
    result = runner.invoke(main, ["gc", "--age", "12h"])
    assert result.exit_code == 0
    assert "Deleted 1 ticket(s)" in result.output


def test_gc_invalid_age_format(runner, temp_repo):
    """Test gc with invalid age format."""
    result = runner.invoke(main, ["gc", "--age", "invalid"])
    assert result.exit_code == 1
    assert "Invalid duration format" in result.output
