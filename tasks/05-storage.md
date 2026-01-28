# Task 05: Storage Layer

## Summary
Implement file I/O for reading and writing tickets as markdown files with YAML frontmatter.

## Dependencies
- Task 01: Project Setup
- Task 02: Models (Ticket class)
- Task 03: Utils (find_bodega_dir, resolve_id)
- Task 04: Config (BodegaConfig)

## Requirements

### 1. Core Storage Class (`src/bodega/storage.py`)

```python
from pathlib import Path
from typing import Optional, Iterator
import frontmatter
import fcntl
from contextlib import contextmanager

from .models import Ticket, TicketStatus
from .config import BodegaConfig, load_config
from .utils import resolve_id, generate_id

class TicketStorage:
    """Handles reading/writing tickets to the filesystem."""

    def __init__(self, config: Optional[BodegaConfig] = None):
        self.config = config or load_config()
        if not self.config.bodega_dir:
            raise StorageError("Not in a bodega repository. Run 'bodega init' first.")
        self.tickets_dir = self.config.bodega_dir

    def _ticket_path(self, ticket_id: str) -> Path:
        """Get the file path for a ticket ID."""
        return self.tickets_dir / f"{ticket_id}.md"
```

### 2. Reading Tickets

```python
def get(self, ticket_id: str) -> Ticket:
    """
    Get a ticket by ID (supports partial matching).

    Raises:
        TicketNotFoundError: If ticket doesn't exist
        ValueError: If ID is ambiguous
    """
    full_id = resolve_id(ticket_id, self.list_ids())
    path = self._ticket_path(full_id)

    if not path.exists():
        raise TicketNotFoundError(f"Ticket not found: {full_id}")

    return self._read_ticket(path)

def _read_ticket(self, path: Path) -> Ticket:
    """Read and parse a ticket file."""
    post = frontmatter.load(path)

    # Extract content sections from body
    description, design, acceptance, notes = self._parse_body(post.content)

    # Build ticket from frontmatter + parsed content
    return Ticket.from_dict({
        **post.metadata,
        "description": description,
        "design": design,
        "acceptance_criteria": acceptance,
        "notes": notes,
    })

def _parse_body(self, content: str) -> tuple[str, str, str, list[str]]:
    """
    Parse markdown body into sections.

    Returns: (description, design, acceptance_criteria, notes_list)
    """
    # Split on ## headings
    # Description is content before first ## or under ## Description
    # Design is under ## Design
    # Acceptance Criteria is under ## Acceptance Criteria
    # Notes are bullet points under ## Notes
    ...
```

### 3. Writing Tickets

```python
def save(self, ticket: Ticket) -> Path:
    """
    Save a ticket to disk.

    Updates the 'updated' timestamp automatically.
    Uses file locking to prevent corruption.
    """
    ticket.updated = datetime.utcnow()
    path = self._ticket_path(ticket.id)

    content = ticket.to_markdown()

    with self._file_lock(path):
        path.write_text(content)

    return path

def create(self, ticket: Ticket) -> Ticket:
    """
    Create a new ticket.

    Generates ID if not set.
    Raises error if ID already exists.
    """
    if not ticket.id:
        ticket.id = generate_id(self.config.id_prefix)

    path = self._ticket_path(ticket.id)
    if path.exists():
        raise TicketExistsError(f"Ticket already exists: {ticket.id}")

    self.save(ticket)
    return ticket

def delete(self, ticket_id: str) -> None:
    """Delete a ticket file."""
    full_id = resolve_id(ticket_id, self.list_ids())
    path = self._ticket_path(full_id)
    path.unlink()
```

### 4. Listing and Querying

```python
def list_ids(self) -> list[str]:
    """Get all ticket IDs."""
    return [p.stem for p in self.tickets_dir.glob("*.md")]

def list_all(self) -> list[Ticket]:
    """Get all tickets."""
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
```

### 5. File Locking

```python
@contextmanager
def _file_lock(self, path: Path, timeout: float = 5.0):
    """
    Advisory file lock for safe concurrent writes.

    Uses fcntl.flock on Unix systems.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    # Create lock file
    lock_path = path.with_suffix(".lock")

    with open(lock_path, "w") as lock_file:
        try:
            # Try to acquire lock with timeout
            import time
            start = time.time()
            while True:
                try:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.time() - start > timeout:
                        raise StorageError(f"Could not acquire lock on {path}")
                    time.sleep(0.1)

            yield

        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass
```

### 6. Exceptions

```python
class StorageError(Exception):
    """Base exception for storage errors."""
    pass

class TicketNotFoundError(StorageError):
    """Ticket does not exist."""
    pass

class TicketExistsError(StorageError):
    """Ticket already exists."""
    pass
```

### 7. Initialization

```python
def init_repository(path: Optional[Path] = None, force: bool = False) -> Path:
    """
    Initialize a new bodega repository.

    Creates .bodega/ directory with config.yaml template.
    """
    from .config import write_default_config

    base = path or Path.cwd()
    bodega_dir = base / ".bodega"

    if bodega_dir.exists() and not force:
        raise StorageError(f"Bodega repository already exists at {bodega_dir}")

    bodega_dir.mkdir(parents=True, exist_ok=True)
    write_default_config(bodega_dir / "config.yaml")

    return bodega_dir
```

## Acceptance Criteria

- [ ] `TicketStorage` finds `.bodega/` directory automatically
- [ ] `get()` reads and parses ticket files correctly
- [ ] `save()` writes valid markdown with frontmatter
- [ ] `create()` generates new ID and prevents duplicates
- [ ] `query()` filters correctly by all criteria
- [ ] File locking prevents concurrent write corruption
- [ ] `init_repository()` creates proper directory structure
- [ ] Partial ID matching works in `get()`

## Test Cases

```python
def test_roundtrip(tmp_path):
    # Init repo
    init_repository(tmp_path)
    storage = TicketStorage(BodegaConfig(bodega_dir=tmp_path / ".bodega"))

    # Create ticket
    ticket = Ticket(id="", title="Test ticket", description="Test desc")
    created = storage.create(ticket)
    assert created.id.startswith("bg-")

    # Read it back
    loaded = storage.get(created.id)
    assert loaded.title == "Test ticket"
    assert loaded.description == "Test desc"

def test_query_filters(storage_with_tickets):
    storage = storage_with_tickets  # fixture with multiple tickets

    bugs = list(storage.query(ticket_type="bug"))
    assert all(t.type.value == "bug" for t in bugs)

    open_tickets = list(storage.query(status=TicketStatus.OPEN))
    assert all(t.status == TicketStatus.OPEN for t in open_tickets)

def test_partial_id_match(storage_with_tickets):
    storage = storage_with_tickets
    # Assuming a ticket bg-abc123 exists
    ticket = storage.get("abc")
    assert ticket.id == "bg-abc123"
```
