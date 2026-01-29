"""Init command - Initialize a new bodega repository."""

import click
from pathlib import Path

from bodega.storage import init_repository, StorageError
from bodega.commands.utils import pass_context, Context
from bodega.worktree import init_worktree
from bodega.utils import find_repo_root


@click.command()
@click.help_option("-h", "--help", help="Show this message and exit")
@click.option("--force", is_flag=True, help="Reinitialize existing repository")
@click.argument("path", required=False, type=click.Path())
@pass_context
def init(ctx: Context, force: bool, path: str | None):
    """
    Initialize a new bodega repository with git worktree support

    Creates a .bodega/ directory with default configuration and sets up
    a git worktree on a separate branch for ticket storage.

    Examples:

        bodega init           # Initialize in current directory

        bodega init ./myproj  # Initialize in specific directory

        bodega init --force   # Reinitialize existing repo
    """
    target = Path(path) if path else Path.cwd()

    # Check if in git repo
    repo_root = find_repo_root()
    if not repo_root:
        click.echo("Error: Not in a git repository", err=True)
        click.echo("Initialize git first: git init", err=True)
        raise SystemExit(1)

    try:
        # Create .bodega directory and config
        bodega_dir = init_repository(target, force=force)
        click.echo(f"Initialized bodega repository at {bodega_dir}")

        # Initialize git worktree
        worktree_path = init_worktree(
            Path(repo_root),
            bodega_dir,
            branch_name=ctx.config.git_branch
        )
        click.echo(f"Created git worktree on branch '{ctx.config.git_branch}'")
        click.echo("Added .bodega/.gitignore to exclude worktree/")

        click.echo("\nNext steps:")
        click.echo("  bodega create \"My first ticket\"")
        click.echo("  bodega list")

    except StorageError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
