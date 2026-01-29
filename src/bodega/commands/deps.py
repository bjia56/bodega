import click

from bodega.commands.utils import pass_context, Context, require_repo
from bodega.storage import TicketNotFoundError
from bodega.graph import DependencyGraph

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
