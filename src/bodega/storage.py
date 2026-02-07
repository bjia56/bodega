"""Storage module for managing .bodega directory and files."""

from pathlib import Path
from typing import Optional, Iterator
import frontmatter
from contextlib import contextmanager
from filelock import FileLock, Timeout

from bodega.models.ticket import Ticket, TicketStatus
from bodega.config import BodegaConfig, load_config, write_default_config
from bodega.utils import resolve_id, generate_id, now_utc
from bodega.errors import StorageError, TicketNotFoundError, TicketExistsError
from bodega.worktree import auto_commit_ticket


# ============================================================================
# Repository Initialization
# ============================================================================

def init_repository(path: Optional[Path] = None, force: bool = False) -> Path:
    """
    Initialize a new bodega repository.

    Creates .bodega/ directory with config.yaml template.

    Args:
        path: Base directory for the repository (default: current working directory)
        force: If True, overwrite existing repository

    Returns:
        Path to the created .bodega directory

    Raises:
        StorageError: If repository already exists and force=False
    """
    base = path or Path.cwd()
    bodega_dir = base / ".bodega"

    if bodega_dir.exists() and not force:
        raise StorageError(f"Bodega repository already exists at {bodega_dir}")

    bodega_dir.mkdir(parents=True, exist_ok=True)
    write_default_config(bodega_dir / "config.yaml")

    return bodega_dir


# ============================================================================
# Ticket Storage Class
# ============================================================================

class TicketStorage:
    """Handles reading/writing tickets to the filesystem."""

    def __init__(self, config: Optional[BodegaConfig] = None):
        """
        Initialize ticket storage.

        Args:
            config: Optional BodegaConfig. If None, will load from default locations.

        Raises:
            StorageError: If not in a bodega repository
        """
        self.config = config or load_config()
        if not self.config.bodega_dir:
            raise StorageError("Not in a bodega repository. Run 'bodega init' first.")

        # Determine storage mode based on offline_mode and git_branch config
        if self.config.offline_mode:
            # Offline mode - use ~/.bodega/<project>/ store
            self.tickets_dir = self.config.bodega_dir
            self.worktree_path = None
            self.use_worktree = False
            self.is_offline = True
        elif self.config.git_branch:
            # Worktree mode - use separate branch for ticket storage
            worktree_bodega_dir = self.config.bodega_dir / "worktree" / ".bodega"
            self.tickets_dir = worktree_bodega_dir
            self.worktree_path = worktree_bodega_dir.parent  # .bodega/worktree/
            self.use_worktree = True
            self.is_offline = False
        else:
            # Direct mode - store tickets in .bodega/ on current branch
            self.tickets_dir = self.config.bodega_dir
            self.worktree_path = None
            self.use_worktree = False
            self.is_offline = False

    def _ticket_path(self, ticket_id: str) -> Path:
        """
        Get the file path for a ticket ID.

        Args:
            ticket_id: The ticket ID

        Returns:
            Path to the ticket markdown file
        """
        return self.tickets_dir / f"{ticket_id}.md"

    # ========================================================================
    # Reading Tickets
    # ========================================================================

    def get(self, ticket_id: str) -> Ticket:
        """
        Get a ticket by ID (supports partial matching).

        Args:
            ticket_id: Full or partial ticket ID

        Returns:
            The loaded Ticket object

        Raises:
            TicketNotFoundError: If ticket doesn't exist
            AmbiguousIDError: If ID is ambiguous
        """
        full_id = resolve_id(ticket_id, self.list_ids())
        path = self._ticket_path(full_id)

        if not path.exists():
            raise TicketNotFoundError(f"Ticket not found: {full_id}")

        return self._read_ticket(path)

    def _read_ticket(self, path: Path) -> Ticket:
        """
        Read and parse a ticket file.

        Args:
            path: Path to the ticket markdown file

        Returns:
            Parsed Ticket object
        """
        post = frontmatter.load(path)

        # Build ticket from frontmatter + content
        ticket_data = {**post.metadata, "content": post.content}
        return Ticket.from_dict(ticket_data)

    # ========================================================================
    # Writing Tickets
    # ========================================================================

    def save(self, ticket: Ticket, update_timestamp: bool = True) -> Path:
        """
        Save a ticket to disk.

        Updates the 'updated' timestamp automatically.
        Uses file locking to prevent corruption.
        Auto-commits to bodega branch if enabled.

        Args:
            ticket: The ticket to save

        Returns:
            Path to the saved ticket file
        """
        if update_timestamp:
            ticket.updated = now_utc()
        path = self._ticket_path(ticket.id)

        content = ticket.to_markdown()

        with self._file_lock(path):
            path.write_text(content)

        # Auto-commit to bodega branch (only in worktree mode, not offline)
        if self.use_worktree and not self.is_offline and self.config.git_auto_commit:
            auto_commit_ticket(
                self.worktree_path,
                path,
                operation="update",
                ticket_id=ticket.id
            )

        return path

    def create(self, ticket: Ticket, update_timestamp: bool = True) -> Ticket:
        """
        Create a new ticket.

        Generates ID if not set.
        Raises error if ID already exists.
        Auto-commits to bodega branch if enabled.

        Args:
            ticket: The ticket to create

        Returns:
            The created ticket with ID set

        Raises:
            TicketExistsError: If ticket ID already exists
        """
        if not ticket.id:
            ticket.id = generate_id(self.config.id_prefix)

        path = self._ticket_path(ticket.id)
        if path.exists():
            raise TicketExistsError(f"Ticket already exists: {ticket.id}")

        # Set timestamps
        if update_timestamp:
            ticket.updated = now_utc()
        content = ticket.to_markdown()

        with self._file_lock(path):
            path.write_text(content)

        # Auto-commit with create-specific message (only in worktree mode, not offline)
        if self.use_worktree and not self.is_offline and self.config.git_auto_commit:
            auto_commit_ticket(
                self.worktree_path,
                path,
                operation="create",
                ticket_id=ticket.id,
                message=ticket.title
            )

        return ticket

    def delete(self, ticket_id: str) -> None:
        """
        Delete a ticket file.

        Auto-commits deletion to bodega branch if enabled.

        Args:
            ticket_id: Full or partial ticket ID

        Raises:
            TicketNotFoundError: If ticket doesn't exist
            AmbiguousIDError: If ID is ambiguous
        """
        full_id = resolve_id(ticket_id, self.list_ids())
        path = self._ticket_path(full_id)
        path.unlink()

        # Auto-commit deletion (only in worktree mode, not offline)
        if self.use_worktree and not self.is_offline and self.config.git_auto_commit:
            auto_commit_ticket(
                self.worktree_path,
                path,
                operation="delete",
                ticket_id=full_id
            )

    # ========================================================================
    # Listing and Querying
    # ========================================================================

    def list_ids(self) -> list[str]:
        """
        Get all ticket IDs.

        Returns:
            List of ticket IDs (without .md extension)
        """
        return [p.stem for p in self.tickets_dir.glob("*.md")]

    def list_all(self) -> list[Ticket]:
        """
        Get all tickets.

        Returns:
            List of all Ticket objects
        """
        return [self._read_ticket(p) for p in self.tickets_dir.glob("*.md")]

    def query(
        self,
        status: Optional[TicketStatus] = None,
        ticket_type: Optional[str] = None,
        tag: Optional[str] = None,
        assignee: Optional[str] = None,
        priority: Optional[int] = None,
        include_closed: bool = False,
    ) -> Iterator[Ticket]:
        """
        Query tickets with filters.

        By default excludes closed tickets unless include_closed=True.

        Args:
            status: Filter by status
            ticket_type: Filter by type (string value like "bug", "feature")
            tag: Filter by tag (ticket must have this tag)
            assignee: Filter by assignee
            priority: Filter by priority (0-4)
            include_closed: If False, exclude closed tickets

        Yields:
            Tickets matching the filter criteria
        """
        for ticket in self.list_all():
            # Filter by status
            if not include_closed and ticket.status == TicketStatus.CLOSED:
                continue
            if status and ticket.status != status:
                continue

            # Filter by type
            if ticket_type and ticket.type.value != ticket_type:
                continue

            # Filter by tag
            if tag and tag not in ticket.tags:
                continue

            # Filter by assignee
            if assignee and ticket.assignee != assignee:
                continue

            # Filter by priority
            if priority is not None and ticket.priority != priority:
                continue

            yield ticket

    # ========================================================================
    # File Locking
    # ========================================================================

    @contextmanager
    def _file_lock(self, path: Path, timeout: float = 5.0):
        """
        Advisory file lock for safe concurrent writes.

        Uses filelock library for cross-platform compatibility.

        Args:
            path: Path to the file to lock
            timeout: Maximum time to wait for lock acquisition in seconds

        Raises:
            StorageError: If lock cannot be acquired within timeout

        Yields:
            None (context manager)
        """
        path.parent.mkdir(parents=True, exist_ok=True)

        # Create lock file
        lock_path = path.with_suffix(".lock")
        lock = FileLock(lock_path, timeout=timeout)

        try:
            with lock:
                yield
        except Timeout:
            raise StorageError(f"Could not acquire lock on {path}")
