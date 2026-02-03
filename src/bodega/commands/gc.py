"""Garbage collection command - Delete old closed tickets."""

import click
from datetime import timedelta
from pathlib import Path

from bodega.commands.utils import pass_context, Context, require_repo
from bodega.models.ticket import TicketStatus
from bodega.utils import now_utc, parse_duration
from bodega.errors import BodegaError


@click.command()
@click.help_option("-h", "--help", help="Show this message and exit")
@click.option(
    "--age",
    "-a",
    default="30d",
    help="Delete tickets closed longer than this duration (default: 30d). Format: <number><unit> where unit is d/days, h/hours, or m/minutes. Examples: 30d, 7days, 12h"
)
@click.option(
    "--dry-run",
    "-n",
    is_flag=True,
    help="Show which tickets would be deleted without actually deleting them"
)
@pass_context
def gc(ctx: Context, age: str, dry_run: bool):
    """
    Garbage collect (delete) old closed tickets

    Deletes tickets that have been closed for longer than the specified
    duration. In worktree mode, creates a single commit for all deletions.

    Examples:

        bodega gc                # Delete tickets closed > 30 days ago

        bodega gc --age 7d       # Delete tickets closed > 7 days ago

        bodega gc --age 12h      # Delete tickets closed > 12 hours ago

        bodega gc --dry-run      # Show what would be deleted
    """
    storage = require_repo(ctx)

    # Parse the age duration
    try:
        age_delta = parse_duration(age)
    except BodegaError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    # Calculate cutoff time
    cutoff_time = now_utc() - age_delta

    # Find tickets to delete
    tickets_to_delete = []
    for ticket in storage.list_all():
        if ticket.status == TicketStatus.CLOSED:
            # Use the ticket's updated time as the close time
            if ticket.updated < cutoff_time:
                tickets_to_delete.append(ticket)

    if not tickets_to_delete:
        click.echo(f"No closed tickets older than {age}")
        return

    # Show what will be deleted
    if dry_run:
        click.echo(f"Tickets that would be deleted (closed before {cutoff_time.strftime('%Y-%m-%d %H:%M:%S UTC')}):")
        for ticket in tickets_to_delete:
            age_str = _format_age(now_utc() - ticket.updated)
            click.echo(f"  {ticket.id}: {ticket.title} (closed {age_str} ago)")
        click.echo(f"\nTotal: {len(tickets_to_delete)} ticket(s)")
        return

    # Delete tickets
    deleted_count = 0
    for ticket in tickets_to_delete:
        try:
            storage.delete(ticket.id)
            deleted_count += 1
        except Exception as e:
            click.echo(f"Warning: Failed to delete {ticket.id}: {e}", err=True)

    click.echo(f"Deleted {deleted_count} ticket(s)")

    # If in worktree mode, commit the changes
    if storage.use_worktree:
        from bodega.worktree import has_uncommitted_changes, _run_git, _generate_batch_commit_message

        if has_uncommitted_changes(storage.worktree_path, '.bodega'):
            # Stage deletions
            _run_git(['git', 'add', '-A', '.bodega/'], cwd=storage.worktree_path)

            # Generate commit message
            commit_msg = _generate_batch_commit_message(
                storage.worktree_path,
                f'Garbage collect {deleted_count} closed ticket(s) older than {age}'
            )

            # Commit
            _run_git(
                ['git', 'commit', '-m', commit_msg],
                cwd=storage.worktree_path,
                check=False
            )

            click.echo(f"Changes committed to {ctx.config.git_branch} branch")


def _format_age(delta: timedelta) -> str:
    """
    Format a timedelta as a human-readable age string.

    Args:
        delta: The timedelta to format

    Returns:
        Human-readable age string (e.g., "3 days", "12 hours", "45 minutes")
    """
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, _ = divmod(remainder, 60)

    if days > 0:
        return f"{days} day{'s' if days != 1 else ''}"
    elif hours > 0:
        return f"{hours} hour{'s' if hours != 1 else ''}"
    else:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
