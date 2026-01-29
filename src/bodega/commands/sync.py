"""Sync command - Synchronize tickets between main and bodega branches."""

import click
from pathlib import Path

from bodega.commands.utils import pass_context, Context
from bodega.worktree import sync_branches, get_sync_status
from bodega.errors import StorageError
from bodega.utils import find_repo_root
from bodega.worktree import get_current_branch


@click.command()
@click.help_option("-h", "--help", help="Show this message and exit")
@click.option("--dry-run", is_flag=True, help="Show what would be synced without making changes")
@click.option("--no-merge-main", is_flag=True, help="Skip merging bodega → main (one-way sync)")
@pass_context
def sync(ctx: Context, dry_run: bool, no_merge_main: bool):
    """
    Synchronize tickets between main and bodega branches

    Performs two-way merge:
      1. main → bodega (bring ticket commits from main)
      2. bodega → main (bring ticket commits from bodega)

    After sync, ticket files appear in main branch as uncommitted changes.
    You must manually commit them to your main branch.

    Examples:

        bodega sync              # Two-way sync

        bodega sync --dry-run    # Show what would be synced

        bodega sync --no-merge-main  # Only sync main → bodega
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

    # Get current branch
    try:
        current_branch = get_current_branch(Path(repo_root))
    except StorageError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    if dry_run:
        try:
            status = get_sync_status(
                Path(repo_root),
                worktree_path,
                current_branch,
                ctx.config.git_branch
            )

            click.echo("Sync status:")
            click.echo(f"  {current_branch} → {ctx.config.git_branch}: {status.commits_ahead_main} commits")
            click.echo(f"  {ctx.config.git_branch} → {current_branch}: {status.commits_ahead_bodega} commits")

            if status.uncommitted_in_main:
                click.echo(f"\nWarning: Uncommitted changes in .bodega/ on {current_branch}")
                click.echo("Sync would abort. Commit or stash changes first.")
            elif status.uncommitted_in_worktree:
                click.echo(f"\nUncommitted changes in worktree would be auto-committed")

        except StorageError as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1)
        return

    # Perform sync
    try:
        result = sync_branches(
            Path(repo_root),
            worktree_path,
            current_branch,
            ctx.config.git_branch,
            strategy=ctx.config.git_sync_strategy,
            skip_merge_to_main=no_merge_main
        )

        click.echo(f"Merged {result.commits_from_main} commits: {current_branch} → {ctx.config.git_branch}")

        if not no_merge_main:
            click.echo(f"Merged {result.commits_from_bodega} commits: {ctx.config.git_branch} → {current_branch}")

            if result.files_changed > 0:
                click.echo(f"\n{result.files_changed} ticket file(s) updated in .bodega/")
                click.echo("Remember to commit changes in main branch:")
                click.echo(f"  git add .bodega/")
                click.echo(f"  git commit -m 'Update tickets'")
            else:
                click.echo("\nNo ticket files changed")

        if result.had_conflicts:
            click.echo(f"\nNote: Conflicts were auto-resolved using '{ctx.config.git_sync_strategy}' strategy")

    except StorageError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@click.command()
@click.help_option("-h", "--help", help="Show this message and exit")
@pass_context
def status(ctx: Context):
    """
    Show sync status between main and bodega branches

    Displays:
      - Current branch
      - Commits ahead/behind
      - Uncommitted changes
      - Sync recommendations
    """
    if not ctx.storage:
        click.echo("Error: Not in a bodega repository. Run 'bodega init' first.", err=True)
        raise SystemExit(1)

    repo_root = find_repo_root()
    if not repo_root:
        click.echo("Error: Not in a git repository", err=True)
        raise SystemExit(1)

    worktree_path = ctx.config.bodega_dir / "worktree"

    try:
        current_branch = get_current_branch(Path(repo_root))
    except StorageError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    try:
        sync_status = get_sync_status(
            Path(repo_root),
            worktree_path,
            current_branch,
            ctx.config.git_branch
        )

        click.echo(f"Bodega branch: {ctx.config.git_branch}")
        click.echo(f"Current branch: {current_branch}")
        click.echo()

        click.echo("Worktree status:")
        click.echo(f"  Location: {worktree_path}")

        # Count tickets
        ticket_files = list((worktree_path / ".bodega").glob("*.md"))
        click.echo(f"  Tickets: {len(ticket_files)} files")

        if sync_status.uncommitted_in_worktree:
            click.echo("  Uncommitted: Yes")
        else:
            click.echo("  Uncommitted: No")

        click.echo()
        click.echo("Sync status:")
        click.echo(f"  {current_branch} → {ctx.config.git_branch}: {sync_status.commits_ahead_main} commits ahead")
        click.echo(f"  {ctx.config.git_branch} → {current_branch}: {sync_status.commits_ahead_bodega} commits ahead")

        if sync_status.uncommitted_in_main:
            click.echo(f"\n⚠ Uncommitted changes in .bodega/ on {current_branch}")
            click.echo("  Commit or stash before running 'bodega sync'")

        click.echo()

        # Recommendations
        needs_sync = (sync_status.commits_ahead_main > 0 or
                     sync_status.commits_ahead_bodega > 0 or
                     sync_status.uncommitted_in_worktree)

        if needs_sync and not sync_status.uncommitted_in_main:
            click.echo("Status: Out of sync (run 'bodega sync' to synchronize)")
        elif sync_status.uncommitted_in_main:
            click.echo("Status: Cannot sync (uncommitted changes in .bodega/)")
        else:
            click.echo("Status: In sync")

    except StorageError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
