"""List commands - Query and display tickets."""

import click
from bodega.commands.utils import pass_context, Context, filter_options, format_option


@click.command(name="list")
@filter_options
@format_option
@click.option("--include-closed", is_flag=True, help="Include closed tickets")
@pass_context
def list_tickets(ctx: Context, status: str, ticket_type: str, tag: str, assignee: str,
                 priority: int, fmt: str, include_closed: bool):
    """List all tickets"""
    click.echo("list command - to be implemented")


@click.command()
@format_option
@pass_context
def ready(ctx: Context, fmt: str):
    """List tickets ready to work on (not blocked)"""
    click.echo("ready command - to be implemented")


@click.command()
@format_option
@pass_context
def blocked(ctx: Context, fmt: str):
    """List tickets that are blocked"""
    click.echo("blocked command - to be implemented")


@click.command()
@format_option
@pass_context
def closed(ctx: Context, fmt: str):
    """List closed tickets"""
    click.echo("closed command - to be implemented")


@click.command()
@filter_options
@format_option
@pass_context
def query(ctx: Context, status: str, ticket_type: str, tag: str, assignee: str,
          priority: int, fmt: str):
    """Advanced query with multiple filters"""
    click.echo("query command - to be implemented")
