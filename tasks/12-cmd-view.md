# Task 12: View Commands

## Summary
Implement commands for viewing and editing tickets: `show`, `edit`, and `note`.

## Dependencies
- Task 01: Project Setup
- Task 02: Models (Ticket)
- Task 05: Storage (TicketStorage)
- Task 06: Output (format_ticket_detail, ticket_to_dict)
- Task 08: CLI Base

## Requirements

### 1. View Commands (`src/bodega/commands/view.py`)

```python
import click
import subprocess
import json
from datetime import datetime

from ..cli import pass_context, Context, require_repo
from ..storage import TicketNotFoundError
from ..output import format_ticket_detail, ticket_to_dict

@click.command()
@click.argument("ticket_id", metavar="ID")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.option("--raw", is_flag=True, help="Output raw markdown file")
@pass_context
def show(ctx: Context, ticket_id: str, as_json: bool, raw: bool):
    """
    Display ticket details.

    Examples:

        bodega show bg-a1b2c3

        bodega show a1b  # Partial ID

        bodega show --json bg-a1b2c3

        bodega show --raw bg-a1b2c3
    """
    storage = require_repo(ctx)

    try:
        ticket = storage.get(ticket_id)

        if raw:
            # Output raw markdown file
            path = storage._ticket_path(ticket.id)
            click.echo(path.read_text())
        elif as_json:
            # Output as JSON
            data = ticket_to_dict(ticket)
            click.echo(json.dumps(data, indent=2, default=str))
        else:
            # Formatted display
            click.echo(format_ticket_detail(ticket, ctx.config))

    except TicketNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@click.command()
@click.argument("ticket_id", metavar="ID")
@pass_context
def edit(ctx: Context, ticket_id: str):
    """
    Open ticket in $EDITOR for editing.

    The ticket file is opened directly, allowing full control over
    all fields and content.

    Examples:

        bodega edit bg-a1b2c3

        EDITOR=code bodega edit bg-a1b2c3
    """
    storage = require_repo(ctx)

    try:
        ticket = storage.get(ticket_id)
        path = storage._ticket_path(ticket.id)

        # Open in editor
        editor = ctx.config.effective_editor
        result = subprocess.run([editor, str(path)])

        if result.returncode != 0:
            click.echo(f"Editor exited with code {result.returncode}", err=True)
            raise SystemExit(1)

        # Validate the edited file
        try:
            # Re-read to validate
            storage.get(ticket.id)
            click.echo(f"Saved {ticket.id}")
        except Exception as e:
            click.echo(f"Warning: File may have invalid format: {e}", err=True)

    except TicketNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@click.command()
@click.argument("ticket_id", metavar="ID")
@click.argument("text")
@pass_context
def note(ctx: Context, ticket_id: str, text: str):
    """
    Add a timestamped note to a ticket.

    Notes are appended to the ## Notes section with a timestamp.

    Examples:

        bodega note bg-a1b2c3 "Blocked waiting for API spec"

        bodega note a1b "Discussed with team, moving forward"
    """
    storage = require_repo(ctx)

    try:
        ticket = storage.get(ticket_id)

        # Add timestamped note
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        ticket.notes.append(f"{timestamp}: {text}")
        ticket.updated = datetime.utcnow()

        storage.save(ticket)
        click.echo(f"Added note to {ticket.id}")

    except TicketNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
```

## Acceptance Criteria

- [ ] `bodega show <id>` displays formatted ticket details
- [ ] `bodega show --json <id>` outputs valid JSON
- [ ] `bodega show --raw <id>` outputs raw markdown file
- [ ] `bodega edit <id>` opens ticket in $EDITOR
- [ ] `bodega edit` validates file after editing
- [ ] `bodega note <id> <text>` adds timestamped note
- [ ] All commands support partial ID matching
- [ ] Error handling for non-existent tickets

## Test Cases

```python
from click.testing import CliRunner
from bodega.cli import main
import json

def test_show(tmp_bodega_with_ticket):
    runner = CliRunner()
    ticket_id = tmp_bodega_with_ticket

    result = runner.invoke(main, ["show", ticket_id])
    assert result.exit_code == 0
    assert ticket_id in result.output
    assert "Status:" in result.output

def test_show_json(tmp_bodega_with_ticket):
    runner = CliRunner()
    ticket_id = tmp_bodega_with_ticket

    result = runner.invoke(main, ["show", "--json", ticket_id])
    assert result.exit_code == 0

    data = json.loads(result.output)
    assert data["id"] == ticket_id
    assert "title" in data
    assert "status" in data

def test_show_raw(tmp_bodega_with_ticket):
    runner = CliRunner()
    ticket_id = tmp_bodega_with_ticket

    result = runner.invoke(main, ["show", "--raw", ticket_id])
    assert result.exit_code == 0
    assert "---" in result.output  # YAML frontmatter

def test_note(tmp_bodega_with_ticket):
    runner = CliRunner()
    ticket_id = tmp_bodega_with_ticket

    result = runner.invoke(main, ["note", ticket_id, "Test note"])
    assert result.exit_code == 0
    assert "Added note" in result.output

    # Verify note was added
    result = runner.invoke(main, ["show", "--json", ticket_id])
    data = json.loads(result.output)
    assert any("Test note" in n for n in data["notes"])

def test_show_not_found(tmp_bodega):
    runner = CliRunner()
    result = runner.invoke(main, ["show", "bg-notfound"])
    assert result.exit_code == 1
```
