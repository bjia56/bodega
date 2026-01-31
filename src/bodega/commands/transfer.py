"""Transfer command - Import tickets from other systems."""

import click
import json
from pathlib import Path
from datetime import datetime, UTC

from bodega.commands.utils import pass_context, Context, require_repo
from bodega.models import Ticket, TicketType, TicketStatus
from bodega.utils import generate_id


@click.command()
@click.help_option("-h", "--help", help="Show this message and exit")
@click.option("--from", "from_system", type=click.Choice(["beads"], case_sensitive=False),
              default="beads", help="Source system to transfer from (default: beads)")
@click.option("--path", "-p", type=click.Path(exists=True),
              help="Path to source directory (default: .beads)")
@click.option("--dry-run", is_flag=True,
              help="Show what would be transferred")
@click.option("--preserve-ids", is_flag=True,
              help="Keep original IDs instead of generating new ones")
@pass_context
def transfer(
    ctx: Context,
    from_system: str,
    path: str | None,
    dry_run: bool,
    preserve_ids: bool,
):
    """
    Transfer tickets from another system

    Reads from the specified source system and creates bodega tickets.
    Currently supports transferring from beads.

    Examples:

        bodega transfer                        # Transfer from .beads

        bodega transfer --from beads           # Explicit source

        bodega transfer --path /other/.beads   # Custom path

        bodega transfer --dry-run              # Show what would transfer

        bodega transfer --preserve-ids         # Keep original IDs
    """
    storage = require_repo(ctx)

    # Currently only beads is supported
    if from_system.lower() != "beads":
        click.echo(f"Error: Unsupported source system: {from_system}", err=True)
        raise SystemExit(1)

    # Find beads directory
    beads_path = Path(path) if path else Path.cwd() / ".beads"
    issues_file = beads_path / "issues.jsonl"

    if not issues_file.exists():
        click.echo(f"Error: Source file not found: {issues_file}", err=True)
        raise SystemExit(1)

    # Read and parse beads issues
    issues = []
    with open(issues_file) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                issue = json.loads(line)
                issues.append(issue)
            except json.JSONDecodeError as e:
                click.echo(f"Warning: Invalid JSON on line {line_num}: {e}", err=True)

    if not issues:
        click.echo("No issues found to transfer.")
        return

    click.echo(f"Found {len(issues)} issues to transfer.")

    # Build ID mapping (old -> new)
    id_map = {}
    for issue in issues:
        old_id = issue.get("id", "")
        if preserve_ids:
            new_id = old_id
        else:
            new_id = generate_id(ctx.config.id_prefix)
        id_map[old_id] = new_id

    # Convert and save tickets
    migrated = 0
    for issue in issues:
        try:
            ticket = convert_beads_issue(issue, id_map, preserve_ids, ctx.config.id_prefix)

            if dry_run:
                click.echo(f"  Would create: {ticket.id} - {ticket.title}")
            else:
                storage.create(ticket)
                click.echo(f"  Created: {ticket.id} - {ticket.title}")

            migrated += 1

        except Exception as e:
            old_id = issue.get("id", "unknown")
            click.echo(f"  Error transferring {old_id}: {e}", err=True)

    if dry_run:
        click.echo(f"\nDry run complete. Would transfer {migrated} tickets.")
    else:
        click.echo(f"\nTransfer complete. Created {migrated} tickets.")


def convert_beads_issue(
    issue: dict,
    id_map: dict[str, str],
    preserve_ids: bool,
    prefix: str,
) -> Ticket:
    """Convert a beads issue dict to a Ticket."""

    old_id = issue.get("id", "")
    new_id = id_map.get(old_id, generate_id(prefix))

    # Map status
    status_str = issue.get("status", "open")
    status_map = {
        "open": TicketStatus.OPEN,
        "in-progress": TicketStatus.IN_PROGRESS,
        "in_progress": TicketStatus.IN_PROGRESS,
        "closed": TicketStatus.CLOSED,
        "done": TicketStatus.CLOSED,
    }
    status = status_map.get(status_str, TicketStatus.OPEN)

    # Map type
    type_str = issue.get("issue_type", "task")
    type_map = {
        "bug": TicketType.BUG,
        "feature": TicketType.FEATURE,
        "task": TicketType.TASK,
        "epic": TicketType.EPIC,
        "chore": TicketType.CHORE,
    }
    ticket_type = type_map.get(type_str, TicketType.TASK)

    # Parse dependencies
    deps = []
    links = []
    parent = None

    for dep in issue.get("dependencies", []):
        dep_type = dep.get("type", "")
        target = dep.get("depends_on_id", "")
        new_target = id_map.get(target, target)

        if dep_type == "blocks":
            deps.append(new_target)
        elif dep_type == "related":
            links.append(new_target)
        elif dep_type == "parent-child":
            parent = new_target

    # Parse timestamps
    created_str = issue.get("created_at")
    created = datetime.fromisoformat(created_str.replace("Z", "+00:00")) if created_str else datetime.now(UTC)

    # Parse notes (could be string or list)
    notes_raw = issue.get("notes", [])
    if isinstance(notes_raw, str):
        notes = [notes_raw] if notes_raw else []
    else:
        notes = notes_raw

    return Ticket(
        id=new_id,
        title=issue.get("title", "Untitled"),
        type=ticket_type,
        status=status,
        priority=issue.get("priority", 2),
        assignee=issue.get("owner"),
        tags=issue.get("labels", []),
        deps=deps,
        links=links,
        parent=parent,
        external_ref=issue.get("external_ref"),
        created=created,
        updated=created,  # Use created as initial updated
        description=issue.get("description"),
        design=issue.get("design"),
        acceptance_criteria=issue.get("acceptance_criteria"),
        notes=notes,
    )
