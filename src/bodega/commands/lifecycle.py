"""Lifecycle commands - Manage ticket status transitions."""

import click
from bodega.commands.utils import pass_context, Context, ticket_id_argument


@click.command()
@ticket_id_argument
@pass_context
def start(ctx: Context, ticket_id: str):
    """Start working on a ticket (move to in-progress)"""
    click.echo("start command - to be implemented")


@click.command()
@ticket_id_argument
@pass_context
def close(ctx: Context, ticket_id: str):
    """Close a ticket"""
    click.echo("close command - to be implemented")


@click.command()
@ticket_id_argument
@pass_context
def reopen(ctx: Context, ticket_id: str):
    """Reopen a closed ticket"""
    click.echo("reopen command - to be implemented")


@click.command()
@ticket_id_argument
@click.argument("new_status", required=True)
@pass_context
def status(ctx: Context, ticket_id: str, new_status: str):
    """Change ticket status"""
    click.echo("status command - to be implemented")
