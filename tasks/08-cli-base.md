# Task 08: CLI Base Structure

## Summary
Set up the main Click CLI structure with command groups and shared options.

## Dependencies
- Task 01: Project Setup
- Task 04: Config (for loading configuration)
- Task 05: Storage (for TicketStorage)

## Requirements

### 1. Main CLI Entry Point (`src/bodega/cli.py`)

```python
import sys
import click
from pathlib import Path
from typing import Optional

from . import __version__
from .config import load_config, BodegaConfig
from .storage import TicketStorage, StorageError

# Shared context object
class Context:
    def __init__(self):
        self.config: Optional[BodegaConfig] = None
        self.storage: Optional[TicketStorage] = None
        self.debug: bool = False

pass_context = click.make_pass_decorator(Context, ensure=True)

@click.group()
@click.version_option(version=__version__)
@click.option("--debug", is_flag=True, help="Enable debug output")
@pass_context
def main(ctx: Context, debug: bool):
    """Bodega - Git-native issue tracking for developers and AI agents."""
    ctx.debug = debug

    # Load config (may fail if not in repo, that's ok for some commands)
    try:
        ctx.config = load_config()
        if ctx.config.bodega_dir:
            ctx.storage = TicketStorage(ctx.config)
    except StorageError:
        # Not in a bodega repo - only init command will work
        ctx.config = BodegaConfig()
```

### 2. Error Handling

```python
def handle_error(ctx: Context, error: Exception, exit_code: int = 1) -> None:
    """Handle errors with appropriate output."""
    if ctx.debug:
        import traceback
        click.echo(traceback.format_exc(), err=True)
    else:
        click.echo(f"Error: {error}", err=True)
    sys.exit(exit_code)

def require_repo(ctx: Context) -> TicketStorage:
    """Ensure we're in a bodega repository."""
    if not ctx.storage:
        click.echo("Error: Not in a bodega repository. Run 'bodega init' first.", err=True)
        sys.exit(1)
    return ctx.storage
```

### 3. Command Registration Pattern

```python
# At the bottom of cli.py, import and register command groups
from .commands import init, create, lifecycle, view, list_cmd, deps, migrate

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
```

### 4. Shared Options and Decorators

```python
# Common option for ticket ID argument
def ticket_id_argument(func):
    """Decorator for commands that take a ticket ID."""
    return click.argument("ticket_id", metavar="ID")(func)

# Common options for filtering
def filter_options(func):
    """Decorator for commands that support filtering."""
    func = click.option("--status", "-s", help="Filter by status")(func)
    func = click.option("--type", "-t", "ticket_type", help="Filter by type")(func)
    func = click.option("--tag", help="Filter by tag")(func)
    func = click.option("--assignee", help="Filter by assignee")(func)
    func = click.option("--priority", "-p", type=int, help="Filter by priority")(func)
    return func

# Format option
def format_option(func):
    """Decorator for commands that support output format."""
    return click.option(
        "--format", "-f", "fmt",
        type=click.Choice(["table", "compact", "ids"]),
        help="Output format"
    )(func)
```

### 5. Commands Init File (`src/bodega/commands/__init__.py`)

```python
"""Bodega CLI commands."""

from . import (
    init,
    create,
    lifecycle,
    view,
    list_cmd,  # 'list' is a reserved word
    deps,
    migrate,
)

__all__ = [
    "init",
    "create",
    "lifecycle",
    "view",
    "list_cmd",
    "deps",
    "migrate",
]
```

## Acceptance Criteria

- [ ] `bodega --version` shows version
- [ ] `bodega --help` shows all commands
- [ ] `bodega <command> --help` shows command help
- [ ] Context object properly passes config/storage to commands
- [ ] Error messages are clean (no tracebacks unless --debug)
- [ ] Commands fail gracefully when not in repo
- [ ] Exit codes: 0=success, 1=error, 2=usage error

## Test Cases

```python
from click.testing import CliRunner
from bodega.cli import main

def test_version():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output

def test_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "bodega" in result.output.lower()

def test_not_in_repo():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["list"])
        assert result.exit_code == 1
        assert "Not in a bodega repository" in result.output
```
