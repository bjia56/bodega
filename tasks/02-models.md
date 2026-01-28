# Task 02: Ticket Model

## Summary
Implement the Ticket dataclass that represents a ticket's data.

## Dependencies
- Task 01: Project Setup

## Requirements

### 1. Create Ticket Model (`src/bodega/models/ticket.py`)

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum

class TicketType(str, Enum):
    BUG = "bug"
    FEATURE = "feature"
    TASK = "task"
    EPIC = "epic"
    CHORE = "chore"

class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in-progress"
    CLOSED = "closed"

@dataclass
class Ticket:
    id: str
    title: str
    type: TicketType = TicketType.TASK
    status: TicketStatus = TicketStatus.OPEN
    priority: int = 2
    assignee: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    deps: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    parent: Optional[str] = None
    external_ref: Optional[str] = None
    created: datetime = field(default_factory=datetime.utcnow)
    updated: datetime = field(default_factory=datetime.utcnow)

    # Content sections (not in frontmatter)
    description: Optional[str] = None
    design: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    notes: list[str] = field(default_factory=list)
```

### 2. Add Methods to Ticket

```python
def to_frontmatter(self) -> dict:
    """Convert ticket metadata to frontmatter dict."""
    # Return dict with all frontmatter fields
    # Exclude None values and empty lists
    # Convert enums to their string values
    # Convert datetimes to ISO format strings

def to_markdown(self) -> str:
    """Convert full ticket to markdown string with frontmatter."""
    # Use python-frontmatter to generate the file content

@classmethod
def from_dict(cls, data: dict) -> "Ticket":
    """Create Ticket from parsed frontmatter + content dict."""
    # Handle type coercion (strings to enums, ISO strings to datetime)

def is_blocked(self) -> bool:
    """Check if ticket has unresolved dependencies."""
    # Note: This is a placeholder - actual check requires storage access

def add_note(self, text: str) -> None:
    """Add a timestamped note."""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    self.notes.append(f"{timestamp}: {text}")
    self.updated = datetime.utcnow()
```

### 3. Validation

Add validation in `__post_init__`:
- `priority` must be 0-4
- `id` must match pattern `^[a-z]+-[a-f0-9]+$` or be empty (for new tickets)
- `title` must not be empty

### 4. Export in `models/__init__.py`

```python
from .ticket import Ticket, TicketType, TicketStatus

__all__ = ["Ticket", "TicketType", "TicketStatus"]
```

## Acceptance Criteria

- [ ] Can create Ticket with minimal args: `Ticket(id="bg-abc123", title="Test")`
- [ ] Can create Ticket with all args
- [ ] `to_frontmatter()` returns correct dict
- [ ] `to_markdown()` produces valid markdown with YAML frontmatter
- [ ] `from_dict()` correctly parses a dict back to Ticket
- [ ] Validation raises `ValueError` for invalid data
- [ ] Enums serialize to strings, not enum objects

## Test Cases

```python
def test_ticket_minimal():
    t = Ticket(id="bg-abc123", title="Test ticket")
    assert t.type == TicketType.TASK
    assert t.status == TicketStatus.OPEN
    assert t.priority == 2

def test_ticket_to_markdown():
    t = Ticket(id="bg-abc123", title="Test", description="A test ticket")
    md = t.to_markdown()
    assert "---" in md
    assert "id: bg-abc123" in md
    assert "## Description" in md

def test_ticket_roundtrip():
    original = Ticket(id="bg-abc123", title="Test", tags=["api"])
    md = original.to_markdown()
    restored = Ticket.from_dict(parse_markdown(md))  # pseudo
    assert original.id == restored.id
    assert original.tags == restored.tags
```
