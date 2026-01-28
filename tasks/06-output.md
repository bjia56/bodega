# Task 06: Output Formatting

## Summary
Implement output formatting utilities for displaying tickets in various formats (table, compact, ids, JSON).

## Dependencies
- Task 01: Project Setup
- Task 02: Models (Ticket class)
- Task 04: Config (for date_format, list_format)

## Requirements

### 1. Output Module (`src/bodega/output.py`)

```python
import json
import sys
from typing import Iterable, Optional

from .models import Ticket, TicketStatus, TicketType
from .config import BodegaConfig
from .utils import format_datetime

# ANSI color codes (disabled if NO_COLOR env var is set)
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"

    @classmethod
    def enabled(cls) -> bool:
        import os
        return (
            sys.stdout.isatty()
            and "NO_COLOR" not in os.environ
        )

def colorize(text: str, color: str) -> str:
    """Apply color if colors are enabled."""
    if Colors.enabled():
        return f"{color}{text}{Colors.RESET}"
    return text
```

### 2. Status and Priority Colors

```python
def status_color(status: TicketStatus) -> str:
    """Get color for a status."""
    return {
        TicketStatus.OPEN: Colors.YELLOW,
        TicketStatus.IN_PROGRESS: Colors.BLUE,
        TicketStatus.CLOSED: Colors.GREEN,
    }.get(status, "")

def priority_color(priority: int) -> str:
    """Get color for a priority."""
    if priority == 0:
        return Colors.RED + Colors.BOLD
    elif priority == 1:
        return Colors.RED
    elif priority == 2:
        return ""  # normal, no color
    else:
        return Colors.DIM

def type_color(ticket_type: TicketType) -> str:
    """Get color for a ticket type."""
    return {
        TicketType.BUG: Colors.RED,
        TicketType.FEATURE: Colors.GREEN,
        TicketType.TASK: Colors.BLUE,
        TicketType.EPIC: Colors.MAGENTA,
        TicketType.CHORE: Colors.DIM,
    }.get(ticket_type, "")
```

### 3. Table Format

```python
def format_table(
    tickets: Iterable[Ticket],
    config: BodegaConfig,
    show_header: bool = True
) -> str:
    """
    Format tickets as a table.

    ID          TYPE    PRI  STATUS       TITLE
    bg-a1b2c3   bug     1    open         Fix login bug
    bg-d4e5f6   task    2    in-progress  Update docs
    """
    tickets = list(tickets)
    if not tickets:
        return "No tickets found."

    lines = []

    # Header
    if show_header:
        header = f"{'ID':<12} {'TYPE':<8} {'PRI':<4} {'STATUS':<12} TITLE"
        lines.append(colorize(header, Colors.BOLD))

    # Rows
    for t in tickets:
        type_str = colorize(f"{t.type.value:<8}", type_color(t.type))
        pri_str = colorize(f"{t.priority:<4}", priority_color(t.priority))
        status_str = colorize(f"{t.status.value:<12}", status_color(t.status))

        # Truncate title if needed
        title = t.title[:50] + "..." if len(t.title) > 53 else t.title

        lines.append(f"{t.id:<12} {type_str} {pri_str} {status_str} {title}")

    return "\n".join(lines)
```

### 4. Compact Format

```python
def format_compact(tickets: Iterable[Ticket], config: BodegaConfig) -> str:
    """
    Format tickets in compact one-line format.

    bg-a1b2c3 [bug/1] Fix login bug
    bg-d4e5f6 [task/2] Update documentation
    """
    lines = []
    for t in tickets:
        type_pri = colorize(f"[{t.type.value}/{t.priority}]", type_color(t.type))
        lines.append(f"{t.id} {type_pri} {t.title}")
    return "\n".join(lines) if lines else "No tickets found."
```

### 5. IDs Only Format

```python
def format_ids(tickets: Iterable[Ticket], config: BodegaConfig) -> str:
    """Format as IDs only, one per line."""
    ids = [t.id for t in tickets]
    return "\n".join(ids) if ids else ""
```

### 6. JSON Format

```python
def format_json(
    tickets: Iterable[Ticket],
    config: BodegaConfig,
    pretty: bool = True
) -> str:
    """Format tickets as JSON array."""
    data = [ticket_to_dict(t) for t in tickets]
    if pretty:
        return json.dumps(data, indent=2, default=str)
    return json.dumps(data, default=str)

def ticket_to_dict(ticket: Ticket) -> dict:
    """Convert ticket to JSON-serializable dict."""
    return {
        "id": ticket.id,
        "title": ticket.title,
        "type": ticket.type.value,
        "status": ticket.status.value,
        "priority": ticket.priority,
        "assignee": ticket.assignee,
        "tags": ticket.tags,
        "deps": ticket.deps,
        "links": ticket.links,
        "parent": ticket.parent,
        "external_ref": ticket.external_ref,
        "created": ticket.created.isoformat() if ticket.created else None,
        "updated": ticket.updated.isoformat() if ticket.updated else None,
        "description": ticket.description,
        "design": ticket.design,
        "acceptance_criteria": ticket.acceptance_criteria,
        "notes": ticket.notes,
    }
```

### 7. Single Ticket Display

```python
def format_ticket_detail(ticket: Ticket, config: BodegaConfig) -> str:
    """
    Format a single ticket for `bodega show`.

    Shows all fields and content sections.
    """
    lines = []

    # Header
    status_colored = colorize(ticket.status.value, status_color(ticket.status))
    type_colored = colorize(ticket.type.value, type_color(ticket.type))
    lines.append(colorize(f"[{ticket.id}]", Colors.BOLD) + f" {ticket.title}")
    lines.append("")

    # Metadata
    lines.append(f"Type:     {type_colored}")
    lines.append(f"Status:   {status_colored}")
    lines.append(f"Priority: {ticket.priority}")
    if ticket.assignee:
        lines.append(f"Assignee: {ticket.assignee}")
    if ticket.tags:
        lines.append(f"Tags:     {', '.join(ticket.tags)}")
    if ticket.deps:
        lines.append(f"Blocked by: {', '.join(ticket.deps)}")
    if ticket.links:
        lines.append(f"Linked to:  {', '.join(ticket.links)}")
    if ticket.parent:
        lines.append(f"Parent:   {ticket.parent}")
    if ticket.external_ref:
        lines.append(f"External: {ticket.external_ref}")

    lines.append(f"Created:  {format_datetime(ticket.created, config.date_format)}")
    lines.append(f"Updated:  {format_datetime(ticket.updated, config.date_format)}")

    # Content sections
    if ticket.description:
        lines.append("")
        lines.append(colorize("## Description", Colors.BOLD))
        lines.append(ticket.description)

    if ticket.design:
        lines.append("")
        lines.append(colorize("## Design", Colors.BOLD))
        lines.append(ticket.design)

    if ticket.acceptance_criteria:
        lines.append("")
        lines.append(colorize("## Acceptance Criteria", Colors.BOLD))
        lines.append(ticket.acceptance_criteria)

    if ticket.notes:
        lines.append("")
        lines.append(colorize("## Notes", Colors.BOLD))
        for note in ticket.notes:
            lines.append(f"- {note}")

    return "\n".join(lines)
```

### 8. Format Dispatcher

```python
def format_tickets(
    tickets: Iterable[Ticket],
    config: BodegaConfig,
    fmt: Optional[str] = None
) -> str:
    """
    Format tickets using the specified or configured format.

    Args:
        tickets: Tickets to format
        config: Bodega configuration
        fmt: Format override (table, compact, ids, json)
    """
    fmt = fmt or config.list_format

    if fmt == "table":
        return format_table(tickets, config)
    elif fmt == "compact":
        return format_compact(tickets, config)
    elif fmt == "ids":
        return format_ids(tickets, config)
    elif fmt == "json":
        return format_json(tickets, config)
    else:
        return format_table(tickets, config)
```

## Acceptance Criteria

- [ ] Table format aligns columns properly
- [ ] Colors are disabled when `NO_COLOR` is set
- [ ] Colors are disabled when stdout is not a TTY
- [ ] JSON output is valid and complete
- [ ] `format_ticket_detail` shows all ticket fields
- [ ] Empty ticket lists produce appropriate message
- [ ] Long titles are truncated in table view

## Test Cases

```python
def test_format_table():
    tickets = [
        Ticket(id="bg-abc123", title="Test", type=TicketType.BUG, priority=1),
        Ticket(id="bg-def456", title="Another", type=TicketType.TASK, priority=2),
    ]
    output = format_table(tickets, BodegaConfig())
    assert "bg-abc123" in output
    assert "bg-def456" in output
    assert "bug" in output

def test_format_json():
    tickets = [Ticket(id="bg-abc123", title="Test")]
    output = format_json(tickets, BodegaConfig())
    data = json.loads(output)
    assert len(data) == 1
    assert data[0]["id"] == "bg-abc123"

def test_no_color(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    assert not Colors.enabled()

def test_format_empty():
    output = format_table([], BodegaConfig())
    assert "No tickets" in output
```
