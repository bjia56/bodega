"""Bodega CLI - Main entry point and command structure."""

import click

from bodega import __version__
from bodega.config import load_config, BodegaConfig
from bodega.storage import TicketStorage
from bodega.errors import StorageError
from bodega.commands.utils import Context, pass_context


# ============================================================================
# Main CLI Group
# ============================================================================

@click.group()
@click.version_option(version=__version__)
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
    create,
    lifecycle,
    view,
    list_cmd,
    deps,
    migrate,
)

# Register individual commands
main.add_command(init.init)
main.add_command(create.create)

# Register lifecycle commands
main.add_command(lifecycle.start)
main.add_command(lifecycle.close)
main.add_command(lifecycle.reopen)
main.add_command(lifecycle.status)

# Register view commands
main.add_command(view.show)
main.add_command(view.edit)
main.add_command(view.note)

# Register list commands
main.add_command(list_cmd.list_tickets)
main.add_command(list_cmd.ready)
main.add_command(list_cmd.blocked)
main.add_command(list_cmd.closed)
main.add_command(list_cmd.query)

# Register dependency commands
main.add_command(deps.dep)
main.add_command(deps.undep)
main.add_command(deps.link)
main.add_command(deps.unlink)
main.add_command(deps.tree)
main.add_command(deps.cycle)

# Register migrate command
main.add_command(migrate.migrate_beads)


if __name__ == "__main__":
    main()
