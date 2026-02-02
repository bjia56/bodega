"""Push command - Push local bodega branch to remote with conflict resolution."""

import click
from pathlib import Path

from bodega.commands.utils import pass_context, Context
from bodega.worktree import push_to_remote
from bodega.errors import StorageError
from bodega.utils import find_repo_root


@click.command()
@click.help_option("-h", "--help", help="Show this message and exit")
@click.option("--dry-run", is_flag=True, help="Show what would be pushed without making changes")
@pass_context
def push(ctx: Context, dry_run: bool):
    """
    Push local bodega branch to remote repository

    This command synchronizes your local bodega branch with the remote:
      1. Fetches latest changes from remote bodega branch
      2. Attempts to rebase local changes on top of remote (or merge if needed)
      3. Pushes the updated bodega branch to remote

    If conflicts occur during rebase/merge, they are auto-resolved using
    the configured git_sync_strategy (default: 'theirs' = local wins).

    Examples:

        bodega push              # Push to remote with auto-sync

        bodega push --dry-run    # Show what would be pushed
    """
    if not ctx.storage:
        click.echo("Error: Not in a bodega repository. Run 'bodega init' first.", err=True)
        raise SystemExit(1)

    repo_root = find_repo_root()
    if not repo_root:
        click.echo("Error: Not in a git repository", err=True)
        raise SystemExit(1)

    # Get paths
    worktree_path = ctx.config.bodega_dir / "worktree"

    if dry_run:
        try:
            # Just show status
            from bodega.worktree import get_push_status
            status = get_push_status(
                Path(repo_root),
                worktree_path,
                ctx.config.git_branch
            )

            click.echo("Push status:")
            click.echo(f"  Local branch: {ctx.config.git_branch}")

            if status.has_remote:
                click.echo(f"  Remote exists: yes")
                click.echo(f"  Commits to push: {status.commits_to_push}")
                click.echo(f"  Commits to pull: {status.commits_to_pull}")

                if status.uncommitted_changes:
                    click.echo(f"\nUncommitted changes in worktree would be auto-committed")

                if status.commits_to_pull > 0 and status.commits_to_push > 0:
                    click.echo(f"\nBranches have diverged - will attempt rebase")
            else:
                click.echo(f"  Remote exists: no (will create on push)")
                click.echo(f"  Commits to push: {status.commits_to_push}")

        except StorageError as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1)
        return

    # Perform push
    try:
        result = push_to_remote(
            Path(repo_root),
            worktree_path,
            ctx.config.git_branch,
            strategy=ctx.config.git_sync_strategy
        )

        if result.auto_committed:
            click.echo("Auto-committed local changes before push")

        if result.pulled_commits > 0:
            click.echo(f"Pulled {result.pulled_commits} commit(s) from remote")

        if result.had_conflicts:
            click.echo(f"Auto-resolved conflicts using '{ctx.config.git_sync_strategy}' strategy")

        if result.pushed_commits > 0:
            click.echo(f"Pushed {result.pushed_commits} commit(s) to remote")
        else:
            click.echo("Everything up-to-date")

    except StorageError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
