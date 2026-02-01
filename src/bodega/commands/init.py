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
@click.option("--branch", type=str, default=None, help="Git branch for worktree-based storage (e.g., 'bodega'). If not specified, tickets are stored in current branch.")
@click.argument("path", required=False, type=click.Path())
@pass_context
def init(ctx: Context, force: bool, branch: str | None, path: str | None):
    """
    Initialize a new bodega repository

    Creates a .bodega/ directory with default configuration.

    By default, tickets are stored in .bodega/ on the current branch.
    Use --branch to enable git worktree mode for separate ticket storage.

    Examples:

        bodega init                    # Store tickets in current branch

        bodega init --branch bodega    # Use worktree on 'bodega' branch

        bodega init ./myproj           # Initialize in specific directory

        bodega init --force            # Reinitialize existing repo
    """
    target = Path(path) if path else Path.cwd()

    try:
        # Create .bodega directory and config
        bodega_dir = init_repository(target, force=force)
        click.echo(f"Initialized bodega repository at {bodega_dir}")

        # If branch specified, set up worktree
        if branch:
            # Check if in git repo
            repo_root = find_repo_root()
            if not repo_root:
                click.echo("Error: --branch requires a git repository", err=True)
                click.echo("Initialize git first: git init", err=True)
                raise SystemExit(1)

            # Update config with branch name
            config_path = bodega_dir / "config.yaml"
            if config_path.exists():
                import yaml
                with open(config_path, 'r') as f:
                    config_data = yaml.safe_load(f) or {}

                # Set git branch in config
                if 'git' not in config_data:
                    config_data['git'] = {}
                config_data['git']['branch'] = branch

                with open(config_path, 'w') as f:
                    yaml.dump(config_data, f, default_flow_style=False)

            # Initialize git worktree
            worktree_path = init_worktree(
                Path(repo_root),
                bodega_dir,
                branch_name=branch
            )
            click.echo(f"Created git worktree on branch '{branch}'")
            click.echo("Added .bodega/.gitignore to exclude worktree/")
        else:
            # No branch specified - store tickets in current branch
            click.echo("Tickets will be stored in .bodega/ on current branch")

            # Update config to set empty branch
            config_path = bodega_dir / "config.yaml"
            if config_path.exists():
                import yaml
                with open(config_path, 'r') as f:
                    config_data = yaml.safe_load(f) or {}

                # Set git branch to empty string
                if 'git' not in config_data:
                    config_data['git'] = {}
                config_data['git']['branch'] = ""

                with open(config_path, 'w') as f:
                    yaml.dump(config_data, f, default_flow_style=False)

        click.echo("\nNext steps:")
        click.echo("  bodega create \"My first ticket\"")
        click.echo("  bodega list")

    except StorageError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
