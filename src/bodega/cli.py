"""Bodega CLI - Main entry point and command structure."""

import click
import os

prog_name = os.environ.get("CHIMP_REAL_ARGV0")
if prog_name:
    prog_name = os.path.basename(prog_name)
else:
    prog_name = "bodega"

# patch the program name
import click.core
click.core._detect_program_name = lambda *args, **kwargs: prog_name

from bodega import __version__
from bodega.config import load_config, BodegaConfig
from bodega.storage import TicketStorage
from bodega.errors import StorageError
from bodega.commands.utils import Context, pass_context


# ============================================================================
# Main CLI Group
# ============================================================================

@click.group()
@click.version_option(version=__version__, help="Show the Bodega version and exit")
@click.help_option("-h", "--help", help="Show this message and exit")
@click.option("--debug", is_flag=True, help="Enable debug output")
@pass_context
def main(ctx: Context, debug: bool):
    """Bodega - Git-native issue tracking for developers and AI agents"""
    ctx.debug = debug

    # Load config (may fail if not in repo, that's ok for some commands)
    try:
        ctx.config = load_config()
        if ctx.config.bodega_dir:
            ctx.storage = TicketStorage(ctx.config)
    except StorageError:
        # Not in a bodega repo - only init command will work
        ctx.config = BodegaConfig()
        ctx.storage = None


# ============================================================================
# Command Registration
# ============================================================================

# Import command modules
from bodega.commands import (
    init,
    order,
    lifecycle,
    view,
    list_cmd,
    deps,
    migrate,
    sync,
)

# Register individual commands
main.add_command(init.init)
main.add_command(order.order)

# Register lifecycle commands
main.add_command(lifecycle.prep)
main.add_command(lifecycle.bag)
main.add_command(lifecycle.remake)
main.add_command(lifecycle.status)

# Register view commands
main.add_command(view.peek)
main.add_command(view.adjust)
main.add_command(view.note)

# Register list commands
main.add_command(list_cmd.list_tickets)
main.add_command(list_cmd.ready)
main.add_command(list_cmd.blocked)
main.add_command(list_cmd.served)
main.add_command(list_cmd.query)

# Register dependency commands
main.add_command(deps.needs)
main.add_command(deps.free)
main.add_command(deps.combo)
main.add_command(deps.split)
main.add_command(deps.tree)
main.add_command(deps.cycle)

# Register migrate command
main.add_command(migrate.migrate_beads)

# Register sync commands
main.add_command(sync.sync)
main.add_command(sync.status)


if __name__ == "__main__":
    main()
