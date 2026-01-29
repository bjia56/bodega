"""Create command - Create new tickets."""

import click
import subprocess
import tempfile
import re
from pathlib import Path
import frontmatter

from bodega.commands.utils import pass_context, Context, require_repo
from bodega.models.ticket import Ticket, TicketType, TicketStatus
from bodega.utils import get_git_user


TEMPLATE = """\
---
title: {title}
type: {type}
priority: {priority}
assignee: {assignee}
tags: []
# deps: []
# parent:
# external_ref:
---
## Description

Enter description here...

## Design

(Optional) Design notes...

## Acceptance Criteria

- [ ] Criterion 1
- [ ] Criterion 2
"""


@click.command()
@click.argument("title", required=False)
@click.option("--type", "-t", "ticket_type",
              type=click.Choice(["bug", "feature", "task", "epic", "chore"]),
              default=None, help="Ticket type")
@click.option("--priority", "-p", type=click.IntRange(0, 4),
              default=None, help="Priority (0=critical, 4=backlog)")
@click.option("--assignee", "-a", default=None, help="Assignee name")
@click.option("--tag", multiple=True, help="Tag (can be repeated)")
@click.option("--parent", default=None, help="Parent ticket ID")
@click.option("--external-ref", "-e", default=None, help="External reference")
@click.option("--dep", "-d", multiple=True, help="Blocking ticket ID (can be repeated)")
@click.option("--description", default=None, help="Description text")
@pass_context
def create(
    ctx: Context,
    title: str | None,
    ticket_type: str | None,
    priority: int | None,
    assignee: str | None,
    tag: tuple[str, ...],
    parent: str | None,
    external_ref: str | None,
    dep: tuple[str, ...],
    description: str | None,
):
    """
    Create a new ticket.

    If TITLE is not provided, opens $EDITOR for interactive creation.

    Examples:

        bodega create "Fix login bug"

        bodega create -t bug -p 1 "Fix login bug"

        bodega create -t feature --tag api --tag v2 "Add profiles"

        bodega create  # Opens editor
    """
    storage = require_repo(ctx)
    config = ctx.config

    # Use defaults from config
    final_type = ticket_type or config.default_type
    final_priority = priority if priority is not None else config.default_priority
    final_assignee = assignee or config.default_assignee or get_git_user()

    if title:
        # Create directly from arguments
        ticket = Ticket(
            id="",  # Will be generated
            title=title,
            type=TicketType(final_type),
            status=TicketStatus.OPEN,
            priority=final_priority,
            assignee=final_assignee,
            tags=list(tag),
            deps=list(dep),
            parent=parent,
            external_ref=external_ref,
            description=description,
        )
    else:
        # Interactive creation via editor
        ticket = create_interactive(ctx, final_type, final_priority, final_assignee)
        if ticket is None:
            click.echo("Ticket creation cancelled.", err=True)
            raise SystemExit(1)

    # Validate dependencies exist
    all_ids = storage.list_ids()
    for d in ticket.deps:
        if d not in all_ids:
            click.echo(f"Warning: Dependency {d} does not exist", err=True)

    # Create the ticket
    created = storage.create(ticket)
    click.echo(created.id)


def create_interactive(
    ctx: Context,
    default_type: str,
    default_priority: int,
    default_assignee: str | None,
) -> Ticket | None:
    """Create ticket via editor."""
    template = TEMPLATE.format(
        title="Enter title",
        type=default_type,
        priority=default_priority,
        assignee=default_assignee or "",
    )

    # Write template to temp file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False
    ) as f:
        f.write(template)
        temp_path = Path(f.name)

    try:
        # Open editor
        editor = ctx.config.effective_editor
        result = subprocess.run([editor, str(temp_path)])

        if result.returncode != 0:
            return None

        # Parse edited content
        content = temp_path.read_text()

        # Check if user kept default title
        if "Enter title" in content:
            return None

        # Parse and create ticket
        post = frontmatter.loads(content)

        return Ticket(
            id="",
            title=post.metadata.get("title", "Untitled"),
            type=TicketType(post.metadata.get("type", "task")),
            status=TicketStatus.OPEN,
            priority=post.metadata.get("priority", 2),
            assignee=post.metadata.get("assignee") or None,
            tags=post.metadata.get("tags", []),
            deps=post.metadata.get("deps", []),
            parent=post.metadata.get("parent"),
            external_ref=post.metadata.get("external_ref"),
            description=_extract_section(post.content, "Description"),
            design=_extract_section(post.content, "Design"),
            acceptance_criteria=_extract_section(post.content, "Acceptance Criteria"),
        )

    finally:
        temp_path.unlink()


def _extract_section(content: str, heading: str) -> str | None:
    """Extract content under a markdown heading."""
    pattern = rf"##\s+{re.escape(heading)}\s*\n(.*?)(?=\n##|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        text = match.group(1).strip()
        # Return None for placeholder text
        if text and text not in ["Enter description here...", "(Optional) Design notes..."]:
            return text
    return None
