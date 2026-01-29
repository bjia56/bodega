"""Create command - Create new tickets."""

import click
from bodega.commands.utils import pass_context, Context


@click.command()
@click.argument("title", nargs=-1, required=True)
@click.option("--type", "-t", "ticket_type", help="Ticket type (bug, feature, task, epic, chore)")
@click.option("--priority", "-p", type=int, help="Priority (0-4)")
@click.option("--assignee", "-a", help="Assignee")
@click.option("--tag", "tags", multiple=True, help="Tags (can be specified multiple times)")
@pass_context
def create(ctx: Context, title: tuple, ticket_type: str, priority: int, assignee: str, tags: tuple):
    """Create a new ticket"""
    click.echo("create command - to be implemented")
