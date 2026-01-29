"""Init command - Initialize a new bodega repository."""

import click
from bodega.commands.utils import pass_context, Context


@click.command()
@click.option("--force", "-f", is_flag=True, help="Overwrite existing repository")
@pass_context
def init(ctx: Context, force: bool):
    """Initialize a new bodega repository"""
    click.echo("init command - to be implemented")
