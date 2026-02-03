"""Git worktree management for bodega ticket storage."""

import subprocess
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from bodega.errors import StorageError


@dataclass
class SyncResult:
    """Result of a sync operation."""
    commits_from_main: int
    commits_from_bodega: int
    files_changed: int
    had_conflicts: bool


@dataclass
class SyncStatus:
    """Status of sync between branches."""
    commits_ahead_main: int
    commits_ahead_bodega: int
    uncommitted_in_main: bool
    uncommitted_in_worktree: bool


@dataclass
class PushStatus:
    """Status of push to remote."""
    has_remote: bool
    commits_to_push: int
    commits_to_pull: int
    uncommitted_changes: bool


@dataclass
class PushResult:
    """Result of a push operation."""
    auto_committed: bool
    pulled_commits: int
    pushed_commits: int
    had_conflicts: bool


def _run_git(cmd: list[str], cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
    """
    Run a git command.

    Args:
        cmd: Git command as list (e.g., ['git', 'status'])
        cwd: Working directory for command
        check: Whether to raise exception on non-zero exit

    Returns:
        CompletedProcess result

    Raises:
        StorageError: If command fails and check=True
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check
        )
        return result
    except subprocess.CalledProcessError as e:
        raise StorageError(f"Git command failed: {' '.join(cmd)}\n{e.stderr}")


def _generate_batch_commit_message(worktree_path: Path, prefix: str) -> str:
    """
    Generate a descriptive commit message for batched changes.

    Lists ticket IDs/titles for .md files and other files separately.

    Args:
        worktree_path: Path to worktree root
        prefix: First line of commit message (e.g., "Auto-commit before sync")

    Returns:
        Multi-line commit message with ticket and file details
    """
    import frontmatter

    # Get list of changed files
    result = _run_git(
        ['git', 'diff', '--cached', '--name-only', '.bodega/'],
        cwd=worktree_path,
        check=False
    )

    if result.returncode != 0:
        # No staged changes, return simple message
        return prefix

    changed_files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]

    if not changed_files:
        return prefix

    # Separate ticket files from other files
    ticket_files = []
    other_files = []

    for file_path in changed_files:
        if file_path.endswith('.md') and '.bodega/' in file_path:
            # It's a ticket file - try to read it for title
            full_path = worktree_path / file_path
            if full_path.exists():
                try:
                    post = frontmatter.load(full_path)
                    ticket_id = post.metadata.get('id', full_path.stem)
                    ticket_title = post.metadata.get('title', 'Unknown title')
                    ticket_files.append((ticket_id, ticket_title))
                except Exception:
                    # If we can't read it, just use the filename
                    ticket_files.append((full_path.stem, '(unable to read title)'))
            else:
                # File was deleted - just use the filename
                ticket_files.append((full_path.stem, '(deleted)'))
        else:
            other_files.append(file_path)

    # Build commit message
    lines = [prefix]

    if ticket_files:
        lines.append("")
        lines.append("Tickets:")
        for ticket_id, title in ticket_files:
            lines.append(f"  {ticket_id}: {title}")

    if other_files:
        lines.append("")
        lines.append("Other files:")
        for file_path in other_files:
            lines.append(f"  {file_path}")

    return '\n'.join(lines)


def get_current_branch(repo_root: Path) -> str:
    """
    Get the current git branch name.

    Args:
        repo_root: Path to git repository root

    Returns:
        Current branch name

    Raises:
        StorageError: If not on a branch or git command fails
    """
    result = _run_git(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=repo_root)
    branch = result.stdout.strip()
    if branch == 'HEAD':
        raise StorageError("Not currently on a branch (detached HEAD state)")
    return branch


def init_worktree(repo_root: Path, bodega_dir: Path, branch_name: str = "bodega") -> Path:
    """
    Initialize git worktree for ticket storage.

    Creates:
    - bodega branch from current HEAD (if branch doesn't exist)
    - Worktree at .bodega/worktree/
    - .bodega/.gitignore with worktree/ entry
    - .bodega/worktree/.bodega/ directory for tickets
    - Initial commit on bodega branch (if needed)

    Args:
        repo_root: Path to git repository root
        bodega_dir: Path to .bodega directory
        branch_name: Name of branch to create (default: "bodega")

    Returns:
        Path to worktree's .bodega directory (.bodega/worktree/.bodega/)

    Raises:
        StorageError: If worktree creation fails
    """
    worktree_path = bodega_dir / "worktree"

    # Create .bodega/.gitignore
    gitignore_path = bodega_dir / ".gitignore"
    gitignore_path.write_text("worktree/\n")

    # Check if branch already exists locally
    result = _run_git(['git', 'rev-parse', '--verify', branch_name], cwd=repo_root, check=False)
    branch_exists_locally = result.returncode == 0

    # Check if branch exists on remote
    result = _run_git(['git', 'rev-parse', '--verify', f'origin/{branch_name}'], cwd=repo_root, check=False)
    branch_exists_remotely = result.returncode == 0

    if branch_exists_locally:
        # Branch exists locally, just create worktree
        _run_git(['git', 'worktree', 'add', str(worktree_path), branch_name], cwd=repo_root)
    elif branch_exists_remotely:
        # Branch exists on remote but not locally - create local tracking branch with worktree
        _run_git(['git', 'worktree', 'add', '-b', branch_name, str(worktree_path), f'origin/{branch_name}'], cwd=repo_root)
    else:
        # Create new branch and worktree from current HEAD
        _run_git(['git', 'worktree', 'add', '-b', branch_name, str(worktree_path), 'HEAD'], cwd=repo_root)

    # Create .bodega directory in worktree
    worktree_bodega_dir = worktree_path / ".bodega"
    worktree_bodega_dir.mkdir(parents=True, exist_ok=True)

    # Copy config.yaml to worktree if it exists in main and doesn't exist in worktree
    main_config = bodega_dir / "config.yaml"
    worktree_config = worktree_bodega_dir / "config.yaml"
    if main_config.exists() and not worktree_config.exists():
        worktree_config.write_text(main_config.read_text())

    # Check if there are any commits on the branch
    result = _run_git(['git', 'rev-list', '-n', '1', 'HEAD'], cwd=worktree_path, check=False)
    has_commits = result.returncode == 0 and result.stdout.strip()

    # Only create initial commit if branch is new (no commits yet) and we have something to commit
    if not has_commits or not branch_exists_locally:
        _run_git(['git', 'add', '.bodega/'], cwd=worktree_path)
        _run_git(
            ['git', 'commit', '-m', 'Initialize bodega ticket tracking'],
            cwd=worktree_path,
            check=False  # May fail if nothing to commit or already committed
        )

    return worktree_bodega_dir


def ensure_worktree(bodega_dir: Path, branch_name: str = "bodega") -> Path:
    """
    Ensure worktree exists and is healthy.

    Checks if worktree directory exists and is properly registered.
    If missing or broken, attempts to reinitialize.

    Args:
        bodega_dir: Path to .bodega directory
        branch_name: Name of bodega branch (default: "bodega")

    Returns:
        Path to worktree's .bodega directory

    Raises:
        StorageError: If worktree cannot be created or verified
    """
    from bodega.utils import find_repo_root

    worktree_path = bodega_dir / "worktree"
    worktree_bodega_dir = worktree_path / ".bodega"

    # Check if worktree directory exists
    if not worktree_path.exists():
        # Need to create worktree
        repo_root = find_repo_root()
        if not repo_root:
            raise StorageError("Not in a git repository")
        return init_worktree(Path(repo_root), bodega_dir, branch_name)

    # Check if it's a valid git worktree
    git_file = worktree_path / ".git"
    if not git_file.exists():
        raise StorageError(
            f"Worktree directory exists but is not a valid git worktree: {worktree_path}\n"
            f"Remove the directory and run 'bodega init --force' to reinitialize"
        )

    # Ensure .bodega directory exists in worktree
    if not worktree_bodega_dir.exists():
        worktree_bodega_dir.mkdir(parents=True, exist_ok=True)

    return worktree_bodega_dir


def auto_commit_ticket(
    worktree_path: Path,
    ticket_file: Path,
    operation: str,
    ticket_id: str,
    message: Optional[str] = None
) -> Optional[str]:
    """
    Auto-commit ticket change to bodega branch.

    Args:
        worktree_path: Path to worktree root (.bodega/worktree/)
        ticket_file: Path to ticket file
        operation: Operation type ('create', 'update', 'delete', 'close')
        ticket_id: Ticket ID
        message: Optional additional message (e.g., ticket title)

    Returns:
        Commit SHA, or None if commit failed

    Raises:
        StorageError: If git commands fail
    """
    # Make path relative to worktree for git add
    relative_path = ticket_file.relative_to(worktree_path)

    # Stage the file (or deletion)
    if operation == 'delete':
        _run_git(['git', 'rm', str(relative_path)], cwd=worktree_path, check=False)
    else:
        _run_git(['git', 'add', str(relative_path)], cwd=worktree_path)

    # Format commit message
    if operation == 'create' and message:
        commit_msg = f"Create ticket {ticket_id}: {message}"
    elif operation == 'update':
        commit_msg = f"Update ticket {ticket_id}"
    elif operation == 'close':
        commit_msg = f"Close ticket {ticket_id}"
    elif operation == 'delete':
        commit_msg = f"Delete ticket {ticket_id}"
    else:
        commit_msg = f"{operation.capitalize()} ticket {ticket_id}"

    # Commit
    result = _run_git(
        ['git', 'commit', '-m', commit_msg],
        cwd=worktree_path,
        check=False
    )

    if result.returncode != 0:
        # Commit failed (possibly nothing to commit)
        return None

    # Get commit SHA
    result = _run_git(['git', 'rev-parse', 'HEAD'], cwd=worktree_path)
    return result.stdout.strip()


def has_uncommitted_changes(path: Path, subdir: Optional[str] = None) -> bool:
    """
    Check if there are uncommitted changes in a directory.

    Args:
        path: Path to git repository or worktree
        subdir: Optional subdirectory to check (e.g., '.bodega')

    Returns:
        True if there are uncommitted changes
    """
    cmd = ['git', 'status', '--porcelain']
    if subdir:
        cmd.append(subdir)

    result = _run_git(cmd, cwd=path)
    return bool(result.stdout.strip())


def get_commits_ahead(repo_root: Path, branch1: str, branch2: str) -> int:
    """
    Get number of commits branch1 is ahead of branch2.

    Args:
        repo_root: Path to git repository root
        branch1: First branch name
        branch2: Second branch name

    Returns:
        Number of commits branch1 is ahead of branch2
    """
    result = _run_git(
        ['git', 'rev-list', '--count', f'{branch2}..{branch1}'],
        cwd=repo_root,
        check=False
    )
    if result.returncode != 0:
        return 0
    return int(result.stdout.strip())


def get_sync_status(
    repo_root: Path,
    worktree_path: Path,
    main_branch: str,
    bodega_branch: str
) -> SyncStatus:
    """
    Get sync status between main and bodega branches.

    Args:
        repo_root: Path to git repository root
        worktree_path: Path to worktree root
        main_branch: Main branch name
        bodega_branch: Bodega branch name

    Returns:
        SyncStatus with sync information
    """
    commits_ahead_main = get_commits_ahead(repo_root, main_branch, bodega_branch)
    commits_ahead_bodega = get_commits_ahead(repo_root, bodega_branch, main_branch)
    uncommitted_in_main = has_uncommitted_changes(repo_root, '.bodega')
    uncommitted_in_worktree = has_uncommitted_changes(worktree_path, '.bodega')

    return SyncStatus(
        commits_ahead_main=commits_ahead_main,
        commits_ahead_bodega=commits_ahead_bodega,
        uncommitted_in_main=uncommitted_in_main,
        uncommitted_in_worktree=uncommitted_in_worktree
    )


def sync_branches(
    repo_root: Path,
    worktree_path: Path,
    main_branch: str,
    bodega_branch: str,
    strategy: str = "theirs",
    skip_merge_to_main: bool = False
) -> SyncResult:
    """
    Two-way sync between main and bodega branches.

    1. Commits any uncommitted changes in worktree
    2. Merges main → bodega
    3. Merges bodega → main (unless skip_merge_to_main=True)

    Args:
        repo_root: Path to git repository root
        worktree_path: Path to worktree root
        main_branch: Main branch name
        bodega_branch: Bodega branch name
        strategy: Conflict resolution strategy ('theirs', 'ours', 'manual')
        skip_merge_to_main: If True, only merge main → bodega

    Returns:
        SyncResult with sync statistics

    Raises:
        StorageError: If sync fails or there are uncommitted changes in main
    """
    # Check for uncommitted changes in main's .bodega/
    if has_uncommitted_changes(repo_root, '.bodega'):
        raise StorageError(
            "Uncommitted changes in .bodega/. Commit or stash before syncing.\n\n"
            "Run: git status .bodega/"
        )

    # Commit any uncommitted changes in worktree
    if has_uncommitted_changes(worktree_path, '.bodega'):
        _run_git(['git', 'add', '.bodega/'], cwd=worktree_path)
        commit_msg = _generate_batch_commit_message(worktree_path, 'Auto-commit before sync')
        _run_git(
            ['git', 'commit', '-m', commit_msg],
            cwd=worktree_path,
            check=False
        )

    # Get initial commit counts
    initial_commits_main = get_commits_ahead(repo_root, main_branch, bodega_branch)
    initial_commits_bodega = get_commits_ahead(repo_root, bodega_branch, main_branch)

    had_conflicts = False

    # Step 1: Merge main → bodega (in worktree)
    merge_strategy = []
    if strategy == 'theirs':
        # For main → bodega, we want bodega to win (ours from worktree perspective)
        merge_strategy = ['-X', 'ours']
    elif strategy == 'ours':
        # Main wins
        merge_strategy = ['-X', 'theirs']

    result = _run_git(
        ['git', 'merge', main_branch, '--no-edit'] + merge_strategy,
        cwd=worktree_path,
        check=False
    )
    if result.returncode != 0:
        if strategy == 'manual':
            raise StorageError(
                f"Merge conflict detected. Please resolve manually in {worktree_path}"
            )
        had_conflicts = True

    commits_from_main = initial_commits_main

    if skip_merge_to_main:
        return SyncResult(
            commits_from_main=commits_from_main,
            commits_from_bodega=0,
            files_changed=0,
            had_conflicts=had_conflicts
        )

    # Step 2: Merge bodega → main (in main repo)
    # Switch to main branch (if not already)
    current_branch = get_current_branch(repo_root)
    if current_branch != main_branch:
        _run_git(['git', 'checkout', main_branch], cwd=repo_root)

    # Merge bodega into main
    merge_strategy = []
    if strategy == 'theirs':
        # For bodega → main, we want bodega to win
        merge_strategy = ['-X', 'theirs']
    elif strategy == 'ours':
        # Main wins
        merge_strategy = ['-X', 'ours']

    result = _run_git(
        ['git', 'merge', bodega_branch, '--no-edit'] + merge_strategy,
        cwd=repo_root,
        check=False
    )
    if result.returncode != 0:
        if strategy == 'manual':
            raise StorageError("Merge conflict detected. Please resolve manually.")
        had_conflicts = True

    commits_from_bodega = initial_commits_bodega

    # Count changed files in .bodega/
    result = _run_git(
        ['git', 'diff', '--name-only', 'HEAD', '.bodega/'],
        cwd=repo_root,
        check=False
    )
    files_changed = len([line for line in result.stdout.strip().split('\n') if line])

    return SyncResult(
        commits_from_main=commits_from_main,
        commits_from_bodega=commits_from_bodega,
        files_changed=files_changed,
        had_conflicts=had_conflicts
    )


def cleanup_worktree(worktree_path: Path, repo_root: Path) -> None:
    """
    Remove worktree (for troubleshooting/cleanup).

    Removes worktree directory and git worktree registration.
    Keeps bodega branch intact.

    Args:
        worktree_path: Path to worktree root
        repo_root: Path to git repository root

    Raises:
        StorageError: If cleanup fails
    """
    # Remove worktree registration
    _run_git(['git', 'worktree', 'remove', str(worktree_path)], cwd=repo_root, check=False)

    # Remove directory if still exists
    if worktree_path.exists():
        import shutil
        shutil.rmtree(worktree_path)


def get_push_status(
    repo_root: Path,
    worktree_path: Path,
    bodega_branch: str
) -> PushStatus:
    """
    Get push status for bodega branch to remote.

    Args:
        repo_root: Path to git repository root
        worktree_path: Path to worktree root
        bodega_branch: Bodega branch name

    Returns:
        PushStatus with push information
    """
    # Check if remote branch exists
    result = _run_git(
        ['git', 'ls-remote', '--heads', 'origin', bodega_branch],
        cwd=worktree_path,
        check=False
    )
    has_remote = bool(result.stdout.strip())

    commits_to_push = 0
    commits_to_pull = 0

    if has_remote:
        # Fetch latest remote state
        _run_git(['git', 'fetch', 'origin', bodega_branch], cwd=worktree_path, check=False)

        # Get commits ahead (to push)
        commits_to_push = get_commits_ahead(worktree_path, bodega_branch, f'origin/{bodega_branch}')

        # Get commits behind (to pull)
        commits_to_pull = get_commits_ahead(worktree_path, f'origin/{bodega_branch}', bodega_branch)
    else:
        # No remote - count all commits
        result = _run_git(['git', 'rev-list', '--count', 'HEAD'], cwd=worktree_path, check=False)
        if result.returncode == 0:
            commits_to_push = int(result.stdout.strip())

    uncommitted_changes = has_uncommitted_changes(worktree_path, '.bodega')

    return PushStatus(
        has_remote=has_remote,
        commits_to_push=commits_to_push,
        commits_to_pull=commits_to_pull,
        uncommitted_changes=uncommitted_changes
    )


def push_to_remote(
    repo_root: Path,
    worktree_path: Path,
    bodega_branch: str,
    strategy: str = "theirs"
) -> PushResult:
    """
    Push bodega branch to remote with conflict resolution.

    1. Auto-commits any uncommitted changes
    2. Fetches from remote
    3. Rebases local changes on remote (or merges if rebase fails)
    4. Pushes to remote

    Args:
        repo_root: Path to git repository root
        worktree_path: Path to worktree root
        bodega_branch: Bodega branch name
        strategy: Conflict resolution strategy ('theirs' = local wins, 'ours' = remote wins)

    Returns:
        PushResult with push statistics

    Raises:
        StorageError: If push fails
    """
    auto_committed = False
    pulled_commits = 0
    had_conflicts = False
    pushed_commits = 0

    # Step 1: Commit any uncommitted changes in worktree
    if has_uncommitted_changes(worktree_path, '.bodega'):
        _run_git(['git', 'add', '.bodega/'], cwd=worktree_path)
        commit_msg = _generate_batch_commit_message(worktree_path, 'Auto-commit before push')
        result = _run_git(
            ['git', 'commit', '-m', commit_msg],
            cwd=worktree_path,
            check=False
        )
        auto_committed = result.returncode == 0

    # Step 2: Fetch from remote
    _run_git(['git', 'fetch', 'origin', bodega_branch], cwd=worktree_path, check=False)

    # Step 3: Check if remote exists
    result = _run_git(
        ['git', 'ls-remote', '--heads', 'origin', bodega_branch],
        cwd=worktree_path,
        check=False
    )
    has_remote = bool(result.stdout.strip())

    # Count commits to push BEFORE we sync/push
    if has_remote:
        pushed_commits = get_commits_ahead(worktree_path, bodega_branch, f'origin/{bodega_branch}')
    else:
        # No remote yet - count all commits
        result = _run_git(['git', 'rev-list', '--count', 'HEAD'], cwd=worktree_path, check=False)
        if result.returncode == 0:
            pushed_commits = int(result.stdout.strip())

    if has_remote:
        # Get initial commit count to pull
        pulled_commits = get_commits_ahead(worktree_path, f'origin/{bodega_branch}', bodega_branch)

        if pulled_commits > 0:
            # Try rebase first
            merge_strategy = []
            if strategy == 'theirs':
                # Local wins
                merge_strategy = ['-X', 'ours']
            elif strategy == 'ours':
                # Remote wins
                merge_strategy = ['-X', 'theirs']

            result = _run_git(
                ['git', 'rebase', f'origin/{bodega_branch}'] + merge_strategy,
                cwd=worktree_path,
                check=False
            )

            if result.returncode != 0:
                # Rebase failed, abort and try merge instead
                _run_git(['git', 'rebase', '--abort'], cwd=worktree_path, check=False)

                result = _run_git(
                    ['git', 'merge', f'origin/{bodega_branch}', '--no-edit'] + merge_strategy,
                    cwd=worktree_path,
                    check=False
                )

                if result.returncode != 0:
                    if strategy == 'manual':
                        raise StorageError(
                            f"Merge conflict detected. Please resolve manually in {worktree_path}"
                        )
                    had_conflicts = True

    # Step 4: Set upstream if not set
    result = _run_git(
        ['git', 'rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}'],
        cwd=worktree_path,
        check=False
    )
    if result.returncode != 0 or not result.stdout.strip():
        # No upstream set, set it
        _run_git(
            ['git', 'branch', '--set-upstream-to', f'origin/{bodega_branch}', bodega_branch],
            cwd=worktree_path,
            check=False
        )

    # Step 5: Push to remote
    push_cmd = ['git', 'push']
    if not has_remote:
        # First push - set upstream
        push_cmd.extend(['-u', 'origin', bodega_branch])

    result = _run_git(push_cmd, cwd=worktree_path, check=False)

    if result.returncode != 0:
        raise StorageError(f"Failed to push to remote:\n{result.stderr}")

    return PushResult(
        auto_committed=auto_committed,
        pulled_commits=pulled_commits,
        pushed_commits=pushed_commits,
        had_conflicts=had_conflicts
    )
