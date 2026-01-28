# Task 14: Dependency Commands

## Summary
Implement dependency management commands: `dep`, `undep`, `link`, `unlink`, `tree`, and `cycle`.

## Dependencies
- Task 01: Project Setup
- Task 02: Models (Ticket)
- Task 05: Storage (TicketStorage)
- Task 07: Graph (DependencyGraph)
- Task 08: CLI Base

## Requirements

### 1. Dependency Commands (`src/bodega/commands/deps.py`)

```python
import click

from ..cli import pass_context, Context, require_repo
from ..storage import TicketNotFoundError
from ..graph import DependencyGraph

@click.command()
@click.argument("ticket_id", metavar="ID")
@click.argument("blocker_id", metavar="BLOCKER")
@pass_context
def dep(ctx: Context, ticket_id: str, blocker_id: str):
    """
    Add a dependency (BLOCKER blocks ID).

    After this, ID cannot be completed until BLOCKER is closed.

    Examples:

        bodega dep bg-a1b2c3 bg-d4e5f6
        # bg-d4e5f6 now blocks bg-a1b2c3
    """
    storage = require_repo(ctx)

    try:
        # Resolve both IDs
        ticket = storage.get(ticket_id)
        blocker = storage.get(blocker_id)

        # Check for self-dependency
        if ticket.id == blocker.id:
            click.echo("Error: Ticket cannot depend on itself", err=True)
            raise SystemExit(1)

        # Check if already a dependency
        if blocker.id in ticket.deps:
            click.echo(f"{ticket.id} already depends on {blocker.id}")
            return

        # Check for cycle
        graph = DependencyGraph(storage)
        if graph.would_create_cycle(ticket.id, blocker.id):
            click.echo(f"Error: Adding this dependency would create a cycle", err=True)
            raise SystemExit(1)

        # Add dependency
        ticket.deps.append(blocker.id)
        storage.save(ticket)
        click.echo(f"{ticket.id} now depends on {blocker.id}")

    except TicketNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@click.command()
@click.argument("ticket_id", metavar="ID")
@click.argument("blocker_id", metavar="BLOCKER")
@pass_context
def undep(ctx: Context, ticket_id: str, blocker_id: str):
    """
    Remove a dependency.

    Examples:

        bodega undep bg-a1b2c3 bg-d4e5f6
    """
    storage = require_repo(ctx)

    try:
        ticket = storage.get(ticket_id)
        blocker = storage.get(blocker_id)

        if blocker.id not in ticket.deps:
            click.echo(f"{ticket.id} does not depend on {blocker.id}")
            return

        ticket.deps.remove(blocker.id)
        storage.save(ticket)
        click.echo(f"Removed dependency: {ticket.id} no longer depends on {blocker.id}")

    except TicketNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@click.command()
@click.argument("id1", metavar="ID1")
@click.argument("id2", metavar="ID2")
@pass_context
def link(ctx: Context, id1: str, id2: str):
    """
    Create a symmetric link between tickets.

    Links are bidirectional - both tickets will reference each other.

    Examples:

        bodega link bg-a1b2c3 bg-d4e5f6
    """
    storage = require_repo(ctx)

    try:
        ticket1 = storage.get(id1)
        ticket2 = storage.get(id2)

        if ticket1.id == ticket2.id:
            click.echo("Error: Cannot link ticket to itself", err=True)
            raise SystemExit(1)

        # Check if already linked
        if ticket2.id in ticket1.links and ticket1.id in ticket2.links:
            click.echo(f"{ticket1.id} and {ticket2.id} are already linked")
            return

        # Add links (symmetric)
        if ticket2.id not in ticket1.links:
            ticket1.links.append(ticket2.id)
        if ticket1.id not in ticket2.links:
            ticket2.links.append(ticket1.id)

        storage.save(ticket1)
        storage.save(ticket2)
        click.echo(f"Linked {ticket1.id} ↔ {ticket2.id}")

    except TicketNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@click.command()
@click.argument("id1", metavar="ID1")
@click.argument("id2", metavar="ID2")
@pass_context
def unlink(ctx: Context, id1: str, id2: str):
    """
    Remove a link between tickets.

    Examples:

        bodega unlink bg-a1b2c3 bg-d4e5f6
    """
    storage = require_repo(ctx)

    try:
        ticket1 = storage.get(id1)
        ticket2 = storage.get(id2)

        # Remove from both (symmetric)
        changed = False
        if ticket2.id in ticket1.links:
            ticket1.links.remove(ticket2.id)
            changed = True
        if ticket1.id in ticket2.links:
            ticket2.links.remove(ticket1.id)
            changed = True

        if not changed:
            click.echo(f"{ticket1.id} and {ticket2.id} are not linked")
            return

        storage.save(ticket1)
        storage.save(ticket2)
        click.echo(f"Unlinked {ticket1.id} ↔ {ticket2.id}")

    except TicketNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@click.command()
@click.argument("ticket_id", metavar="ID", required=False)
@pass_context
def tree(ctx: Context, ticket_id: str | None):
    """
    Display dependency tree.

    If ID is provided, shows tree for that ticket.
    Otherwise shows all dependency trees.

    Examples:

        bodega tree              # Show all trees

        bodega tree bg-a1b2c3    # Show tree for specific ticket
    """
    storage = require_repo(ctx)
    graph = DependencyGraph(storage)

    if ticket_id:
        try:
            ticket = storage.get(ticket_id)
            output = graph.format_tree(ticket.id)
        except TicketNotFoundError as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1)
        except ValueError as e:
            click.echo(f"Error: {e}", err=True)
            raise SystemExit(1)
    else:
        output = graph.format_tree()

    if output:
        click.echo(output)
    else:
        click.echo("No tickets found.")


@click.command()
@pass_context
def cycle(ctx: Context):
    """
    Detect circular dependencies.

    Reports any cycles found in the dependency graph.

    Examples:

        bodega cycle
    """
    storage = require_repo(ctx)
    graph = DependencyGraph(storage)

    cycles = graph.find_cycles()

    if not cycles:
        click.echo("No dependency cycles found.")
        return

    click.echo(f"Found {len(cycles)} cycle(s):")
    for cycle_path in cycles:
        path_str = " → ".join(cycle_path)
        click.echo(f"  {path_str}")
```

## Acceptance Criteria

- [ ] `bodega dep <id> <blocker>` adds dependency
- [ ] `bodega dep` prevents self-dependency
- [ ] `bodega dep` prevents cycles
- [ ] `bodega undep` removes dependency
- [ ] `bodega link` creates bidirectional link
- [ ] `bodega unlink` removes link from both tickets
- [ ] `bodega tree` shows all dependency trees
- [ ] `bodega tree <id>` shows tree for specific ticket
- [ ] `bodega cycle` detects and reports cycles
- [ ] All commands support partial ID matching

## Test Cases

```python
from click.testing import CliRunner
from bodega.cli import main

def test_dep(tmp_bodega):
    runner = CliRunner()

    # Create two tickets
    result = runner.invoke(main, ["create", "Task A"])
    id_a = result.output.strip()
    result = runner.invoke(main, ["create", "Task B"])
    id_b = result.output.strip()

    # Add dependency
    result = runner.invoke(main, ["dep", id_a, id_b])
    assert result.exit_code == 0
    assert "depends on" in result.output

    # Verify in blocked list
    result = runner.invoke(main, ["blocked"])
    assert id_a in result.output

def test_dep_prevents_cycle(tmp_bodega):
    runner = CliRunner()

    # A depends on B
    result = runner.invoke(main, ["create", "A"])
    id_a = result.output.strip()
    result = runner.invoke(main, ["create", "B"])
    id_b = result.output.strip()

    runner.invoke(main, ["dep", id_a, id_b])

    # B depends on A should fail (cycle)
    result = runner.invoke(main, ["dep", id_b, id_a])
    assert result.exit_code == 1
    assert "cycle" in result.output.lower()

def test_link(tmp_bodega):
    runner = CliRunner()

    result = runner.invoke(main, ["create", "Task A"])
    id_a = result.output.strip()
    result = runner.invoke(main, ["create", "Task B"])
    id_b = result.output.strip()

    result = runner.invoke(main, ["link", id_a, id_b])
    assert result.exit_code == 0
    assert "Linked" in result.output

    # Verify both have links
    result = runner.invoke(main, ["show", "--json", id_a])
    import json
    data = json.loads(result.output)
    assert id_b in data["links"]

def test_tree(tmp_bodega):
    runner = CliRunner()

    # Create hierarchy: Root <- Child <- Grandchild
    result = runner.invoke(main, ["create", "Root"])
    root_id = result.output.strip()
    result = runner.invoke(main, ["create", "Child"])
    child_id = result.output.strip()

    runner.invoke(main, ["dep", child_id, root_id])

    result = runner.invoke(main, ["tree", root_id])
    assert result.exit_code == 0
    assert root_id in result.output
    assert child_id in result.output

def test_cycle_detection(tmp_bodega):
    runner = CliRunner()
    result = runner.invoke(main, ["cycle"])
    assert result.exit_code == 0
    assert "No dependency cycles" in result.output
```
