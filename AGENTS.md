# Bodega - Agent Development Guide

This document provides essential information for AI coding agents working in this repository.

## Project Overview

Bodega is a Git-native issue tracking system for developers and AI agents, written in Python 3.11+.
Uses Click for CLI, YAML for config, frontmatter for ticket storage in markdown files.

## Build & Test Commands

### Installation
```bash
# Install package in development mode
pip install -e .

# Install with dev dependencies
pip install -e '.[dev]'
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_ticket.py

# Run single test function
pytest tests/test_ticket.py::test_ticket_minimal

# Run with verbose output
pytest -v

# Run with short traceback (default in pyproject.toml)
pytest --tb=short
```

### Running the CLI
```bash
# Run via module
python -m bodega --help

# Run via entry point (after install)
bodega --help
```

### Build
```bash
# Build wheel
python -m build

# The wheel file is generated in dist/
```

## Code Style & Conventions

### Import Order
1. Standard library imports (e.g., `import os`, `from pathlib import Path`)
2. Third-party imports (e.g., `import click`, `import frontmatter`)
3. Local imports (e.g., `from bodega.models import Ticket`)

Group imports with blank lines between groups. Use absolute imports for local modules.

Example:
```python
import os
from pathlib import Path

import click
import frontmatter

from bodega.models import Ticket
from bodega.utils import generate_id
```

### Type Hints
- Use modern Python type hints (Python 3.11+ syntax)
- Use `list[str]` instead of `List[str]`
- Use `dict[str, int]` instead of `Dict[str, int]`
- Use `str | None` instead of `Optional[str]`
- Use `from typing import Optional` only when needed for complex types

### Naming Conventions
- **Files**: Snake case (e.g., `ticket.py`, `list_cmd.py`)
- **Classes**: PascalCase (e.g., `Ticket`, `TicketStorage`, `BodegaConfig`)
- **Functions/Methods**: Snake case (e.g., `generate_id`, `from_dict`, `is_blocked`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `DEFAULT_PREFIX`, `TEMPLATE`)
- **Private**: Prefix with underscore (e.g., `_internal_helper`)

### Docstrings
Use triple-quoted strings for module, class, and function docstrings:

```python
def generate_id(prefix: str = DEFAULT_PREFIX) -> str:
    """
    Generate a new ticket ID.

    Format: {prefix}-{6 hex chars}
    Example: bg-a1b2c3

    Args:
        prefix: The prefix for the ID (default: "bg")

    Returns:
        A new ticket ID in the format {prefix}-{6 hex chars}
    """
```

### Dataclasses
- Use `@dataclass` decorator for data structures
- Use `field(default_factory=list)` for mutable defaults
- Implement `__post_init__` for validation

Example:
```python
from dataclasses import dataclass, field

@dataclass
class Ticket:
    id: str
    title: str
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.title.strip():
            raise ValueError("Title must not be empty")
```

### Error Handling
- Use custom exception classes from `bodega.errors`
- Raise specific exceptions (e.g., `TicketNotFoundError`, `StorageError`)
- All custom exceptions inherit from `BodegaError`
- Use descriptive error messages

Example:
```python
from bodega.errors import TicketNotFoundError

def get_ticket(ticket_id: str) -> Ticket:
    if ticket_id not in storage:
        raise TicketNotFoundError(f"No ticket found matching '{ticket_id}'")
    return storage[ticket_id]
```

### Click Commands
- Use `@click.command()` decorator
- Add help option: `@click.help_option("-h", "--help", help="Show this message and exit")`
- Use `@pass_context` decorator to pass custom context
- Import context from `bodega.commands.utils`

Example:
```python
from bodega.commands.utils import pass_context, Context

@click.command()
@click.help_option("-h", "--help", help="Show this message and exit")
@click.argument("ticket_id")
@pass_context
def show(ctx: Context, ticket_id: str):
    """Show ticket details."""
    ticket = ctx.storage.get(ticket_id)
    click.echo(ticket.title)
```

### Code Organization
- Group related functionality with comment headers:
  ```python
  # ============================================================================
  # Section Name
  # ============================================================================
  ```
- Separate command registration from implementation
- Keep commands in `src/bodega/commands/` directory
- Register commands in `src/bodega/cli.py`

### Testing Patterns
- Use pytest fixtures from `tests/conftest.py`
- Common fixtures: `runner`, `temp_repo`, `storage`, `sample_ticket`
- Use `CliRunner` from Click for testing CLI commands
- Test file naming: `test_*.py`
- Test function naming: `test_*`

Example:
```python
def test_ticket_minimal():
    """Test creating a ticket with minimal arguments."""
    t = Ticket(id="bg-abc123", title="Test ticket")
    assert t.id == "bg-abc123"
    assert t.title == "Test ticket"
```

### File Structure
```
src/bodega/
├── __init__.py         # Version info
├── cli.py              # Main CLI entry point
├── models/
│   └── ticket.py       # Data models
├── commands/
│   ├── create.py       # Command implementations
│   └── utils.py        # Command utilities
├── config.py           # Configuration
├── storage.py          # Ticket storage
├── errors.py           # Custom exceptions
├── utils.py            # Utility functions
└── output.py           # Output formatting

tests/
├── conftest.py         # Shared fixtures
├── test_*.py           # Test files
```

## Git Workflow

- Main branch: `main`
- Python version: 3.11+
- CI runs on: push to main, pull requests
- Tests must pass before merge

## Additional Notes

- Use `datetime.now(UTC)` for timestamps, not `datetime.utcnow()`
- Store dates as ISO 8601 strings in frontmatter
- Ticket IDs follow pattern: `^[a-z]+-[a-z0-9]+$` (e.g., `bg-abc123`)
- Priority range: 0 (critical) to 4 (backlog)
- Ticket statuses: `open`, `in-progress`, `closed`
- Ticket types: `bug`, `feature`, `task`, `epic`, `chore`

## Issue tracking

This project uses `bodega` for issue tracking. Run `bodega howto` to get started.