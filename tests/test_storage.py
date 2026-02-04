"""Tests for storage module."""

import pytest
import threading
import time

from bodega.storage import TicketStorage, init_repository
from bodega.errors import (
    StorageError,
    TicketNotFoundError,
    TicketExistsError,
    AmbiguousIDError,
)
from bodega.models.ticket import Ticket, TicketStatus, TicketType
from bodega.config import BodegaConfig


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary bodega repository."""
    bodega_dir = init_repository(tmp_path)
    return tmp_path, bodega_dir


@pytest.fixture
def storage(temp_repo):
    """Create a TicketStorage instance with temp repo."""
    tmp_path, bodega_dir = temp_repo
    config = BodegaConfig(bodega_dir=bodega_dir)
    return TicketStorage(config)


@pytest.fixture
def sample_ticket():
    """Create a sample ticket for testing."""
    return Ticket(
        id="",
        title="Test ticket",
        description="Test description",
        type=TicketType.TASK,
        status=TicketStatus.OPEN,
        priority=2,
    )


@pytest.fixture
def storage_with_tickets(storage):
    """Create storage with multiple test tickets with fixed IDs."""
    tickets = [
        Ticket(
            id="bg-aaa111",  # Fixed ID - starts with 'a'
            title="Bug fix",
            description="Fix the bug",
            type=TicketType.BUG,
            status=TicketStatus.OPEN,
            priority=1,
            tags=["urgent"],
        ),
        Ticket(
            id="bg-bbb222",  # Fixed ID - starts with 'b'
            title="New feature",
            description="Add new feature",
            type=TicketType.FEATURE,
            status=TicketStatus.IN_PROGRESS,
            priority=2,
            assignee="alice",
        ),
        Ticket(
            id="bg-ccc333",  # Fixed ID - starts with 'c'
            title="Closed task",
            description="Already done",
            type=TicketType.TASK,
            status=TicketStatus.CLOSED,
            priority=3,
        ),
        Ticket(
            id="bg-ddd444",  # Fixed ID - starts with 'd'
            title="Another bug",
            description="Another bug to fix",
            type=TicketType.BUG,
            status=TicketStatus.OPEN,
            priority=0,
            tags=["urgent", "security"],
            assignee="bob",
        ),
    ]

    created_tickets = []
    for ticket in tickets:
        # Use save instead of create since we're providing IDs
        storage.save(ticket)
        created_tickets.append(ticket)

    return storage, created_tickets


# ============================================================================
# Repository Initialization Tests
# ============================================================================

def test_init_repository(tmp_path):
    """Test repository initialization."""
    bodega_dir = init_repository(tmp_path)

    assert bodega_dir.exists()
    assert bodega_dir.is_dir()
    assert (bodega_dir / "config.yaml").exists()


def test_init_repository_already_exists(tmp_path):
    """Test that init fails when repository already exists."""
    init_repository(tmp_path)

    with pytest.raises(StorageError, match="already exists"):
        init_repository(tmp_path)


def test_init_repository_force(tmp_path):
    """Test that force=True allows reinitializing (used by --reset flag)."""
    init_repository(tmp_path)
    bodega_dir = init_repository(tmp_path, force=True)

    assert bodega_dir.exists()


# ============================================================================
# Storage Initialization Tests
# ============================================================================

def test_storage_init_without_repo(tmp_path):
    """Test that TicketStorage fails without a bodega repo."""
    config = BodegaConfig(bodega_dir=None)

    with pytest.raises(StorageError, match="Not in a bodega repository"):
        TicketStorage(config)


def test_storage_init_with_repo(storage):
    """Test successful TicketStorage initialization."""
    assert storage.config.bodega_dir is not None
    assert storage.tickets_dir.exists()


# ============================================================================
# Create and Save Tests
# ============================================================================

def test_create_ticket(storage, sample_ticket):
    """Test creating a new ticket."""
    created = storage.create(sample_ticket)

    assert created.id.startswith("bg-")
    assert len(created.id) == 9  # bg- + 6 hex chars

    # Verify file exists
    path = storage._ticket_path(created.id)
    assert path.exists()


def test_create_ticket_with_custom_prefix(temp_repo, sample_ticket):
    """Test creating a ticket with custom ID prefix."""
    tmp_path, bodega_dir = temp_repo
    config = BodegaConfig(bodega_dir=bodega_dir, id_prefix="tk")
    storage = TicketStorage(config)

    created = storage.create(sample_ticket)
    assert created.id.startswith("tk-")


def test_create_ticket_duplicate_id(storage, sample_ticket):
    """Test that creating a ticket with duplicate ID fails."""
    created = storage.create(sample_ticket)

    duplicate = Ticket(
        id=created.id,
        title="Duplicate",
        description="Should fail",
    )

    with pytest.raises(TicketExistsError, match="already exists"):
        storage.create(duplicate)


def test_save_ticket_updates_timestamp(storage, sample_ticket):
    """Test that saving updates the timestamp."""
    created = storage.create(sample_ticket)
    original_updated = created.updated

    # Wait a tiny bit and save again
    time.sleep(0.01)

    storage.save(created)

    # Reload and check timestamp
    loaded = storage.get(created.id)
    assert loaded.updated > original_updated


# ============================================================================
# Read Tests
# ============================================================================

def test_roundtrip(storage, sample_ticket):
    """Test that we can create and read back a ticket."""
    created = storage.create(sample_ticket)

    loaded = storage.get(created.id)

    assert loaded.id == created.id
    assert loaded.title == "Test ticket"
    assert loaded.description == "Test description"
    assert loaded.type == TicketType.TASK
    assert loaded.status == TicketStatus.OPEN
    assert loaded.priority == 2


def test_roundtrip_with_all_fields(storage):
    """Test roundtrip with all ticket fields populated."""
    ticket = Ticket(
        id="",
        title="Complete ticket",
        description="Full description",
        design="Design notes",
        acceptance_criteria="Must work",
        notes=["Note 1", "Note 2"],
        type=TicketType.FEATURE,
        status=TicketStatus.IN_PROGRESS,
        priority=1,
        assignee="alice",
        tags=["frontend", "urgent"],
        deps=["bg-abc123"],
        links=["https://example.com"],
        parent="bg-parent",
        external_ref="JIRA-123",
    )

    created = storage.create(ticket)
    loaded = storage.get(created.id)

    assert loaded.title == "Complete ticket"
    assert loaded.description == "Full description"
    assert loaded.design == "Design notes"
    assert loaded.acceptance_criteria == "Must work"
    assert loaded.notes == ["Note 1", "Note 2"]
    assert loaded.assignee == "alice"
    assert loaded.tags == ["frontend", "urgent"]
    assert loaded.deps == ["bg-abc123"]
    assert loaded.links == ["https://example.com"]
    assert loaded.parent == "bg-parent"
    assert loaded.external_ref == "JIRA-123"


def test_get_nonexistent_ticket(storage):
    """Test getting a ticket that doesn't exist."""
    with pytest.raises(TicketNotFoundError):
        storage.get("bg-nonexistent")


def test_get_partial_id(storage_with_tickets):
    """Test getting a ticket with partial ID."""
    storage, _ = storage_with_tickets

    # Test various partial matches with our fixed IDs
    # bg-aaa111
    loaded = storage.get("bg-a")
    assert loaded.id == "bg-aaa111"
    assert loaded.title == "Bug fix"

    # bg-bbb222
    loaded = storage.get("bg-b")
    assert loaded.id == "bg-bbb222"
    assert loaded.title == "New feature"

    # Longer partial
    loaded = storage.get("bg-ccc")
    assert loaded.id == "bg-ccc333"
    assert loaded.title == "Closed task"


def test_get_ambiguous_id(storage_with_tickets):
    """Test that ambiguous partial ID raises error."""
    storage, tickets = storage_with_tickets

    # This should work - get by just prefix
    # But if there are multiple tickets, it will be ambiguous
    if len(tickets) > 1:
        # Try to get with just the prefix (should be ambiguous)
        with pytest.raises(AmbiguousIDError, match="Ambiguous"):
            storage.get("bg")


# ============================================================================
# Delete Tests
# ============================================================================

def test_delete_ticket(storage, sample_ticket):
    """Test deleting a ticket."""
    created = storage.create(sample_ticket)
    path = storage._ticket_path(created.id)

    assert path.exists()

    storage.delete(created.id)

    assert not path.exists()


def test_delete_with_partial_id(storage_with_tickets):
    """Test deleting with partial ID."""
    storage, _ = storage_with_tickets

    # Delete bg-aaa111 using partial ID
    storage.delete("bg-a")

    with pytest.raises(TicketNotFoundError):
        storage.get("bg-aaa111")


# ============================================================================
# List Tests
# ============================================================================

def test_list_ids_empty(storage):
    """Test listing IDs in empty repository."""
    ids = storage.list_ids()
    assert ids == []


def test_list_ids(storage_with_tickets):
    """Test listing all ticket IDs."""
    storage, tickets = storage_with_tickets

    ids = storage.list_ids()

    assert len(ids) == len(tickets)
    for ticket in tickets:
        assert ticket.id in ids


def test_list_all(storage_with_tickets):
    """Test listing all tickets."""
    storage, tickets = storage_with_tickets

    all_tickets = storage.list_all()

    assert len(all_tickets) == len(tickets)

    titles = [t.title for t in all_tickets]
    assert "Bug fix" in titles
    assert "New feature" in titles


# ============================================================================
# Query Tests
# ============================================================================

def test_query_no_filters(storage_with_tickets):
    """Test query with no filters (excludes closed by default)."""
    storage, tickets = storage_with_tickets

    results = list(storage.query())

    # Should exclude closed tickets by default
    assert len(results) == 3  # 4 total - 1 closed
    assert all(t.status != TicketStatus.CLOSED for t in results)


def test_query_include_closed(storage_with_tickets):
    """Test query including closed tickets."""
    storage, tickets = storage_with_tickets

    results = list(storage.query(include_closed=True))

    assert len(results) == 4


def test_query_by_status(storage_with_tickets):
    """Test filtering by status."""
    storage, tickets = storage_with_tickets

    open_tickets = list(storage.query(status=TicketStatus.OPEN))
    in_progress = list(storage.query(status=TicketStatus.IN_PROGRESS))

    assert len(open_tickets) == 2
    assert all(t.status == TicketStatus.OPEN for t in open_tickets)

    assert len(in_progress) == 1
    assert in_progress[0].title == "New feature"


def test_query_by_type(storage_with_tickets):
    """Test filtering by ticket type."""
    storage, tickets = storage_with_tickets

    bugs = list(storage.query(ticket_type="bug"))

    assert len(bugs) == 2
    assert all(t.type == TicketType.BUG for t in bugs)


def test_query_by_tag(storage_with_tickets):
    """Test filtering by tag."""
    storage, tickets = storage_with_tickets

    urgent = list(storage.query(tag="urgent"))

    assert len(urgent) == 2

    security = list(storage.query(tag="security"))
    assert len(security) == 1
    assert security[0].title == "Another bug"


def test_query_by_assignee(storage_with_tickets):
    """Test filtering by assignee."""
    storage, tickets = storage_with_tickets

    alice_tickets = list(storage.query(assignee="alice"))
    bob_tickets = list(storage.query(assignee="bob"))

    assert len(alice_tickets) == 1
    assert alice_tickets[0].title == "New feature"

    assert len(bob_tickets) == 1
    assert bob_tickets[0].title == "Another bug"


def test_query_by_priority(storage_with_tickets):
    """Test filtering by priority."""
    storage, tickets = storage_with_tickets

    p0 = list(storage.query(priority=0))
    p1 = list(storage.query(priority=1))

    assert len(p0) == 1
    assert p0[0].priority == 0

    assert len(p1) == 1
    assert p1[0].priority == 1


def test_query_multiple_filters(storage_with_tickets):
    """Test combining multiple filters."""
    storage, tickets = storage_with_tickets

    # Bug + urgent tag
    results = list(storage.query(ticket_type="bug", tag="urgent"))

    assert len(results) == 2
    assert all(t.type == TicketType.BUG for t in results)
    assert all("urgent" in t.tags for t in results)


# ============================================================================
# File Locking Tests
# ============================================================================

def test_file_lock_basic(storage, sample_ticket):
    """Test that file locking works for basic save."""
    created = storage.create(sample_ticket)

    # Should be able to save without issue
    created.title = "Updated title"
    storage.save(created)

    loaded = storage.get(created.id)
    assert loaded.title == "Updated title"


def test_file_lock_concurrent_writes(storage, sample_ticket):
    """Test file locking with simulated concurrent writes."""
    created = storage.create(sample_ticket)
    results = []
    errors = []

    def writer(suffix):
        try:
            ticket = storage.get(created.id)
            ticket.title = f"Updated {suffix}"
            time.sleep(0.01)  # Simulate some work
            storage.save(ticket)
            results.append(suffix)
        except Exception as e:
            errors.append(e)

    # Start multiple threads trying to write
    threads = []
    for i in range(3):
        t = threading.Thread(target=writer, args=(f"thread-{i}",))
        threads.append(t)
        t.start()

    # Wait for all threads
    for t in threads:
        t.join()

    # All writes should succeed (locking prevents corruption)
    assert len(errors) == 0
    assert len(results) == 3

    # Final ticket should have one of the updates
    final = storage.get(created.id)
    assert final.title.startswith("Updated thread-")


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

def test_empty_title_validation(storage):
    """Test that tickets with empty titles are rejected."""
    with pytest.raises(ValueError, match="must not be empty"):
        Ticket(id="", title="", description="Test")


def test_invalid_priority(storage):
    """Test that invalid priority is rejected."""
    with pytest.raises(ValueError, match="Priority must be 0-4"):
        Ticket(id="", title="Test", priority=5)


def test_ticket_path_method(storage):
    """Test _ticket_path method."""
    path = storage._ticket_path("bg-abc123")

    assert path.name == "bg-abc123.md"
    assert path.parent == storage.tickets_dir
