import pytest
from datetime import datetime, UTC
from enum import Enum
import frontmatter
from bodega.models import Ticket, TicketType, TicketStatus


def test_ticket_minimal():
    """Test creating a ticket with minimal arguments."""
    t = Ticket(id="bg-abc123", title="Test ticket")
    assert t.id == "bg-abc123"
    assert t.title == "Test ticket"
    assert t.type == TicketType.TASK
    assert t.status == TicketStatus.OPEN
    assert t.priority == 2
    assert t.assignee is None
    assert t.tags == []
    assert t.deps == []
    assert t.links == []
    assert t.parent is None
    assert t.external_ref is None
    assert t.description is None
    assert t.design is None
    assert t.acceptance_criteria is None
    assert t.notes == []


def test_ticket_all_args():
    """Test creating a ticket with all arguments."""
    created = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    updated = datetime(2024, 1, 2, 12, 0, 0, tzinfo=UTC)

    t = Ticket(
        id="bg-abc123",
        title="Full ticket",
        type=TicketType.FEATURE,
        status=TicketStatus.IN_PROGRESS,
        priority=4,
        assignee="alice",
        tags=["api", "backend"],
        deps=["bg-def456"],
        links=["https://example.com"],
        parent="bg-xyz789",
        external_ref="JIRA-123",
        created=created,
        updated=updated,
        description="A test description",
        design="Design notes",
        acceptance_criteria="AC notes",
        notes=["Note 1", "Note 2"],
    )

    assert t.id == "bg-abc123"
    assert t.title == "Full ticket"
    assert t.type == TicketType.FEATURE
    assert t.status == TicketStatus.IN_PROGRESS
    assert t.priority == 4
    assert t.assignee == "alice"
    assert t.tags == ["api", "backend"]
    assert t.deps == ["bg-def456"]
    assert t.links == ["https://example.com"]
    assert t.parent == "bg-xyz789"
    assert t.external_ref == "JIRA-123"
    assert t.created == created
    assert t.updated == updated
    assert t.description == "A test description"
    assert t.design == "Design notes"
    assert t.acceptance_criteria == "AC notes"
    assert t.notes == ["Note 1", "Note 2"]


def test_ticket_validation_priority():
    """Test that invalid priority raises ValueError."""
    with pytest.raises(ValueError, match="Priority must be 0-4"):
        Ticket(id="bg-abc123", title="Test", priority=5)

    with pytest.raises(ValueError, match="Priority must be 0-4"):
        Ticket(id="bg-abc123", title="Test", priority=-1)


def test_ticket_validation_title():
    """Test that empty title raises ValueError."""
    with pytest.raises(ValueError, match="Title must not be empty"):
        Ticket(id="bg-abc123", title="")

    with pytest.raises(ValueError, match="Title must not be empty"):
        Ticket(id="bg-abc123", title="   ")


def test_ticket_validation_id():
    """Test that invalid ID pattern raises ValueError."""
    # Valid patterns
    Ticket(id="bg-abc123", title="Test")
    Ticket(id="feature-def456", title="Test")
    Ticket(id="", title="Test")  # Empty is allowed for new tickets

    # Invalid patterns
    with pytest.raises(ValueError, match="ID must match pattern"):
        Ticket(id="BG-ABC123", title="Test")  # uppercase

    with pytest.raises(ValueError, match="ID must match pattern"):
        Ticket(id="bg_abc123", title="Test")  # underscore

    with pytest.raises(ValueError, match="ID must match pattern"):
        Ticket(id="abc123", title="Test")  # no prefix

    with pytest.raises(ValueError, match="ID must match pattern"):
        Ticket(id="bg-xyz789", title="Test")  # invalid hex char


def test_ticket_to_frontmatter():
    """Test converting ticket to frontmatter dict."""
    t = Ticket(
        id="bg-abc123",
        title="Test ticket",
        type=TicketType.BUG,
        status=TicketStatus.CLOSED,
        priority=3,
        tags=["api"],
        assignee="bob",
    )

    fm = t.to_frontmatter()

    assert fm["id"] == "bg-abc123"
    assert fm["title"] == "Test ticket"
    assert fm["type"] == "bug"
    assert fm["status"] == "closed"
    assert fm["priority"] == 3
    assert fm["tags"] == ["api"]
    assert fm["assignee"] == "bob"
    assert "created" in fm
    assert "updated" in fm
    # Empty lists/None should not be in frontmatter
    assert "deps" not in fm
    assert "links" not in fm
    assert "parent" not in fm


def test_ticket_to_markdown():
    """Test converting ticket to markdown with frontmatter."""
    t = Ticket(
        id="bg-abc123",
        title="Test",
        description="A test ticket",
        design="Some design",
    )

    md = t.to_markdown()

    # Check for frontmatter delimiters
    assert md.startswith("---\n")
    assert "---" in md

    # Check for frontmatter content
    assert "id: bg-abc123" in md
    assert "title: Test" in md

    # Check for content sections
    assert "## Description" in md
    assert "A test ticket" in md
    assert "## Design" in md
    assert "Some design" in md


def test_ticket_to_markdown_with_notes():
    """Test markdown generation with notes."""
    t = Ticket(
        id="bg-abc123",
        title="Test",
        notes=["First note", "Second note"],
    )

    md = t.to_markdown()

    assert "## Notes" in md
    assert "- First note" in md
    assert "- Second note" in md


def test_ticket_from_dict():
    """Test creating ticket from dict."""
    data = {
        "id": "bg-abc123",
        "title": "Test ticket",
        "type": "feature",
        "status": "in-progress",
        "priority": 1,
        "tags": ["api", "backend"],
        "assignee": "alice",
        "created": "2024-01-01T12:00:00+00:00",
        "updated": "2024-01-02T12:00:00+00:00",
        "content": "## Description\n\nA test description\n\n## Notes\n\n- Note 1\n- Note 2",
    }

    t = Ticket.from_dict(data)

    assert t.id == "bg-abc123"
    assert t.title == "Test ticket"
    assert t.type == TicketType.FEATURE
    assert t.status == TicketStatus.IN_PROGRESS
    assert t.priority == 1
    assert t.tags == ["api", "backend"]
    assert t.assignee == "alice"
    assert t.created == datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    assert t.updated == datetime(2024, 1, 2, 12, 0, 0, tzinfo=UTC)
    assert t.description == "A test description"
    assert t.notes == ["Note 1", "Note 2"]


def test_ticket_roundtrip():
    """Test that ticket can be converted to markdown and back."""
    original = Ticket(
        id="bg-abc123",
        title="Test",
        tags=["api"],
        description="Test description",
        acceptance_criteria="Must work",
    )

    # Convert to markdown
    md = original.to_markdown()

    # Parse back using frontmatter
    post = frontmatter.loads(md)
    data = dict(post.metadata)
    data["content"] = post.content

    # Convert back to ticket
    restored = Ticket.from_dict(data)

    assert original.id == restored.id
    assert original.title == restored.title
    assert original.tags == restored.tags
    assert original.type == restored.type
    assert original.status == restored.status
    assert original.priority == restored.priority
    assert original.description == restored.description
    assert original.acceptance_criteria == restored.acceptance_criteria


def test_ticket_is_blocked():
    """Test is_blocked method."""
    t1 = Ticket(id="bg-abc123", title="Test")
    assert not t1.is_blocked()

    t2 = Ticket(id="bg-abc123", title="Test", deps=["bg-def456"])
    assert t2.is_blocked()


def test_ticket_add_note():
    """Test adding a note to a ticket."""
    t = Ticket(id="bg-abc123", title="Test")
    original_updated = t.updated

    t.add_note("This is a test note")

    assert len(t.notes) == 1
    assert "This is a test note" in t.notes[0]
    assert t.updated > original_updated

    # Add another note
    t.add_note("Second note")
    assert len(t.notes) == 2
    assert "Second note" in t.notes[1]


def test_ticket_enum_serialization():
    """Test that enums serialize to strings, not enum objects."""
    t = Ticket(id="bg-abc123", title="Test", type=TicketType.EPIC)

    fm = t.to_frontmatter()
    assert fm["type"] == "epic"
    assert not isinstance(fm["type"], Enum)
    assert isinstance(fm["type"], str)


def test_ticket_string_enum_conversion():
    """Test that string enums are converted to proper enum instances."""
    # This happens in from_dict
    data = {
        "id": "bg-abc123",
        "title": "Test",
        "type": "chore",
        "status": "open",
    }

    t = Ticket.from_dict(data)
    assert isinstance(t.type, TicketType)
    assert t.type == TicketType.CHORE
    assert isinstance(t.status, TicketStatus)
    assert t.status == TicketStatus.OPEN
