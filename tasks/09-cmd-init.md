# Task 09: Init Command

## Summary
Implement the `bodega init` command to initialize a new bodega repository.

## Dependencies
- Task 01: Project Setup
- Task 04: Config (for write_default_config)
- Task 05: Storage (for init_repository)
- Task 08: CLI Base

## Requirements

### 1. Init Command (`src/bodega/commands/init.py`)

```python
import click
from pathlib import Path

from ..storage import init_repository, StorageError
from ..cli import pass_context, Context

@click.command()
@click.option("--force", is_flag=True, help="Reinitialize existing repository")
@click.argument("path", required=False, type=click.Path())
@pass_context
def init(ctx: Context, force: bool, path: str | None):
    """
    Initialize a new bodega repository.

    Creates a .bodega/ directory with default configuration.

    Examples:

        bodega init           # Initialize in current directory

        bodega init ./myproj  # Initialize in specific directory

        bodega init --force   # Reinitialize existing repo
    """
    target = Path(path) if path else Path.cwd()

    try:
        bodega_dir = init_repository(target, force=force)
        click.echo(f"Initialized bodega repository in {bodega_dir}")
    except StorageError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
```

### 2. Created Directory Structure

After `bodega init`, the following should exist:

```
.bodega/
└── config.yaml    # Default configuration template
```

### 3. Output Messages

- Success: `Initialized bodega repository in /path/to/.bodega`
- Already exists: `Error: Bodega repository already exists at /path/to/.bodega`
- With --force: Reinitializes without error

## Acceptance Criteria

- [ ] `bodega init` creates `.bodega/` directory
- [ ] `bodega init` creates `config.yaml` with default template
- [ ] `bodega init` fails if `.bodega/` already exists (without --force)
- [ ] `bodega init --force` reinitializes existing repo
- [ ] `bodega init /path` initializes at specified path
- [ ] Outputs confirmation message on success
- [ ] Returns exit code 0 on success, 1 on error

## Test Cases

```python
from click.testing import CliRunner
from bodega.cli import main

def test_init_creates_directory():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert Path(".bodega").is_dir()
        assert Path(".bodega/config.yaml").is_file()

def test_init_fails_if_exists():
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path(".bodega").mkdir()
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 1
        assert "already exists" in result.output

def test_init_force():
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path(".bodega").mkdir()
        result = runner.invoke(main, ["init", "--force"])
        assert result.exit_code == 0

def test_init_with_path():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init", "subdir"])
        assert result.exit_code == 0
        assert Path("subdir/.bodega").is_dir()
```
