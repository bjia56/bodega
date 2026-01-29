"""View commands - Display and edit tickets."""

import click
from bodega.commands.utils import pass_context, Context, ticket_id_argument


@click.command()
@ticket_id_argument
@pass_context
def show(ctx: Context, ticket_id: str):
    """Show detailed ticket information"""
    click.echo("show command - to be implemented")


@click.command()
@ticket_id_argument
@pass_context
def edit(ctx: Context, ticket_id: str):
    """Edit a ticket in $EDITOR"""
    click.echo("edit command - to be implemented")


@click.command()
@ticket_id_argument
@click.argument("note_text", nargs=-1, required=True)
@pass_context
def note(ctx: Context, ticket_id: str, note_text: tuple):
    """Add a note to a ticket"""
    click.echo("note command - to be implemented")
