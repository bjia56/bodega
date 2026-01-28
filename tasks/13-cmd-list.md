# Task 13: List Commands

## Summary
Implement listing and query commands: `list`, `ready`, `blocked`, `closed`, and `query`.

## Dependencies
- Task 01: Project Setup
- Task 02: Models (Ticket, TicketStatus)
- Task 05: Storage (TicketStorage)
- Task 06: Output (format_tickets, format_json)
- Task 07: Graph (DependencyGraph)
- Task 08: CLI Base

## Requirements

### 1. List Commands (`src/bodega/commands/list_cmd.py`)

Note: File named `list_cmd.py` because `list` is a Python reserved word.

```python
import click
import json

from ..cli import pass_context, Context, require_repo
from ..models import TicketStatus
from ..output import format_tickets, format_json, ticket_to_dict
from ..graph import DependencyGraph

@click.command("list")
@click.option("--all", "-a", "include_all", is_flag=True,
              help="Include closed tickets")
@click.option("--status", "-s",
              type=click.Choice(["open", "in-progress", "closed"]),
              help="Filter by status")
@click.option("--type", "-t", "ticket_type",
              type=click.Choice(["bug", "feature", "task", "epic", "chore"]),
              help="Filter by type")
@click.option("--tag", help="Filter by tag")
@click.option("--assignee", help="Filter by assignee")
@click.option("--priority", "-p", type=click.IntRange(0, 4),
              help="Filter by priority")
@click.option("--sort",
              type=click.Choice(["priority", "created", "updated"]),
              default="priority", help="Sort by field")
@click.option("--reverse", "-r", is_flag=True, help="Reverse sort order")
@click.option("--format", "-f", "fmt",
              type=click.Choice(["table", "compact", "ids"]),
              help="Output format")
@pass_context
def list_tickets(
    ctx: Context,
    include_all: bool,
    status: str | None,
    ticket_type: str | None,
    tag: str | None,
    assignee: str | None,
    priority: int | None,
    sort: str,
    reverse: bool,
    fmt: str | None,
):
    """
    List tickets with optional filters.

    By default, shows only open and in-progress tickets.

    Examples:

        bodega list                      # All open tickets

        bodega list --all                # Include closed

        bodega list -s in-progress       # Filter by status

        bodega list -t bug --tag urgent  # Combined filters

        bodega list --sort created -r    # Sort by created, newest first
    """
    storage = require_repo(ctx)

    # Parse status filter
    status_filter = None
    if status:
        status_filter = TicketStatus(status)

    # Query tickets
    tickets = list(storage.query(
        status=status_filter,
        ticket_type=ticket_type,
        tag=tag,
        assignee=assignee,
        priority=priority,
        include_closed=include_all,
    ))

    # Sort
    sort_key = {
        "priority": lambda t: (t.priority, t.created),
        "created": lambda t: t.created,
        "updated": lambda t: t.updated,
    }[sort]

    tickets.sort(key=sort_key, reverse=reverse)

    # Format and output
    output = format_tickets(tickets, ctx.config, fmt)
    click.echo(output)


@click.command()
@pass_context
def ready(ctx: Context):
    """
    List tickets that are ready to work on.

    Shows open tickets with no unresolved dependencies.

    Examples:

        bodega ready
    """
    storage = require_repo(ctx)
    graph = DependencyGraph(storage)

    tickets = graph.get_ready_tickets()
    tickets.sort(key=lambda t: (t.priority, t.created))

    output = format_tickets(tickets, ctx.config)
    click.echo(output)


@click.command()
@pass_context
def blocked(ctx: Context):
    """
    List tickets that are blocked by dependencies.

    Shows open tickets waiting on other tickets to close.

    Examples:

        bodega blocked
    """
    storage = require_repo(ctx)
    graph = DependencyGraph(storage)

    tickets = graph.get_blocked_tickets()
    tickets.sort(key=lambda t: (t.priority, t.created))

    if not tickets:
        click.echo("No blocked tickets.")
        return

    # Show blockers for each ticket
    for ticket in tickets:
        blockers = graph.get_blockers(ticket.id)
        blocker_str = ", ".join(blockers)
        click.echo(f"{ticket.id} [{ticket.type.value}/{ticket.priority}] {ticket.title}")
        click.echo(f"  Blocked by: {blocker_str}")


@click.command()
@click.option("--count", "-n", default=10, help="Number of tickets to show")
@pass_context
def closed(ctx: Context, count: int):
    """
    List recently closed tickets.

    Examples:

        bodega closed         # Last 10 closed

        bodega closed -n 20   # Last 20 closed
    """
    storage = require_repo(ctx)

    tickets = list(storage.query(
        status=TicketStatus.CLOSED,
        include_closed=True,
    ))

    # Sort by updated (most recently closed first)
    tickets.sort(key=lambda t: t.updated, reverse=True)
    tickets = tickets[:count]

    output = format_tickets(tickets, ctx.config)
    click.echo(output)


@click.command()
@click.option("--all", "-a", "include_all", is_flag=True,
              help="Include closed tickets")
@click.option("--status", "-s",
              type=click.Choice(["open", "in-progress", "closed"]),
              help="Filter by status")
@click.option("--type", "-t", "ticket_type",
              type=click.Choice(["bug", "feature", "task", "epic", "chore"]),
              help="Filter by type")
@click.option("--tag", help="Filter by tag")
@click.option("--assignee", help="Filter by assignee")
@click.option("--priority", "-p", type=click.IntRange(0, 4),
              help="Filter by priority")
@click.option("--id", "ticket_id", help="Query single ticket by ID")
@click.option("--pretty/--no-pretty", default=None,
              help="Pretty-print JSON")
@pass_context
def query(
    ctx: Context,
    include_all: bool,
    status: str | None,
    ticket_type: str | None,
    tag: str | None,
    assignee: str | None,
    priority: int | None,
    ticket_id: str | None,
    pretty: bool | None,
):
    """
    Output tickets as JSON for scripting.

    Examples:

        bodega query                           # All open as JSON

        bodega query --all                     # All tickets

        bodega query --id bg-a1b2c3            # Single ticket

        bodega query | jq '.[].title'          # Pipe to jq

        bodega query --no-pretty               # Compact JSON
    """
    import sys

    storage = require_repo(ctx)

    # Default pretty to True if stdout is a TTY
    if pretty is None:
        pretty = sys.stdout.isatty()

    if ticket_id:
        # Single ticket query
        try:
            ticket = storage.get(ticket_id)
            data = ticket_to_dict(ticket)
            if pretty:
                click.echo(json.dumps(data, indent=2, default=str))
            else:
                click.echo(json.dumps(data, default=str))
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1)
        return

    # Multi-ticket query
    status_filter = TicketStatus(status) if status else None

    tickets = list(storage.query(
        status=status_filter,
        ticket_type=ticket_type,
        tag=tag,
        assignee=assignee,
        priority=priority,
        include_closed=include_all,
    ))

    data = [ticket_to_dict(t) for t in tickets]

    if pretty:
        click.echo(json.dumps(data, indent=2, default=str))
    else:
        click.echo(json.dumps(data, default=str))
```

## Acceptance Criteria

- [ ] `bodega list` shows open and in-progress tickets by default
- [ ] `bodega list --all` includes closed tickets
- [ ] All filter options work: --status, --type, --tag, --assignee, --priority
- [ ] `--sort` and `--reverse` work correctly
- [ ] `--format` option changes output format
- [ ] `bodega ready` shows only unblocked tickets
- [ ] `bodega blocked` shows blocked tickets with their blockers
- [ ] `bodega closed` shows recently closed tickets
- [ ] `bodega query` outputs valid JSON
- [ ] `bodega query --id` queries single ticket
- [ ] Pretty-print defaults to TTY detection

## Test Cases

```python
from click.testing import CliRunner
from bodega.cli import main
import json

def test_list_default(tmp_bodega_with_tickets):
    """tmp_bodega_with_tickets creates multiple tickets"""
    runner = CliRunner()
    result = runner.invoke(main, ["list"])
    assert result.exit_code == 0
    assert "bg-" in result.output

def test_list_with_filters(tmp_bodega_with_tickets):
    runner = CliRunner()

    # Create a bug
    runner.invoke(main, ["create", "-t", "bug", "Test bug"])

    result = runner.invoke(main, ["list", "-t", "bug"])
    assert result.exit_code == 0
    assert "bug" in result.output

def test_list_format_ids(tmp_bodega_with_tickets):
    runner = CliRunner()
    result = runner.invoke(main, ["list", "-f", "ids"])
    assert result.exit_code == 0
    # Should only have IDs, one per line
    for line in result.output.strip().split("\n"):
        if line:
            assert line.startswith("bg-")

def test_ready(tmp_bodega_with_ticket):
    runner = CliRunner()
    result = runner.invoke(main, ["ready"])
    assert result.exit_code == 0

def test_blocked(tmp_bodega):
    runner = CliRunner()

    # Create blocker
    result = runner.invoke(main, ["create", "Blocker"])
    blocker_id = result.output.strip()

    # Create blocked ticket
    result = runner.invoke(main, ["create", "-d", blocker_id, "Blocked"])

    result = runner.invoke(main, ["blocked"])
    assert result.exit_code == 0
    assert "Blocked by:" in result.output

def test_query_json(tmp_bodega_with_tickets):
    runner = CliRunner()
    result = runner.invoke(main, ["query"])
    assert result.exit_code == 0

    data = json.loads(result.output)
    assert isinstance(data, list)
    for ticket in data:
        assert "id" in ticket
        assert "title" in ticket

def test_query_single(tmp_bodega_with_ticket):
    runner = CliRunner()
    ticket_id = tmp_bodega_with_ticket

    result = runner.invoke(main, ["query", "--id", ticket_id])
    assert result.exit_code == 0

    data = json.loads(result.output)
    assert data["id"] == ticket_id
```
