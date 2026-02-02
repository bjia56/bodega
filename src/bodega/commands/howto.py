"""Bodega howto command - Show useful CLI examples for AI agents."""

import click

from bodega.commands.utils import pass_context, Context


@click.command()
@click.help_option("-h", "--help", help="Show this message and exit")
@pass_context
def howto(ctx: Context):
    """Show useful CLI examples for AI agents.

    Displays concise examples of the most common Bodega operations
    for AI agents tracking tickets.
    """

    examples = """
Bodega CLI - Quick Reference

CREATING TICKETS
  bodega create -t bug -p 1 "Fix login error"
  bodega create -t feature --tag api "Add user profiles"
  bodega create -t task -a alice --description "Update docs" "Documentation"

FINDING WORK
  bodega ready                    # Unblocked tickets ready to work on
  bodega list -t bug -p 1         # High-priority bugs
  bodega list --sort priority     # All tickets by priority

QUERYING (JSON output for programmatic access)
  bodega query                    # All open tickets as JSON
  bodega query --id bg-abc123     # Single ticket details
  bodega query -t bug | jq        # Filter with jq

LIFECYCLE
  bodega start bg-abc123          # Start working on ticket
  bodega note bg-abc123 "Progress update text"
  bodega close bg-abc123          # Mark complete

DEPENDENCIES
  bodega dep bg-abc123 bg-def456  # bg-def456 blocks bg-abc123
  bodega tree bg-abc123           # Show dependency tree

TYPICAL WORKFLOW
  1. bodega ready                 # Find work
  2. bodega start bg-abc123       # Start ticket
  3. bodega note bg-abc123 "..."  # Add notes
  4. bodega close bg-abc123       # Complete

TIPS
  - Use partial IDs: 'abc' matches 'bg-abc123'
  - Use 'bodega query' for JSON output
  - Use 'bodega show' to view ticket details
  - Use 'bodega list -f ids' for batch operations
  - Combine filters: -t bug -p 1 --tag urgent
"""

    click.echo(examples.strip())
