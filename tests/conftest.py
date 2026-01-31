"""Shared pytest fixtures for bodega tests."""

import pytest
import subprocess
from pathlib import Path
from click.testing import CliRunner

from bodega.config import BodegaConfig
from bodega.storage import TicketStorage, init_repository
from bodega.models import Ticket, TicketType, TicketStatus
from bodega.cli import main


# ============================================================================
# Basic Fixtures
# ============================================================================

@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_repo(runner):
    """Create a temporary repository for testing (without worktree)."""
    with runner.isolated_filesystem():
        init_repository()
        yield


@pytest.fixture
def temp_git_repo(tmp_path, monkeypatch):
    """
    Create a temporary git repository for testing worktree functionality.

    Initializes git, sets user config, and creates initial commit.
    Changes to the repository directory.
    Yields the path to the repository.
    """
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    # Change to the repo directory for the test
    monkeypatch.chdir(repo_path)

    # Initialize git
    subprocess.run(
        ["git", "init", "--initial-branch=main"],
        check=True,
        capture_output=True
    )

    # Set git user config
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        check=True,
        capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        check=True,
        capture_output=True
    )

    # Create initial commit
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "Initial commit"],
        check=True,
        capture_output=True
    )

    yield repo_path


# ============================================================================
# Storage Fixtures
# ============================================================================

@pytest.fixture
def tmp_bodega(tmp_path):
    """
    Create a temporary bodega repository (without worktree).

    Yields the path to the .bodega directory.
    """
    bodega_dir = init_repository(tmp_path)
    yield bodega_dir


@pytest.fixture
def config(tmp_bodega):
    """BodegaConfig pointing to temporary repository."""
    return BodegaConfig(bodega_dir=tmp_bodega)


@pytest.fixture
def storage(config):
    """TicketStorage for temporary repository."""
    return TicketStorage(config)


# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
def sample_ticket():
    """A sample ticket dict for testing."""
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


# ============================================================================
# Pre-populated Repository Fixtures
# ============================================================================

@pytest.fixture
def temp_repo_with_ticket(runner):
    """Create a temporary repository with a test ticket."""
    with runner.isolated_filesystem():
        init_repository()

        # Create a single ticket
        result = runner.invoke(main, ["order", "Test ticket", "--description", "Test description"])
        ticket_id = result.output.strip()

        yield ticket_id


@pytest.fixture
def temp_repo_with_tickets(runner):
    """
    Create a temporary repository with multiple test tickets.

    Creates:
    - Bug with high priority (urgent tag)
    - Feature with normal priority (api tag)
    - Task with low priority

    Yields list of ticket IDs.
    """
    with runner.isolated_filesystem():
        init_repository()

        tickets = []

        # Bug with high priority
        result = runner.invoke(main, [
            "order", "-t", "bug", "-p", "1", "--tag", "urgent",
            "Critical bug"
        ])
        tickets.append(result.output.strip())

        # Feature with normal priority
        result = runner.invoke(main, [
            "order", "-t", "feature", "-p", "2", "--tag", "api",
            "New feature"
        ])
        tickets.append(result.output.strip())

        # Task with low priority
        result = runner.invoke(main, [
            "order", "-t", "task", "-p", "3",
            "Regular task"
        ])
        tickets.append(result.output.strip())

        yield tickets


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


# ============================================================================
# Utility Fixtures
# ============================================================================

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
