"""Migration commands - Import from other systems."""

import click
from bodega.commands.utils import pass_context, Context


@click.command(name="migrate-beads")
@click.argument("beads_dir", required=True)
@click.option("--dry-run", is_flag=True, help="Show what would be migrated without doing it")
@pass_context
def migrate_beads(ctx: Context, beads_dir: str, dry_run: bool):
    """Migrate from beads format"""
    click.echo("migrate-beads command - to be implemented")
