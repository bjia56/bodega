# Task 16: Test Fixtures

## Summary
Implement shared pytest fixtures for testing bodega components.

## Dependencies
- Task 01: Project Setup
- Task 02: Models
- Task 04: Config
- Task 05: Storage

## Requirements

This task should be implemented early (after task 05) to enable testing of subsequent tasks.

### 1. Conftest File (`tests/conftest.py`)

```python
import pytest
from pathlib import Path
from click.testing import CliRunner

from bodega.config import BodegaConfig
from bodega.storage import TicketStorage, init_repository
from bodega.models import Ticket, TicketType, TicketStatus


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def tmp_bodega(tmp_path):
    """
    Create a temporary bodega repository.

    Yields the path to the .bodega directory.
    """
    bodega_dir = init_repository(tmp_path)
    yield bodega_dir


@pytest.fixture
def config(tmp_bodega):
    """
    BodegaConfig pointing to temporary repository.
    """
    return BodegaConfig(bodega_dir=tmp_bodega)


@pytest.fixture
def storage(config):
    """
    TicketStorage for temporary repository.
    """
    return TicketStorage(config)


@pytest.fixture
def sample_ticket():
    """
    A sample ticket dict for testing.
    """
    return {
        "id": "bg-test01",
        "title": "Test ticket",
        "type": "task",
        "status": "open",
        "priority": 2,
        "assignee": "tester",
        "tags": ["test", "sample"],
        "deps": [],
        "links": [],
        "parent": None,
        "external_ref": None,
        "description": "This is a test ticket.",
        "design": None,
        "acceptance_criteria": "- [ ] Test passes",
        "notes": [],
    }


@pytest.fixture
def tmp_bodega_with_ticket(tmp_bodega, storage):
    """
    Temporary bodega repository with one ticket created.

    Yields the ticket ID.
    """
    ticket = Ticket(
        id="",
        title="Test ticket",
        type=TicketType.TASK,
        status=TicketStatus.OPEN,
        priority=2,
        description="Test description",
    )
    created = storage.create(ticket)
    yield created.id


@pytest.fixture
def tmp_bodega_with_tickets(tmp_bodega, storage):
    """
    Temporary bodega repository with multiple tickets.

    Creates:
    - 2 open tasks
    - 1 in-progress bug
    - 1 closed feature

    Yields dict mapping labels to ticket IDs.
    """
    tickets = {
        "task1": Ticket(
            id="",
            title="Task 1",
            type=TicketType.TASK,
            status=TicketStatus.OPEN,
            priority=2,
            tags=["backend"],
        ),
        "task2": Ticket(
            id="",
            title="Task 2",
            type=TicketType.TASK,
            status=TicketStatus.OPEN,
            priority=3,
            tags=["frontend"],
        ),
        "bug": Ticket(
            id="",
            title="Bug fix",
            type=TicketType.BUG,
            status=TicketStatus.IN_PROGRESS,
            priority=1,
            tags=["urgent"],
        ),
        "feature": Ticket(
            id="",
            title="Completed feature",
            type=TicketType.FEATURE,
            status=TicketStatus.CLOSED,
            priority=2,
        ),
    }

    result = {}
    for label, ticket in tickets.items():
        created = storage.create(ticket)
        result[label] = created.id

    yield result


@pytest.fixture
def tmp_bodega_with_deps(tmp_bodega, storage):
    """
    Temporary bodega with dependency chain.

    Creates: root <- child <- grandchild

    Yields dict with ticket IDs.
    """
    root = storage.create(Ticket(
        id="",
        title="Root task",
        type=TicketType.TASK,
        status=TicketStatus.OPEN,
    ))

    child = storage.create(Ticket(
        id="",
        title="Child task",
        type=TicketType.TASK,
        status=TicketStatus.OPEN,
        deps=[root.id],
    ))

    grandchild = storage.create(Ticket(
        id="",
        title="Grandchild task",
        type=TicketType.TASK,
        status=TicketStatus.OPEN,
        deps=[child.id],
    ))

    yield {
        "root": root.id,
        "child": child.id,
        "grandchild": grandchild.id,
    }


@pytest.fixture
def isolated_cli(runner, tmp_path):
    """
    CLI runner with isolated filesystem.

    Provides a context manager that changes to the temp directory.
    """
    class IsolatedCLI:
        def __init__(self):
            self.runner = runner
            self.path = tmp_path

        def invoke(self, *args, **kwargs):
            with self.runner.isolated_filesystem(temp_dir=self.path):
                return self.runner.invoke(*args, **kwargs)

    return IsolatedCLI()
```

### 2. Test Utilities (`tests/utils.py`)

```python
"""Test utility functions."""

import json
from pathlib import Path


def create_beads_fixture(path: Path, issues: list[dict]) -> Path:
    """
    Create a .beads directory with issues.jsonl for testing migration.

    Args:
        path: Base directory
        issues: List of issue dicts

    Returns:
        Path to .beads directory
    """
    beads_dir = path / ".beads"
    beads_dir.mkdir(parents=True, exist_ok=True)

    with open(beads_dir / "issues.jsonl", "w") as f:
        for issue in issues:
            f.write(json.dumps(issue) + "\n")

    return beads_dir


def parse_cli_output(output: str) -> dict:
    """
    Parse CLI output that might be JSON or table format.

    Returns parsed data or raw output.
    """
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {"raw": output}


def assert_ticket_exists(storage, ticket_id: str) -> None:
    """Assert that a ticket exists in storage."""
    ticket = storage.get(ticket_id)
    assert ticket is not None
    assert ticket.id == ticket_id


def assert_ticket_status(storage, ticket_id: str, expected_status: str) -> None:
    """Assert ticket has expected status."""
    ticket = storage.get(ticket_id)
    assert ticket.status.value == expected_status
```

### 3. Pytest Configuration (`pytest.ini` or `pyproject.toml`)

Add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
```

## Acceptance Criteria

- [ ] `tmp_bodega` fixture creates valid .bodega directory
- [ ] `storage` fixture provides working TicketStorage
- [ ] `tmp_bodega_with_ticket` creates a single ticket
- [ ] `tmp_bodega_with_tickets` creates multiple tickets with varied attributes
- [ ] `tmp_bodega_with_deps` creates tickets with dependency chain
- [ ] `isolated_cli` provides CLI testing in isolated filesystem
- [ ] Test utilities work correctly
- [ ] `pytest` runs successfully with fixtures

## Usage Examples

```python
def test_create_ticket(storage):
    """Test using storage fixture."""
    ticket = Ticket(id="", title="New ticket")
    created = storage.create(ticket)
    assert created.id.startswith("bg-")

def test_list_filters(tmp_bodega_with_tickets):
    """Test using pre-populated fixture."""
    ids = tmp_bodega_with_tickets
    # ids["task1"], ids["bug"], etc. are available

def test_cli_list(runner, tmp_bodega_with_tickets):
    """Test CLI command."""
    from bodega.cli import main
    result = runner.invoke(main, ["list"])
    assert result.exit_code == 0

def test_dependency_chain(tmp_bodega_with_deps, storage):
    """Test using dependency fixture."""
    ids = tmp_bodega_with_deps
    grandchild = storage.get(ids["grandchild"])
    assert ids["child"] in grandchild.deps
```

## Notes

- Fixtures should be implemented as part of the initial project setup
- Add new fixtures as needed when implementing commands
- Keep fixtures focused and composable
- Use `yield` for fixtures that need cleanup
