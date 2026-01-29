"""Init command - Initialize a new bodega repository."""

import click
from pathlib import Path

from bodega.storage import init_repository, StorageError
from bodega.commands.utils import pass_context, Context


@click.command()
@click.option("--force", is_flag=True, help="Reinitialize existing repository")
@click.argument("path", required=False, type=click.Path())
@pass_context
def init(ctx: Context, force: bool, path: str | None):
    """
    Initialize a new bodega repository.

    Creates a .bodega/ directory with default configuration.

    Examples:

        bodega init           # Initialize in current directory

        bodega init ./myproj  # Initialize in specific directory

        bodega init --force   # Reinitialize existing repo
    """
    target = Path(path) if path else Path.cwd()

    try:
        bodega_dir = init_repository(target, force=force)
        click.echo(f"Initialized bodega repository in {bodega_dir}")
    except StorageError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
