# Bodega - Agent Development Guide

Essential guide for AI coding agents working in this repository.

## Project Overview

Bodega is a Git-native issue tracking system written in Python 3.11+.
- Stack: Click (CLI), YAML (config), python-frontmatter (ticket storage)
- Tickets are Markdown files with YAML frontmatter in `.bodega/` directory
- Git worktree workflow with dedicated `bodega` branch

## Build & Test Commands

### Installation
```bash
pip install -e '.[dev]'     # Dev mode with all dependencies
pip install -e .            # Runtime dependencies only
```

### Testing
```bash
pytest                                      # Run all tests (default: -v --tb=short)
pytest tests/test_ticket.py                 # Run specific file
pytest tests/test_ticket.py::test_minimal   # Run single test
pytest -k "test_create"                     # Run tests matching pattern
```

### CLI Usage
```bash
python -m bodega --help     # Development
bodega --help               # After install
bodega --debug <command>    # Enable debug output
```

### Build
```bash
python -m build             # Creates dist/bodega-*.whl
```

## Code Style & Conventions

### Imports (Always separate with blank lines)
```python
# 1. Standard library
import subprocess
from pathlib import Path
from datetime import datetime, UTC

# 2. Third-party
import click
import frontmatter
import yaml

# 3. Local (absolute imports only)
from bodega.models import Ticket
from bodega.utils import generate_id, now_utc
from bodega.errors import TicketNotFoundError
```

### Type Hints (Python 3.11+ syntax)
```python
from typing import Optional  # Only for complex types

def resolve_id(partial: str, all_ids: list[str]) -> str:  # Use list[T], dict[K,V]
    ...

def find_dir(start: Optional[Path] = None) -> Path | None:  # Use T | None when simple
    ...
```

### Naming
- **Files**: `snake_case.py` (e.g., `list_cmd.py`, `import_cmd.py`)
- **Classes**: `PascalCase` (e.g., `Ticket`, `TicketStorage`)
- **Functions/Methods**: `snake_case` (e.g., `generate_id`, `from_dict`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_PREFIX`, `TEMPLATE`)
- **Private**: `_leading_underscore`
- **Enums**: PascalCase class, UPPER values (e.g., `TicketType.TASK`)

### Docstrings (Google style)
```python
def generate_id(prefix: str = DEFAULT_PREFIX) -> str:
    """
    Generate a new ticket ID.

    Format: {prefix}-{6 hex chars}. Example: bg-a1b2c3

    Args:
        prefix: The prefix for the ID (default: "bg")

    Returns:
        A new ticket ID in the format {prefix}-{6 hex chars}
    """
```

### Dataclasses
```python
from dataclasses import dataclass, field

@dataclass
class Ticket:
    id: str
    title: str
    tags: list[str] = field(default_factory=list)  # Mutable defaults
    created: datetime = field(default_factory=now_utc)

    def __post_init__(self):
        # Validation and type coercion
        if not self.title.strip():
            raise ValueError("Title must not be empty")
        if isinstance(self.type, str):
            self.type = TicketType(self.type)
```

### Error Handling
```python
from bodega.errors import TicketNotFoundError, AmbiguousIDError  # All inherit from BodegaError
from bodega.commands.utils import require_repo, handle_error

@click.command()
@pass_context
def show(ctx: Context, ticket_id: str):
    storage = require_repo(ctx)  # Auto-exits if not in repo
    try:
        ticket = storage.get(ticket_id)
    except TicketNotFoundError as e:
        handle_error(ctx, e)
```

### Click Commands
```python
from bodega.commands.utils import pass_context, Context

@click.command()
@click.help_option("-h", "--help", help="Show this message and exit")  # Always include
@click.argument("ticket_id", metavar="ID")
@click.option("--priority", "-p", type=int, help="Priority (0-4)")
@pass_context
def edit(ctx: Context, ticket_id: str, priority: int | None):
    """Edit ticket properties."""
    storage = require_repo(ctx)
    # Implementation...
```

**Shared decorators**: `ticket_id_argument`, `filter_options`, `format_option`
**Command location**: `src/bodega/commands/`, register in `src/bodega/cli.py`

### Code Organization
```python
# ============================================================================
# Section Name (80-char lines)
# ============================================================================
```

### Testing
```python
# Key fixtures (from tests/conftest.py):
# - runner: Click CliRunner
# - temp_repo: Temp bodega repo (no git)
# - temp_git_repo: Temp git repo with initial commit
# - storage: TicketStorage instance
# - sample_ticket: Dict with sample data
# - tmp_bodega_with_tickets: Pre-populated repo

def test_ticket_minimal():
    """Test creating a ticket with minimal arguments."""
    t = Ticket(id="bg-abc123", title="Test ticket")
    assert t.id == "bg-abc123"
    assert t.type == TicketType.TASK

def test_create_command(runner, temp_repo):
    """Test create command via CLI."""
    result = runner.invoke(main, ["create", "New ticket"])
    assert result.exit_code == 0
```

## File Structure
```
src/bodega/
├── cli.py              # Main CLI group, command registration
├── models/ticket.py    # Ticket dataclass, enums (TicketType, TicketStatus)
├── commands/           # Command implementations
│   ├── utils.py        # Context, pass_context, error handling, shared decorators
│   ├── lifecycle.py    # start, close, reopen, status
│   ├── list_cmd.py     # list, ready, blocked, closed, query
│   └── ...
├── storage.py          # TicketStorage, init_repository
├── config.py           # BodegaConfig, load_config
├── worktree.py         # Git worktree operations
├── errors.py           # BodegaError, TicketNotFoundError, etc.
├── utils.py            # ID gen/validation, datetime, git utils
└── output.py           # Output formatting

tests/
├── conftest.py         # Shared fixtures
└── test_*.py           # Test modules
```

## Important Domain Rules

### Ticket IDs
- Pattern: `^[a-z][a-z0-9]*-[a-z0-9\.]+$` (e.g., `bg-abc123`)
- Generate: `generate_id(prefix)` from `bodega.utils`
- Validate: `is_valid_id(id_str)`
- Resolve partial: `resolve_id(partial, all_ids)`

### Timestamps
```python
from datetime import datetime, UTC
from bodega.utils import now_utc

# ALWAYS use now_utc(), NEVER datetime.utcnow() (deprecated)
created = now_utc()
# Store as ISO 8601: created.isoformat()
```

### Ticket Properties
- **Types** (TicketType enum): `bug`, `feature`, `task`, `epic`, `chore`
- **Statuses** (TicketStatus enum): `open`, `in-progress`, `closed`
- **Priority**: 0-4 (0=critical, 1=high, 2=normal, 3=low, 4=backlog)
- **Dependencies**: List of IDs in `deps` field (blocks this ticket)
- **Links**: Symmetric relationships (related tickets)

## CI/CD
- Runs on: push to `main`, pull requests
- Python: 3.11
- Workflow: `.github/workflows/test.yml`

## Issue Tracking
This project uses `bodega` for issue tracking. Run `bodega howto` for AI agent usage examples.
