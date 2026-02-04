import click
import sys
from typing import Optional
import traceback

from bodega.config import BodegaConfig
from bodega.storage import TicketStorage


# ============================================================================
# Context Object
# ============================================================================

class Context:
    """Shared context object for CLI commands."""

    def __init__(self):
        self.config: Optional[BodegaConfig] = None
        self.storage: Optional[TicketStorage] = None
        self.debug: bool = False


pass_context = click.make_pass_decorator(Context, ensure=True)


# ============================================================================
# Error Handling
# ============================================================================

def handle_error(ctx: Context, error: Exception, exit_code: int = 1) -> None:
    """
    Handle errors with appropriate output.

    Args:
        ctx: The CLI context
        error: The exception that occurred
        exit_code: The exit code to use (default: 1)
    """
    if ctx.debug:
        click.echo(traceback.format_exc(), err=True)
    else:
        click.echo(f"Error: {error}", err=True)
    sys.exit(exit_code)


def require_repo(ctx: Context) -> TicketStorage:
    """
    Ensure we're in a bodega repository.

    Args:
        ctx: The CLI context

    Returns:
        The TicketStorage instance

    Raises:
        SystemExit: If not in a repository
    """
    if not ctx.storage:
        click.echo("Error: Not in a bodega repository. Run 'bodega init' first.", err=True)
        sys.exit(1)
    return ctx.storage


# ============================================================================
# Shared Decorators and Options
# ============================================================================

def ticket_id_argument(func):
    """Decorator for commands that take a ticket ID."""
    return click.argument("ticket_id", metavar="ID")(func)


def filter_options(func):
    """Decorator for commands that support filtering."""
    func = click.option("--status", "-s", help="Filter by status")(func)
    func = click.option("--type", "-t", "ticket_type", help="Filter by type")(func)
    func = click.option("--tag", help="Filter by tag")(func)
    func = click.option("--assignee", help="Filter by assignee")(func)
    func = click.option("--priority", "-p", type=int, help="Filter by priority")(func)
    return func


def format_option(func):
    """Decorator for commands that support output format."""
    return click.option(
        "--format", "-f", "fmt",
        type=click.Choice(["table", "compact", "ids", "json"]),
        help="Output format"
    )(func)
