# Task 04: Configuration System

## Summary
Implement the layered configuration system with global, project, and environment variable support.

## Dependencies
- Task 01: Project Setup
- Task 03: Utils (for `find_bodega_dir`)

## Requirements

### 1. Configuration Dataclass (`src/bodega/config.py`)

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import os
import yaml

@dataclass
class BodegaConfig:
    """Bodega configuration with layered loading."""

    # Defaults for new tickets
    default_type: str = "task"
    default_priority: int = 2
    default_assignee: str = ""  # empty = use git user.name

    # ID configuration
    id_prefix: str = "bg"

    # Editor
    editor: Optional[str] = None  # None = use $EDITOR

    # Output settings
    list_format: str = "table"  # table, compact, ids
    date_format: str = "%Y-%m-%d %H:%M"

    # Paths (computed, not from config file)
    bodega_dir: Optional[Path] = None

    @property
    def effective_editor(self) -> str:
        """Get editor command, with fallback chain."""
        return self.editor or os.environ.get("EDITOR", "vi")
```

### 2. Configuration Loading

```python
GLOBAL_CONFIG_PATH = Path.home() / ".bodega" / "config.yaml"

def load_config(project_dir: Optional[Path] = None) -> BodegaConfig:
    """
    Load configuration with precedence:
    1. Environment variables (highest)
    2. Project config (.bodega/config.yaml)
    3. Global config (~/.bodega/config.yaml)
    4. Built-in defaults (lowest)
    """
    config = BodegaConfig()

    # Load global config
    if GLOBAL_CONFIG_PATH.exists():
        _merge_yaml_config(config, GLOBAL_CONFIG_PATH)

    # Find and load project config
    from .utils import find_bodega_dir
    bodega_dir = project_dir or find_bodega_dir()
    if bodega_dir:
        config.bodega_dir = bodega_dir
        project_config = bodega_dir / "config.yaml"
        if project_config.exists():
            _merge_yaml_config(config, project_config)

    # Apply environment variables (highest precedence)
    _apply_env_vars(config)

    return config


def _merge_yaml_config(config: BodegaConfig, path: Path) -> None:
    """Merge YAML config file into config object."""
    with open(path) as f:
        data = yaml.safe_load(f) or {}

    # Handle nested 'defaults' section
    defaults = data.get("defaults", {})
    if "type" in defaults:
        config.default_type = defaults["type"]
    if "priority" in defaults:
        config.default_priority = defaults["priority"]
    if "assignee" in defaults:
        config.default_assignee = defaults["assignee"]

    # Top-level settings
    if "id_prefix" in data:
        config.id_prefix = data["id_prefix"]
    if "editor" in data:
        config.editor = data["editor"]
    if "list_format" in data:
        config.list_format = data["list_format"]
    if "date_format" in data:
        config.date_format = data["date_format"]


def _apply_env_vars(config: BodegaConfig) -> None:
    """Apply environment variable overrides."""
    if "BODEGA_DIR" in os.environ:
        config.bodega_dir = Path(os.environ["BODEGA_DIR"])
    # EDITOR is handled via effective_editor property
```

### 3. Config File Template

```python
DEFAULT_CONFIG_TEMPLATE = """\
# Bodega configuration
# See: https://github.com/yourname/bodega

# Default values for new tickets
defaults:
  type: task
  priority: 2
  # assignee: ""  # Empty = use git user.name

# ID prefix for generated ticket IDs
# id_prefix: bg

# Editor command (defaults to $EDITOR)
# editor: vim

# List output format: table, compact, ids
# list_format: table

# Date format for display
# date_format: "%Y-%m-%d %H:%M"
"""

def write_default_config(path: Path) -> None:
    """Write default config template to path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(DEFAULT_CONFIG_TEMPLATE)
```

### 4. Config Validation

```python
def validate_config(config: BodegaConfig) -> list[str]:
    """
    Validate configuration, return list of errors.
    Empty list = valid.
    """
    errors = []

    if config.default_priority not in range(5):
        errors.append(f"Invalid default_priority: {config.default_priority} (must be 0-4)")

    valid_types = {"bug", "feature", "task", "epic", "chore"}
    if config.default_type not in valid_types:
        errors.append(f"Invalid default_type: {config.default_type}")

    valid_formats = {"table", "compact", "ids"}
    if config.list_format not in valid_formats:
        errors.append(f"Invalid list_format: {config.list_format}")

    return errors
```

## Acceptance Criteria

- [ ] `load_config()` returns sensible defaults when no config files exist
- [ ] Global config at `~/.bodega/config.yaml` is loaded
- [ ] Project config at `.bodega/config.yaml` overrides global
- [ ] `BODEGA_DIR` environment variable overrides config
- [ ] `effective_editor` falls back to `$EDITOR` then `vi`
- [ ] `write_default_config()` creates valid YAML
- [ ] `validate_config()` catches invalid values

## Test Cases

```python
def test_default_config():
    config = BodegaConfig()
    assert config.default_type == "task"
    assert config.default_priority == 2
    assert config.id_prefix == "bg"

def test_load_global_config(tmp_path, monkeypatch):
    global_dir = tmp_path / ".bodega"
    global_dir.mkdir()
    (global_dir / "config.yaml").write_text("id_prefix: myproj\n")

    monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", global_dir / "config.yaml")
    config = load_config()
    assert config.id_prefix == "myproj"

def test_project_overrides_global(tmp_path, monkeypatch):
    # Setup global
    global_dir = tmp_path / "home" / ".bodega"
    global_dir.mkdir(parents=True)
    (global_dir / "config.yaml").write_text("id_prefix: global\n")

    # Setup project
    project_dir = tmp_path / "project" / ".bodega"
    project_dir.mkdir(parents=True)
    (project_dir / "config.yaml").write_text("id_prefix: project\n")

    monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", global_dir / "config.yaml")
    config = load_config(project_dir)
    assert config.id_prefix == "project"

def test_env_var_override(monkeypatch, tmp_path):
    monkeypatch.setenv("BODEGA_DIR", str(tmp_path / "custom"))
    config = load_config()
    assert config.bodega_dir == tmp_path / "custom"
```
