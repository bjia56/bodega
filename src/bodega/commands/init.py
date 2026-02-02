"""Init command - Initialize a new bodega repository."""

import click
from pathlib import Path

from bodega.storage import init_repository, StorageError
from bodega.commands.utils import pass_context, Context
from bodega.worktree import init_worktree, ensure_worktree
from bodega.utils import find_repo_root
from bodega.config import load_config


@click.command()
@click.help_option("-h", "--help", help="Show this message and exit")
@click.option("--reset", is_flag=True, help="Reset and reinitialize existing repository")
@click.option("--branch", type=str, default=None, help="Git branch for worktree-based storage (e.g., 'bodega'). If not specified, tickets are stored in current branch.")
@click.argument("path", required=False, type=click.Path())
@pass_context
def init(ctx: Context, reset: bool, branch: str | None, path: str | None):
    """
    Initialize a new bodega repository

    Creates a .bodega/ directory with default configuration.

    By default, tickets are stored in .bodega/ on the current branch.
    Use --branch to enable git worktree mode for separate ticket storage.

    When run in a cloned repository with existing .bodega/ directory,
    automatically sets up local worktree based on existing configuration.

    Examples:

        bodega init                    # Store tickets in current branch

        bodega init --branch bodega    # Use worktree on 'bodega' branch

        bodega init ./myproj           # Initialize in specific directory

        bodega init --reset            # Reset existing repository
    """
    target = Path(path) if path else Path.cwd()
    bodega_dir = target / ".bodega"

    try:
        # Check if this is a cloned repository with existing configuration
        if bodega_dir.exists() and (bodega_dir / "config.yaml").exists() and not reset:
            click.echo(f"Found existing bodega repository at {bodega_dir}")

            # Load existing configuration
            try:
                config = load_config(bodega_dir)
            except Exception as e:
                click.echo(f"Warning: Could not load config: {e}", err=True)
                click.echo("Use --reset to reinitialize", err=True)
                raise SystemExit(1)

            # Check if worktree mode is configured
            if config.git_branch:
                # Worktree mode - ensure worktree is set up
                worktree_path = bodega_dir / "worktree"

                # Check if in git repo
                repo_root = find_repo_root()
                if not repo_root:
                    click.echo("Error: Configuration uses git worktree but not in a git repository", err=True)
                    raise SystemExit(1)

                if not worktree_path.exists():
                    click.echo(f"Setting up worktree for branch '{config.git_branch}'...")
                    try:
                        worktree_bodega_dir = ensure_worktree(bodega_dir, config.git_branch)
                        click.echo(f"Created git worktree on branch '{config.git_branch}'")
                        click.echo(f"Tickets will be stored in worktree")
                    except StorageError as e:
                        click.echo(f"Error setting up worktree: {e}", err=True)
                        raise SystemExit(1)
                else:
                    click.echo(f"Worktree already configured on branch '{config.git_branch}'")
            else:
                # Direct mode - tickets in current branch
                click.echo("Tickets are stored in .bodega/ on current branch")

            click.echo("\nRepository ready to use:")
            click.echo("  bodega create \"My first ticket\"")
            click.echo("  bodega list")
            return

        # Create .bodega directory and config (new repository or reset)
        bodega_dir = init_repository(target, force=reset)
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
