# Task 11: Lifecycle Commands

## Summary
Implement ticket lifecycle commands: `start`, `close`, `reopen`, and `status`.

## Dependencies
- Task 01: Project Setup
- Task 02: Models (Ticket, TicketStatus)
- Task 05: Storage (TicketStorage)
- Task 08: CLI Base

## Requirements

### 1. Lifecycle Commands (`src/bodega/commands/lifecycle.py`)

```python
import click

from ..cli import pass_context, Context, require_repo
from ..models import TicketStatus
from ..storage import TicketNotFoundError

@click.command()
@click.argument("ticket_id", metavar="ID")
@pass_context
def start(ctx: Context, ticket_id: str):
    """
    Set ticket status to in-progress.

    Examples:

        bodega start bg-a1b2c3

        bodega start a1b  # Partial ID
    """
    storage = require_repo(ctx)

    try:
        ticket = storage.get(ticket_id)

        if ticket.status == TicketStatus.IN_PROGRESS:
            click.echo(f"{ticket.id} is already in-progress")
            return

        ticket.status = TicketStatus.IN_PROGRESS
        storage.save(ticket)
        click.echo(f"{ticket.id} → in-progress")

    except TicketNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except ValueError as e:  # Ambiguous ID
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@click.command()
@click.argument("ticket_id", metavar="ID")
@pass_context
def close(ctx: Context, ticket_id: str):
    """
    Set ticket status to closed.

    Examples:

        bodega close bg-a1b2c3

        bodega close a1b
    """
    storage = require_repo(ctx)

    try:
        ticket = storage.get(ticket_id)

        if ticket.status == TicketStatus.CLOSED:
            click.echo(f"{ticket.id} is already closed")
            return

        ticket.status = TicketStatus.CLOSED
        storage.save(ticket)
        click.echo(f"{ticket.id} → closed")

    except TicketNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@click.command()
@click.argument("ticket_id", metavar="ID")
@pass_context
def reopen(ctx: Context, ticket_id: str):
    """
    Set ticket status back to open.

    Examples:

        bodega reopen bg-a1b2c3
    """
    storage = require_repo(ctx)

    try:
        ticket = storage.get(ticket_id)

        if ticket.status == TicketStatus.OPEN:
            click.echo(f"{ticket.id} is already open")
            return

        ticket.status = TicketStatus.OPEN
        storage.save(ticket)
        click.echo(f"{ticket.id} → open")

    except TicketNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@click.command()
@click.argument("ticket_id", metavar="ID")
@pass_context
def status(ctx: Context, ticket_id: str):
    """
    Get ticket status.

    Examples:

        bodega status bg-a1b2c3
    """
    storage = require_repo(ctx)

    try:
        ticket = storage.get(ticket_id)
        click.echo(ticket.status.value)

    except TicketNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
```

## Acceptance Criteria

- [ ] `bodega start <id>` sets status to in-progress
- [ ] `bodega close <id>` sets status to closed
- [ ] `bodega reopen <id>` sets status to open
- [ ] `bodega status <id>` prints current status
- [ ] All commands support partial ID matching
- [ ] No-op message when already in target status
- [ ] Error message for non-existent ticket
- [ ] Error message for ambiguous ID
- [ ] Updated timestamp is set on status change

## Test Cases

```python
from click.testing import CliRunner
from bodega.cli import main

def test_start(tmp_bodega_with_ticket):
    """tmp_bodega_with_ticket creates a ticket and returns its ID"""
    runner = CliRunner()
    ticket_id = tmp_bodega_with_ticket

    result = runner.invoke(main, ["start", ticket_id])
    assert result.exit_code == 0
    assert "in-progress" in result.output

    # Verify status changed
    result = runner.invoke(main, ["status", ticket_id])
    assert result.output.strip() == "in-progress"

def test_close(tmp_bodega_with_ticket):
    runner = CliRunner()
    ticket_id = tmp_bodega_with_ticket

    result = runner.invoke(main, ["close", ticket_id])
    assert result.exit_code == 0
    assert "closed" in result.output

def test_reopen(tmp_bodega_with_ticket):
    runner = CliRunner()
    ticket_id = tmp_bodega_with_ticket

    # Close first
    runner.invoke(main, ["close", ticket_id])

    # Reopen
    result = runner.invoke(main, ["reopen", ticket_id])
    assert result.exit_code == 0
    assert "open" in result.output

def test_start_already_in_progress(tmp_bodega_with_ticket):
    runner = CliRunner()
    ticket_id = tmp_bodega_with_ticket

    runner.invoke(main, ["start", ticket_id])
    result = runner.invoke(main, ["start", ticket_id])
    assert "already in-progress" in result.output

def test_partial_id(tmp_bodega_with_ticket):
    runner = CliRunner()
    ticket_id = tmp_bodega_with_ticket
    partial = ticket_id[3:6]  # e.g., "a1b" from "bg-a1b2c3"

    result = runner.invoke(main, ["start", partial])
    assert result.exit_code == 0

def test_not_found(tmp_bodega):
    runner = CliRunner()
    result = runner.invoke(main, ["start", "bg-notfound"])
    assert result.exit_code == 1
    assert "not found" in result.output.lower() or "No ticket" in result.output
```
