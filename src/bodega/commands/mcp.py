"""MCP command - Model Context Protocol server for AI agents."""

import click

from bodega.commands.utils import pass_context, Context, require_repo
from bodega.mcp_server import run_stdio_server, run_http_server


@click.group()
@click.help_option("-h", "--help", help="Show this message and exit")
def mcp():
    """Start MCP server for AI agent integration.

    The Model Context Protocol (MCP) server exposes bodega operations
    as tools that AI agents like Claude can use programmatically.

    Examples:

        bodega mcp stdio    # Run via stdio (for MCP clients)

        bodega mcp http     # Run via HTTP (for development)
    """
    pass


@mcp.command()
@click.help_option("-h", "--help", help="Show this message and exit")
@pass_context
def stdio(ctx: Context):
    """Run MCP server via stdio transport.

    This is the standard mode for MCP clients. The server communicates
    via stdin/stdout using JSON-RPC messages.

    Examples:

        bodega mcp stdio
    """
    storage = require_repo(ctx)
    config = ctx.config

    try:
        run_stdio_server(storage, config)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        if ctx.debug:
            raise
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@mcp.command()
@click.help_option("-h", "--help", help="Show this message and exit")
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=8000, type=int, help="Port to bind to")
@pass_context
def http(ctx: Context, host: str, port: int):
    """Run MCP server via HTTP transport (for development).

    This mode is useful for testing and development. It exposes an HTTP
    endpoint that accepts MCP requests.

    Examples:

        bodega mcp http                    # Default: 127.0.0.1:8000

        bodega mcp http --port 9000        # Custom port

        bodega mcp http --host 0.0.0.0     # Listen on all interfaces
    """
    storage = require_repo(ctx)
    config = ctx.config

    try:
        click.echo(f"Starting MCP server on http://{host}:{port}")
        click.echo("Press Ctrl+C to stop")
        run_http_server(storage, config, host, port)
    except KeyboardInterrupt:
        click.echo("\nShutting down...")
    except Exception as e:
        if ctx.debug:
            raise
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
