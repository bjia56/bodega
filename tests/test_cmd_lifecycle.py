"""Tests for lifecycle commands (start, close, reopen, status)."""

from bodega.cli import main


# ============================================================================
# Start Command Tests
# ============================================================================

def test_start_changes_status_to_in_progress(runner, temp_repo_with_ticket):
    """Test that start changes status to in-progress."""
    ticket_id = temp_repo_with_ticket

    result = runner.invoke(main, ["start", ticket_id])

    assert result.exit_code == 0
    assert "in-progress" in result.output
    assert ticket_id in result.output

    # Verify status changed
    result = runner.invoke(main, ["status", ticket_id])
    assert result.output.strip() == "in-progress"


def test_start_with_partial_id(runner, temp_repo_with_ticket):
    """Test that start works with partial ID."""
    ticket_id = temp_repo_with_ticket
    partial_id = ticket_id[:5]

    result = runner.invoke(main, ["start", partial_id])

    assert result.exit_code == 0
    assert "in-progress" in result.output


def test_start_already_in_progress(runner, temp_repo_with_ticket):
    """Test that starting an already in-progress ticket shows no-op message."""
    ticket_id = temp_repo_with_ticket

    # Start once
    runner.invoke(main, ["start", ticket_id])

    # Start again
    result = runner.invoke(main, ["start", ticket_id])

    assert result.exit_code == 0
    assert "already in-progress" in result.output
    assert ticket_id in result.output


def test_start_from_closed(runner, temp_repo_with_ticket):
    """Test that start works on closed tickets."""
    ticket_id = temp_repo_with_ticket

    # Close the ticket
    runner.invoke(main, ["close", ticket_id])

    # Start it
    result = runner.invoke(main, ["start", ticket_id])

    assert result.exit_code == 0
    assert "in-progress" in result.output

    # Verify status
    result = runner.invoke(main, ["status", ticket_id])
    assert result.output.strip() == "in-progress"


def test_start_not_found(runner, temp_repo):
    """Test that start fails for non-existent ticket."""
    result = runner.invoke(main, ["start", "bg-notfound"])

    assert result.exit_code == 1
    assert "Error" in result.output


def test_start_requires_id(runner, temp_repo):
    """Test that start requires a ticket ID."""
    result = runner.invoke(main, ["start"])

    assert result.exit_code == 2
    assert "Missing argument" in result.output


def test_start_fails_without_repo(runner):
    """Test that start fails when not in a repository."""
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["start", "bg-test"])

        assert result.exit_code == 1
        assert "Not in a bodega repository" in result.output


# ============================================================================
# Close Command Tests
# ============================================================================

def test_close_changes_status_to_closed(runner, temp_repo_with_ticket):
    """Test that close changes status to closed."""
    ticket_id = temp_repo_with_ticket

    result = runner.invoke(main, ["close", ticket_id])

    assert result.exit_code == 0
    assert "closed" in result.output
    assert ticket_id in result.output

    # Verify status changed
    result = runner.invoke(main, ["status", ticket_id])
    assert result.output.strip() == "closed"


def test_close_with_partial_id(runner, temp_repo_with_ticket):
    """Test that close works with partial ID."""
    ticket_id = temp_repo_with_ticket
    partial_id = ticket_id[:5]

    result = runner.invoke(main, ["close", partial_id])

    assert result.exit_code == 0
    assert "closed" in result.output


def test_close_already_closed(runner, temp_repo_with_ticket):
    """Test that closing an already closed ticket shows no-op message."""
    ticket_id = temp_repo_with_ticket

    # Close once
    runner.invoke(main, ["close", ticket_id])

    # Close again
    result = runner.invoke(main, ["close", ticket_id])

    assert result.exit_code == 0
    assert "already closed" in result.output
    assert ticket_id in result.output


def test_close_from_in_progress(runner, temp_repo_with_ticket):
    """Test that close works on in-progress tickets."""
    ticket_id = temp_repo_with_ticket

    # Start the ticket
    runner.invoke(main, ["start", ticket_id])

    # Close it
    result = runner.invoke(main, ["close", ticket_id])

    assert result.exit_code == 0
    assert "closed" in result.output

    # Verify status
    result = runner.invoke(main, ["status", ticket_id])
    assert result.output.strip() == "closed"


def test_close_not_found(runner, temp_repo):
    """Test that close fails for non-existent ticket."""
    result = runner.invoke(main, ["close", "bg-notfound"])

    assert result.exit_code == 1
    assert "Error" in result.output


def test_close_requires_id(runner, temp_repo):
    """Test that close requires a ticket ID."""
    result = runner.invoke(main, ["close"])

    assert result.exit_code == 2
    assert "Missing argument" in result.output


def test_close_fails_without_repo(runner):
    """Test that close fails when not in a repository."""
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["close", "bg-test"])

        assert result.exit_code == 1
        assert "Not in a bodega repository" in result.output


# ============================================================================
# Reopen Command Tests
# ============================================================================

def test_reopen_changes_status_to_open(runner, temp_repo_with_ticket):
    """Test that reopen changes status to open."""
    ticket_id = temp_repo_with_ticket

    # Close the ticket first
    runner.invoke(main, ["close", ticket_id])

    # Reopen it
    result = runner.invoke(main, ["reopen", ticket_id])

    assert result.exit_code == 0
    assert "open" in result.output
    assert ticket_id in result.output

    # Verify status changed
    result = runner.invoke(main, ["status", ticket_id])
    assert result.output.strip() == "open"


def test_reopen_with_partial_id(runner, temp_repo_with_ticket):
    """Test that reopen works with partial ID."""
    ticket_id = temp_repo_with_ticket
    partial_id = ticket_id[:5]

    # Close first
    runner.invoke(main, ["close", ticket_id])

    # Reopen with partial ID
    result = runner.invoke(main, ["reopen", partial_id])

    assert result.exit_code == 0
    assert "open" in result.output


def test_reopen_already_open(runner, temp_repo_with_ticket):
    """Test that reopening an already open ticket shows no-op message."""
    ticket_id = temp_repo_with_ticket

    # Ticket is already open by default
    result = runner.invoke(main, ["reopen", ticket_id])

    assert result.exit_code == 0
    assert "already open" in result.output
    assert ticket_id in result.output


def test_reopen_from_in_progress(runner, temp_repo_with_ticket):
    """Test that reopen works on in-progress tickets."""
    ticket_id = temp_repo_with_ticket

    # Start the ticket
    runner.invoke(main, ["start", ticket_id])

    # Reopen it
    result = runner.invoke(main, ["reopen", ticket_id])

    assert result.exit_code == 0
    assert "open" in result.output

    # Verify status
    result = runner.invoke(main, ["status", ticket_id])
    assert result.output.strip() == "open"


def test_reopen_not_found(runner, temp_repo):
    """Test that reopen fails for non-existent ticket."""
    result = runner.invoke(main, ["reopen", "bg-notfound"])

    assert result.exit_code == 1
    assert "Error" in result.output


def test_reopen_requires_id(runner, temp_repo):
    """Test that reopen requires a ticket ID."""
    result = runner.invoke(main, ["reopen"])

    assert result.exit_code == 2
    assert "Missing argument" in result.output


def test_reopen_fails_without_repo(runner):
    """Test that reopen fails when not in a repository."""
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["reopen", "bg-test"])

        assert result.exit_code == 1
        assert "Not in a bodega repository" in result.output


# ============================================================================
# Status Command Tests
# ============================================================================

def test_status_shows_open(runner, temp_repo_with_ticket):
    """Test that status shows open status."""
    ticket_id = temp_repo_with_ticket

    result = runner.invoke(main, ["status", ticket_id])

    assert result.exit_code == 0
    assert result.output.strip() == "open"


def test_status_shows_in_progress(runner, temp_repo_with_ticket):
    """Test that status shows in-progress status."""
    ticket_id = temp_repo_with_ticket

    # Start the ticket
    runner.invoke(main, ["start", ticket_id])

    result = runner.invoke(main, ["status", ticket_id])

    assert result.exit_code == 0
    assert result.output.strip() == "in-progress"


def test_status_shows_closed(runner, temp_repo_with_ticket):
    """Test that status shows closed status."""
    ticket_id = temp_repo_with_ticket

    # Close the ticket
    runner.invoke(main, ["close", ticket_id])

    result = runner.invoke(main, ["status", ticket_id])

    assert result.exit_code == 0
    assert result.output.strip() == "closed"


def test_status_with_partial_id(runner, temp_repo_with_ticket):
    """Test that status works with partial ID."""
    ticket_id = temp_repo_with_ticket
    partial_id = ticket_id[:5]

    result = runner.invoke(main, ["status", partial_id])

    assert result.exit_code == 0
    assert result.output.strip() in ["open", "in-progress", "closed"]


def test_status_not_found(runner, temp_repo):
    """Test that status fails for non-existent ticket."""
    result = runner.invoke(main, ["status", "bg-notfound"])

    assert result.exit_code == 1
    assert "Error" in result.output


def test_status_requires_id(runner, temp_repo):
    """Test that status requires a ticket ID."""
    result = runner.invoke(main, ["status"])

    assert result.exit_code == 2
    assert "Missing argument" in result.output


def test_status_fails_without_repo(runner):
    """Test that status fails when not in a repository."""
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["status", "bg-test"])

        assert result.exit_code == 1
        assert "Not in a bodega repository" in result.output


# ============================================================================
# Integration Tests
# ============================================================================

def test_lifecycle_full_workflow(runner, temp_repo_with_ticket):
    """Test full lifecycle: open → in-progress → closed → open."""
    ticket_id = temp_repo_with_ticket

    # Initial status should be open
    result = runner.invoke(main, ["status", ticket_id])
    assert result.output.strip() == "open"

    # Start working
    result = runner.invoke(main, ["start", ticket_id])
    assert result.exit_code == 0

    result = runner.invoke(main, ["status", ticket_id])
    assert result.output.strip() == "in-progress"

    # Close ticket
    result = runner.invoke(main, ["close", ticket_id])
    assert result.exit_code == 0

    result = runner.invoke(main, ["status", ticket_id])
    assert result.output.strip() == "closed"

    # Reopen ticket
    result = runner.invoke(main, ["reopen", ticket_id])
    assert result.exit_code == 0

    result = runner.invoke(main, ["status", ticket_id])
    assert result.output.strip() == "open"


def test_lifecycle_with_list_integration(runner, temp_repo):
    """Test that lifecycle changes are reflected in list command."""
    # Create a ticket
    result = runner.invoke(main, ["order", "Test ticket"])
    ticket_id = result.output.strip()

    # Should appear in list (open by default)
    result = runner.invoke(main, ["list", "-f", "ids"])
    assert ticket_id in result.output

    # Close it
    runner.invoke(main, ["close", ticket_id])

    # Should not appear in list (closed excluded by default)
    result = runner.invoke(main, ["list", "-f", "ids"])
    assert ticket_id not in result.output

    # Should appear with --all flag
    result = runner.invoke(main, ["list", "--all", "-f", "ids"])
    assert ticket_id in result.output


def test_lifecycle_updates_timestamp(runner, temp_repo_with_ticket):
    """Test that status changes update the timestamp."""
    ticket_id = temp_repo_with_ticket

    # Get initial state
    result = runner.invoke(main, ["show", "--json", ticket_id])
    import json
    initial_data = json.loads(result.output)
    initial_updated = initial_data["updated"]

    # Change status
    runner.invoke(main, ["start", ticket_id])

    # Get updated state
    result = runner.invoke(main, ["show", "--json", ticket_id])
    updated_data = json.loads(result.output)
    new_updated = updated_data["updated"]

    # Updated timestamp should have changed
    assert new_updated != initial_updated


def test_multiple_tickets_different_statuses(runner, temp_repo):
    """Test managing multiple tickets with different statuses."""
    # Create three tickets
    result = runner.invoke(main, ["order", "Ticket 1"])
    ticket1 = result.output.strip()

    result = runner.invoke(main, ["order", "Ticket 2"])
    ticket2 = result.output.strip()

    result = runner.invoke(main, ["order", "Ticket 3"])
    ticket3 = result.output.strip()

    # Set different statuses
    runner.invoke(main, ["start", ticket1])
    runner.invoke(main, ["close", ticket2])
    # ticket3 remains open

    # Verify each status
    result = runner.invoke(main, ["status", ticket1])
    assert result.output.strip() == "in-progress"

    result = runner.invoke(main, ["status", ticket2])
    assert result.output.strip() == "closed"

    result = runner.invoke(main, ["status", ticket3])
    assert result.output.strip() == "open"


def test_lifecycle_preserves_other_fields(runner, temp_repo):
    """Test that status changes don't affect other ticket fields."""
    # Create ticket with metadata
    result = runner.invoke(main, [
        "order",
        "-t", "bug",
        "-p", "1",
        "-a", "alice",
        "--tag", "urgent",
        "Test bug"
    ])
    ticket_id = result.output.strip()

    # Change status
    runner.invoke(main, ["start", ticket_id])

    # Verify metadata is preserved
    result = runner.invoke(main, ["show", "--json", ticket_id])
    import json
    data = json.loads(result.output)

    assert data["type"] == "bug"
    assert data["priority"] == 1
    assert data["assignee"] == "alice"
    assert "urgent" in data["tags"]
    assert data["title"] == "Test bug"
    assert data["status"] == "in-progress"
