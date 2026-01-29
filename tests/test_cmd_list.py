"""Tests for list commands (list, ready, blocked, closed, query)."""

import pytest
from click.testing import CliRunner
from pathlib import Path
import json

from bodega.cli import main
from bodega.storage import init_repository


@pytest.fixture
def runner():
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_repo(runner):
    """Create a temporary repository for testing."""
    with runner.isolated_filesystem():
        init_repository()
        yield


@pytest.fixture
def temp_repo_with_tickets(runner):
    """Create a temporary repository with multiple test tickets."""
    with runner.isolated_filesystem():
        init_repository()

        # Create tickets of different types and priorities
        tickets = []

        # Bug with high priority
        result = runner.invoke(main, [
            "create", "-t", "bug", "-p", "1", "--tag", "urgent",
            "Critical bug"
        ])
        tickets.append(result.output.strip())

        # Feature with normal priority
        result = runner.invoke(main, [
            "create", "-t", "feature", "-p", "2", "--tag", "api",
            "New feature"
        ])
        tickets.append(result.output.strip())

        # Task with low priority
        result = runner.invoke(main, [
            "create", "-t", "task", "-p", "3",
            "Regular task"
        ])
        tickets.append(result.output.strip())

        yield tickets


# ============================================================================
# List Command Tests
# ============================================================================

def test_list_default(runner, temp_repo_with_tickets):
    """Test that list shows open tickets by default."""
    result = runner.invoke(main, ["list"])

    assert result.exit_code == 0
    assert "bg-" in result.output


def test_list_includes_all_open_tickets(runner, temp_repo_with_tickets):
    """Test that list shows all open tickets."""
    tickets = temp_repo_with_tickets
    result = runner.invoke(main, ["list"])

    assert result.exit_code == 0
    # All three tickets should appear
    for ticket_id in tickets:
        # The ID might be truncated in compact format, check first few chars
        assert ticket_id[:8] in result.output


def test_list_excludes_closed_by_default(runner, temp_repo_with_tickets):
    """Test that list excludes closed tickets by default."""
    tickets = temp_repo_with_tickets

    # Close one ticket
    runner.invoke(main, ["close", tickets[0]])

    result = runner.invoke(main, ["list"])

    assert result.exit_code == 0
    # Closed ticket should not appear
    # Other tickets should still appear
    assert tickets[1][:8] in result.output
    assert tickets[2][:8] in result.output


def test_list_with_all_flag(runner, temp_repo_with_tickets):
    """Test that list --all includes closed tickets."""
    tickets = temp_repo_with_tickets

    # Close one ticket
    runner.invoke(main, ["close", tickets[0]])

    result = runner.invoke(main, ["list", "--all"])

    assert result.exit_code == 0
    # All tickets including closed should appear
    for ticket_id in tickets:
        assert ticket_id[:8] in result.output


def test_list_filter_by_status(runner, temp_repo_with_tickets):
    """Test filtering by status."""
    tickets = temp_repo_with_tickets

    # Start working on one ticket
    runner.invoke(main, ["start", tickets[0]])

    result = runner.invoke(main, ["list", "-s", "in-progress"])

    assert result.exit_code == 0
    assert tickets[0][:8] in result.output


def test_list_filter_by_type(runner, temp_repo_with_tickets):
    """Test filtering by type."""
    result = runner.invoke(main, ["list", "-t", "bug"])

    assert result.exit_code == 0
    assert "bug" in result.output.lower()


def test_list_filter_by_tag(runner, temp_repo_with_tickets):
    """Test filtering by tag."""
    tickets = temp_repo_with_tickets

    result = runner.invoke(main, ["list", "--tag", "urgent"])

    assert result.exit_code == 0
    assert tickets[0][:8] in result.output.lower()


def test_list_filter_by_priority(runner, temp_repo_with_tickets):
    """Test filtering by priority."""
    tickets = temp_repo_with_tickets

    result = runner.invoke(main, ["list", "-p", "1"])

    assert result.exit_code == 0
    # Should show the bug ticket (priority 1)
    assert tickets[0][:8] in result.output
    # Should not show priority 2 or 3 tickets
    assert tickets[1][:8] not in result.output
    assert tickets[2][:8] not in result.output


def test_list_filter_by_assignee(runner, temp_repo):
    """Test filtering by assignee."""
    # Create ticket with assignee
    runner.invoke(main, ["create", "-a", "alice", "Alice's ticket"])

    result = runner.invoke(main, ["list", "--assignee", "alice"])

    assert result.exit_code == 0
    assert "alice" in result.output.lower()


def test_list_combined_filters(runner, temp_repo_with_tickets):
    """Test combining multiple filters."""
    tickets = temp_repo_with_tickets

    result = runner.invoke(main, [
        "list",
        "-t", "bug",
        "-p", "1",
        "--tag", "urgent"
    ])

    assert result.exit_code == 0
    # Should show the bug ticket (matches all filters)
    assert tickets[0][:8] in result.output
    # Should not show other tickets
    assert tickets[1][:8] not in result.output


def test_list_sort_by_priority(runner, temp_repo_with_tickets):
    """Test sorting by priority (default)."""
    tickets = temp_repo_with_tickets

    result = runner.invoke(main, ["list", "-f", "ids"])

    assert result.exit_code == 0
    # Get order of IDs
    ids = result.output.strip().split("\n")
    # Priority 1 (tickets[0]) should appear before priority 2 (tickets[1])
    # and priority 2 before priority 3 (tickets[2])
    assert ids.index(tickets[0]) < ids.index(tickets[1])
    assert ids.index(tickets[1]) < ids.index(tickets[2])


def test_list_sort_by_created(runner, temp_repo_with_tickets):
    """Test sorting by created date."""
    tickets = temp_repo_with_tickets

    result = runner.invoke(main, ["list", "--sort", "created", "-f", "ids"])

    assert result.exit_code == 0
    # Should have all tickets in the output
    for ticket_id in tickets:
        assert ticket_id in result.output


def test_list_sort_by_updated(runner, temp_repo_with_tickets):
    """Test sorting by updated date."""
    tickets = temp_repo_with_tickets

    result = runner.invoke(main, ["list", "--sort", "updated", "-f", "ids"])

    assert result.exit_code == 0
    # Should have all tickets in the output
    for ticket_id in tickets:
        assert ticket_id in result.output


def test_list_reverse_sort(runner, temp_repo_with_tickets):
    """Test reverse sorting."""
    tickets = temp_repo_with_tickets

    result = runner.invoke(main, ["list", "--reverse", "-f", "ids"])

    assert result.exit_code == 0
    # Get order of IDs
    ids = result.output.strip().split("\n")
    # With reverse, priority 3 should appear before priority 1
    assert ids.index(tickets[2]) < ids.index(tickets[0])


def test_list_format_table(runner, temp_repo_with_tickets):
    """Test table format output."""
    result = runner.invoke(main, ["list", "-f", "table"])

    assert result.exit_code == 0
    # Table format should have headers
    assert "TYPE" in result.output or "Status" in result.output or "ID" in result.output


def test_list_format_compact(runner, temp_repo_with_tickets):
    """Test compact format output."""
    tickets = temp_repo_with_tickets

    result = runner.invoke(main, ["list", "-f", "compact"])

    assert result.exit_code == 0
    # Compact format should have ticket IDs and brackets for type/priority
    assert tickets[0][:8] in result.output
    assert "[" in result.output and "]" in result.output


def test_list_format_ids(runner, temp_repo_with_tickets):
    """Test IDs only format."""
    result = runner.invoke(main, ["list", "-f", "ids"])

    assert result.exit_code == 0
    # Should only have IDs, one per line
    lines = result.output.strip().split("\n")
    for line in lines:
        if line:
            assert line.startswith("bg-")


def test_list_empty_repo(runner, temp_repo):
    """Test list with no tickets."""
    result = runner.invoke(main, ["list"])

    assert result.exit_code == 0
    assert "No tickets" in result.output or result.output.strip() == ""


def test_list_fails_without_repo(runner):
    """Test that list fails when not in a repository."""
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["list"])

        assert result.exit_code == 1
        assert "Not in a bodega repository" in result.output


# ============================================================================
# Ready Command Tests
# ============================================================================

def test_ready_shows_unblocked_tickets(runner, temp_repo_with_tickets):
    """Test that ready shows tickets without dependencies."""
    tickets = temp_repo_with_tickets

    result = runner.invoke(main, ["ready"])

    assert result.exit_code == 0
    # All tickets without deps should appear (all three in this fixture)
    for ticket_id in tickets:
        assert ticket_id[:8] in result.output


def test_ready_excludes_blocked_tickets(runner, temp_repo):
    """Test that ready excludes tickets with open dependencies."""
    # Create blocker ticket
    result = runner.invoke(main, ["create", "Blocker ticket"])
    blocker_id = result.output.strip()

    # Create blocked ticket
    result = runner.invoke(main, ["create", "-d", blocker_id, "Blocked ticket"])
    blocked_id = result.output.strip()

    result = runner.invoke(main, ["ready"])

    assert result.exit_code == 0
    # Blocker should appear
    assert blocker_id[:8] in result.output
    # Blocked ticket should NOT appear
    assert blocked_id[:8] not in result.output


def test_ready_includes_tickets_with_closed_deps(runner, temp_repo):
    """Test that ready includes tickets whose deps are closed."""
    # Create blocker ticket
    result = runner.invoke(main, ["create", "Blocker ticket"])
    blocker_id = result.output.strip()

    # Create blocked ticket
    result = runner.invoke(main, ["create", "-d", blocker_id, "Blocked ticket"])
    blocked_id = result.output.strip()

    # Close the blocker
    runner.invoke(main, ["close", blocker_id])

    result = runner.invoke(main, ["ready"])

    assert result.exit_code == 0
    # Now the previously blocked ticket should be ready
    assert blocked_id[:8] in result.output


def test_ready_fails_without_repo(runner):
    """Test that ready fails when not in a repository."""
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["ready"])

        assert result.exit_code == 1
        assert "Not in a bodega repository" in result.output


# ============================================================================
# Blocked Command Tests
# ============================================================================

def test_blocked_shows_blocked_tickets(runner, temp_repo):
    """Test that blocked shows tickets with open dependencies."""
    # Create blocker ticket
    result = runner.invoke(main, ["create", "Blocker ticket"])
    blocker_id = result.output.strip()

    # Create blocked ticket
    result = runner.invoke(main, ["create", "-d", blocker_id, "Blocked ticket"])
    blocked_id = result.output.strip()

    result = runner.invoke(main, ["blocked"])

    assert result.exit_code == 0
    assert blocked_id[:8] in result.output
    assert "Blocked by:" in result.output
    assert blocker_id in result.output


def test_blocked_shows_blocker_ids(runner, temp_repo):
    """Test that blocked shows which tickets are blocking."""
    # Create two blocker tickets
    result = runner.invoke(main, ["create", "Blocker 1"])
    blocker1 = result.output.strip()

    result = runner.invoke(main, ["create", "Blocker 2"])
    blocker2 = result.output.strip()

    # Create ticket blocked by both
    result = runner.invoke(main, [
        "create", "-d", blocker1, "-d", blocker2, "Blocked ticket"
    ])

    result = runner.invoke(main, ["blocked"])

    assert result.exit_code == 0
    assert "Blocked by:" in result.output
    assert blocker1 in result.output
    assert blocker2 in result.output


def test_blocked_empty_message(runner, temp_repo_with_tickets):
    """Test that blocked shows message when no blocked tickets."""
    result = runner.invoke(main, ["blocked"])

    assert result.exit_code == 0
    assert "No blocked tickets" in result.output


def test_blocked_excludes_closed_blockers(runner, temp_repo):
    """Test that blocked doesn't show tickets whose deps are closed."""
    # Create blocker ticket
    result = runner.invoke(main, ["create", "Blocker ticket"])
    blocker_id = result.output.strip()

    # Create blocked ticket
    result = runner.invoke(main, ["create", "-d", blocker_id, "Blocked ticket"])
    blocked_id = result.output.strip()

    # Close the blocker
    runner.invoke(main, ["close", blocker_id])

    result = runner.invoke(main, ["blocked"])

    assert result.exit_code == 0
    # Blocked ticket should not appear since blocker is closed
    assert "No blocked tickets" in result.output


def test_blocked_fails_without_repo(runner):
    """Test that blocked fails when not in a repository."""
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["blocked"])

        assert result.exit_code == 1
        assert "Not in a bodega repository" in result.output


# ============================================================================
# Closed Command Tests
# ============================================================================

def test_closed_shows_closed_tickets(runner, temp_repo_with_tickets):
    """Test that closed shows recently closed tickets."""
    tickets = temp_repo_with_tickets

    # Close some tickets
    runner.invoke(main, ["close", tickets[0]])
    runner.invoke(main, ["close", tickets[1]])

    result = runner.invoke(main, ["closed"])

    assert result.exit_code == 0
    assert tickets[0][:8] in result.output or tickets[1][:8] in result.output


def test_closed_default_count(runner, temp_repo):
    """Test that closed shows default 10 tickets."""
    # Create and close 15 tickets
    ticket_ids = []
    for i in range(15):
        result = runner.invoke(main, ["create", f"Ticket {i}"])
        ticket_id = result.output.strip()
        ticket_ids.append(ticket_id)
        runner.invoke(main, ["close", ticket_id])

    result = runner.invoke(main, ["closed"])

    assert result.exit_code == 0
    # Should show up to 10 tickets
    # Remove headers
    output = result.output.strip().split("\n")
    lines = [line for line in output[1:] if line]
    assert len(lines) <= 10


def test_closed_custom_count(runner, temp_repo_with_tickets):
    """Test closed with custom count."""
    tickets = temp_repo_with_tickets

    # Close all tickets
    for ticket_id in tickets:
        runner.invoke(main, ["close", ticket_id])

    result = runner.invoke(main, ["closed", "-n", "2"])

    assert result.exit_code == 0
    # Should show exactly 2 tickets
    output = result.output.strip().split("\n")
    lines = [line for line in output[1:] if line]
    assert len(lines) == 2


def test_closed_most_recent_first(runner, temp_repo):
    """Test that closed shows most recently closed first."""
    # Create and close tickets
    result = runner.invoke(main, ["create", "First closed"])
    first_id = result.output.strip()
    runner.invoke(main, ["close", first_id])

    result = runner.invoke(main, ["create", "Second closed"])
    second_id = result.output.strip()
    runner.invoke(main, ["close", second_id])

    result = runner.invoke(main, ["closed"])

    assert result.exit_code == 0
    # Both should appear, with second (most recent) first
    output = result.output.strip().split("\n")
    ids = [line for line in output[1:] if line]
    assert any(second_id in id for id in ids)
    assert any(first_id in id for id in ids)
    # Second should appear before first
    first_idx = ids.index(next(id for id in ids if first_id in id))
    second_idx = ids.index(next(id for id in ids if second_id in id))
    assert second_idx < first_idx


def test_closed_fails_without_repo(runner):
    """Test that closed fails when not in a repository."""
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["closed"])

        assert result.exit_code == 1
        assert "Not in a bodega repository" in result.output


# ============================================================================
# Query Command Tests
# ============================================================================

def test_query_outputs_json(runner, temp_repo_with_tickets):
    """Test that query outputs valid JSON."""
    result = runner.invoke(main, ["query"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)


def test_query_includes_all_fields(runner, temp_repo_with_tickets):
    """Test that query JSON includes all ticket fields."""
    result = runner.invoke(main, ["query"])

    data = json.loads(result.output)
    if data:
        ticket = data[0]
        assert "id" in ticket
        assert "title" in ticket
        assert "type" in ticket
        assert "status" in ticket
        assert "priority" in ticket


def test_query_with_filters(runner, temp_repo_with_tickets):
    """Test that query respects filters."""
    result = runner.invoke(main, ["query", "-t", "bug"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    # All results should be bugs
    for ticket in data:
        assert ticket["type"] == "bug"


def test_query_single_ticket_by_id(runner, temp_repo_with_tickets):
    """Test querying a single ticket by ID."""
    tickets = temp_repo_with_tickets
    ticket_id = tickets[0]

    result = runner.invoke(main, ["query", "--id", ticket_id])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, dict)  # Single ticket, not array
    assert data["id"] == ticket_id


def test_query_all_flag(runner, temp_repo_with_tickets):
    """Test query --all includes closed tickets."""
    tickets = temp_repo_with_tickets

    # Close one ticket
    runner.invoke(main, ["close", tickets[0]])

    result = runner.invoke(main, ["query", "--all"])

    data = json.loads(result.output)
    # Should include the closed ticket
    assert len(data) == len(tickets)


def test_query_pretty_print(runner, temp_repo_with_tickets):
    """Test query with pretty printing."""
    result = runner.invoke(main, ["query", "--pretty"])

    assert result.exit_code == 0
    # Pretty printed JSON should have indentation
    assert "  " in result.output or "\n" in result.output


def test_query_no_pretty(runner, temp_repo_with_tickets):
    """Test query without pretty printing."""
    result = runner.invoke(main, ["query", "--no-pretty"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    # Should still be valid JSON, just compact


def test_query_pipeable(runner, temp_repo_with_tickets):
    """Test that query output can be piped."""
    result = runner.invoke(main, ["query", "--no-pretty"])

    assert result.exit_code == 0
    # Output should be single-line JSON array for piping
    data = json.loads(result.output)
    assert isinstance(data, list)


def test_query_not_found_id(runner, temp_repo):
    """Test query with non-existent ID."""
    result = runner.invoke(main, ["query", "--id", "bg-notfound"])

    assert result.exit_code == 1
    assert "Error" in result.output


def test_query_fails_without_repo(runner):
    """Test that query fails when not in a repository."""
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["query"])

        assert result.exit_code == 1
        assert "Not in a bodega repository" in result.output


# ============================================================================
# Integration Tests
# ============================================================================

def test_list_ready_blocked_integration(runner, temp_repo):
    """Test integration of list, ready, and blocked commands."""
    # Create a dependency chain
    result = runner.invoke(main, ["create", "Root task"])
    root_id = result.output.strip()

    result = runner.invoke(main, ["create", "-d", root_id, "Dependent task"])
    dep_id = result.output.strip()

    # ready should show only root
    result = runner.invoke(main, ["ready"])
    assert root_id[:8] in result.output
    assert dep_id[:8] not in result.output

    # blocked should show dependent
    result = runner.invoke(main, ["blocked"])
    assert dep_id[:8] in result.output
    assert "Blocked by:" in result.output

    # Close root
    runner.invoke(main, ["close", root_id])

    # Now ready should show dependent (since root is closed)
    result = runner.invoke(main, ["ready"])
    assert dep_id[:8] in result.output

    # blocked should be empty
    result = runner.invoke(main, ["blocked"])
    assert "No blocked tickets" in result.output


def test_list_query_consistency(runner, temp_repo_with_tickets):
    """Test that list and query show consistent data."""
    # Get IDs from list
    result = runner.invoke(main, ["list", "-f", "ids"])
    list_ids = set(result.output.strip().split("\n"))

    # Get IDs from query
    result = runner.invoke(main, ["query"])
    data = json.loads(result.output)
    query_ids = {ticket["id"] for ticket in data}

    # Should match
    assert list_ids == query_ids
