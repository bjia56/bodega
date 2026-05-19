"""Configuration module for bodega settings."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import os
import yaml

from bodega.utils import find_bodega_dir


# ============================================================================
# Global Constants
# ============================================================================

GLOBAL_CONFIG_PATH = Path.home() / ".bodega" / "config.yaml"

DEFAULT_CONFIG_TEMPLATE = """\
# Bodega configuration
# See: https://github.com/bjia56/bodega

# Default values for new tickets
defaults:
  type: task
  priority: 2
  # assignee: ""  # Empty = use git user.name

# ID prefix for generated ticket IDs:
# - scalar mode: id_prefix: bg
# - object mode:
#   id_prefix:
#     default: bg
#     overrides:
#       - services: svc
#       - services/api: api

# Editor command (defaults to $EDITOR)
# editor: vim

# List output format: table, compact, ids
# list_format: table

# Date format for display
# date_format: "%Y-%m-%d %H:%M"

# Git integration (optional)
# git:
  # Branch name for worktree-based ticket storage
  # Leave empty or comment out to store tickets in current branch
  # branch: bodega

  # Auto-commit ticket changes to bodega branch (worktree mode only)
  # auto_commit: true

  # Conflict resolution strategy: theirs, ours, manual
  # sync_strategy: theirs
"""


# ============================================================================
# Configuration Dataclass
# ============================================================================

@dataclass
class BodegaConfig:
    """Bodega configuration with layered loading."""

    # Defaults for new tickets
    default_type: str = "task"
    default_priority: int = 2
    default_assignee: str = ""  # empty = use git user.name

    # ID configuration
    id_prefix: str = "bg"

    # Subdirectory-based prefix overrides: maps relative path -> prefix.
    # The longest matching path key wins when creating new tickets.
    id_prefix_overrides: dict[str, str] = field(default_factory=dict)

    # Editor
    editor: Optional[str] = None  # None = use $EDITOR

    # Output settings
    list_format: str = "table"  # table, compact, ids
    date_format: str = "%Y-%m-%d %H:%M"

    # Git worktree settings
    git_branch: str = ""  # Empty = store in current branch, non-empty = use worktree
    git_auto_commit: bool = False
    git_sync_strategy: str = "theirs"  # theirs, ours, manual

    # Paths (computed, not from config file)
    bodega_dir: Optional[Path] = None

    # Offline mode settings
    offline_mode: bool = False  # True if using offline store
    offline_store_path: Optional[Path] = None  # Path to offline store if active

    # Internal tracking (not from config file)
    _id_prefix_was_set: bool = False

    @property
    def effective_editor(self) -> str:
        """Get editor command, with fallback chain."""
        return self.editor or os.environ.get("EDITOR", "vi")


# ============================================================================
# Configuration Loading
# ============================================================================

def _derive_id_prefix(bodega_dir: Optional[Path]) -> str:
    """
    Derive an id_prefix from the project folder name.

    Args:
        bodega_dir: Path to .bodega directory, or None

    Returns:
        Derived prefix (lowercase, alphanumeric only), or "bg" if cannot derive
    """
    if not bodega_dir:
        return "bg"

    # Get the parent directory name (the project folder)
    project_name = bodega_dir.parent.name

    # Convert to lowercase and keep only alphanumeric characters
    prefix = "".join(c for c in project_name.lower() if c.isalnum())

    # If empty or starts with number, fall back to "bg"
    if not prefix or prefix[0].isdigit():
        return "bg"

    return prefix


def load_config(project_dir: Optional[Path] = None) -> BodegaConfig:
    """
    Load configuration with precedence:
    1. Environment variables (highest)
    2. Project config (.bodega/config.yaml)
    3. Global config (~/.bodega/config.yaml)
    4. Built-in defaults (lowest)

    If id_prefix is not explicitly set in any config file, it will be
    derived from the project folder name.

    Args:
        project_dir: Optional path to .bodega directory. If None, will search for it.

    Returns:
        BodegaConfig instance with merged configuration
    """
    config = BodegaConfig()

    # Load global config
    if GLOBAL_CONFIG_PATH.exists():
        _merge_yaml_config(config, GLOBAL_CONFIG_PATH)

    # Find and load project config
    bodega_dir = project_dir or find_bodega_dir()
    if bodega_dir:
        config.bodega_dir = bodega_dir
        project_config = bodega_dir / "config.yaml"
        if project_config.exists():
            _merge_yaml_config(config, project_config)

        # Check if bodega_dir is under ~/.bodega/ (offline mode)
        home_bodega = Path.home() / ".bodega"
        try:
            # Check if bodega_dir is relative to ~/.bodega/
            bodega_dir.relative_to(home_bodega)
            config.offline_mode = True
            config.offline_store_path = bodega_dir
        except ValueError:
            # bodega_dir is not under ~/.bodega/, so not offline mode
            pass

    # Apply environment variables (highest precedence)
    _apply_env_vars(config)

    # If id_prefix was not explicitly set, derive it from folder name
    if not config._id_prefix_was_set:
        config.id_prefix = _derive_id_prefix(bodega_dir)

    # Apply subdirectory prefix override (overrides explicit and derived prefix)
    _apply_subdir_prefix_override(config, bodega_dir)

    return config


def _merge_yaml_config(config: BodegaConfig, path: Path) -> None:
    """
    Merge YAML config file into config object.

    Args:
        config: BodegaConfig instance to merge into
        path: Path to YAML config file
    """
    with open(path) as f:
        data = yaml.safe_load(f) or {}

    # Handle nested 'defaults' section
    defaults = data.get("defaults", {}) or {}
    if "type" in defaults:
        config.default_type = defaults["type"]
    if "priority" in defaults:
        config.default_priority = defaults["priority"]
    if "assignee" in defaults:
        config.default_assignee = defaults["assignee"]

    # Top-level settings
    if "id_prefix" in data:
        raw_id_prefix = data["id_prefix"]
        if isinstance(raw_id_prefix, str):
            config.id_prefix = raw_id_prefix
            config.id_prefix_overrides = {}
            config._id_prefix_was_set = True
        elif isinstance(raw_id_prefix, dict):
            if "default" not in raw_id_prefix:
                raise ValueError(f"id_prefix.default is required in {path}")
            default_prefix = raw_id_prefix["default"]
            if not isinstance(default_prefix, str):
                raise ValueError(f"id_prefix.default must be a string in {path}")

            overrides = raw_id_prefix.get("overrides", [])
            if not isinstance(overrides, list):
                raise ValueError(f"id_prefix.overrides must be a list in {path}")

            parsed_overrides: dict[str, str] = {}
            for entry in overrides:
                if not isinstance(entry, dict):
                    raise ValueError(
                        f"id_prefix.overrides entries must be mappings in {path}"
                    )
                if len(entry) != 1:
                    raise ValueError(
                        f"id_prefix.overrides entries must have exactly one mapping in {path}"
                    )
                for override_path, prefix in entry.items():
                    normalized_key = str(override_path).strip("/")
                    parsed_overrides[normalized_key] = str(prefix)

            config.id_prefix = default_prefix
            config.id_prefix_overrides = parsed_overrides
            config._id_prefix_was_set = True
        else:
            raise ValueError(f"id_prefix must be a string or mapping in {path}")
    if "editor" in data:
        config.editor = data["editor"]
    if "list_format" in data:
        config.list_format = data["list_format"]
    if "date_format" in data:
        config.date_format = data["date_format"]

    # Git worktree settings
    git_config = data.get("git", {})
    if "branch" in git_config:
        config.git_branch = git_config["branch"]
    if "auto_commit" in git_config:
        config.git_auto_commit = git_config["auto_commit"]
    if "sync_strategy" in git_config:
        config.git_sync_strategy = git_config["sync_strategy"]


def _apply_env_vars(config: BodegaConfig) -> None:
    """
    Apply environment variable overrides.

    Args:
        config: BodegaConfig instance to apply overrides to
    """
    if "BODEGA_DIR" in os.environ:
        config.bodega_dir = Path(os.environ["BODEGA_DIR"])
    # EDITOR is handled via effective_editor property


def _apply_subdir_prefix_override(config: BodegaConfig, bodega_dir: Optional[Path]) -> None:
    """
    Apply a subdirectory-based prefix override from id_prefix.overrides.

    Computes the current working directory relative to the repository root
    (``bodega_dir.parent``) and selects the longest-matching key from
    ``config.id_prefix_overrides``.  When a match is found it overrides
    ``config.id_prefix`` regardless of whether it was set explicitly or
    derived from the folder name.  This only affects new-ticket ID
    generation; reading or editing existing tickets is prefix-agnostic.

    No override is applied when:
    - ``config.id_prefix_overrides`` is empty
    - ``bodega_dir`` is None (no repo found)
    - The current working directory is outside the repository root (e.g.
      offline mode stores under ``~/.bodega/``)

    Args:
        config: BodegaConfig instance to potentially modify
        bodega_dir: Path to the ``.bodega`` directory, or None
    """
    if not config.id_prefix_overrides or not bodega_dir:
        return

    repo_root = bodega_dir.parent.resolve()
    try:
        rel = Path.cwd().resolve().relative_to(repo_root)
        rel_str = rel.as_posix()
        if rel_str == ".":
            rel_str = ""
    except ValueError:
        # cwd is outside the repo root – offline mode or similar
        return

    # Find the longest matching path key
    best_prefix: Optional[str] = None
    best_len = -1

    for key, prefix in config.id_prefix_overrides.items():
        # A key matches when cwd is exactly at that path or inside it
        if rel_str == key or rel_str.startswith(key + "/"):
            if len(key) > best_len:
                best_prefix = prefix
                best_len = len(key)

    if best_prefix is not None:
        config.id_prefix = best_prefix


# ============================================================================
# Config File Management
# ============================================================================

def write_default_config(path: Path) -> None:
    """
    Write default config template to path.

    Args:
        path: Path where config file should be written
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(DEFAULT_CONFIG_TEMPLATE)


# ============================================================================
# Config Validation
# ============================================================================

def validate_config(config: BodegaConfig) -> list[str]:
    """
    Validate configuration, return list of errors.
    Empty list = valid.

    Args:
        config: BodegaConfig instance to validate

    Returns:
        List of error messages. Empty list if configuration is valid.
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


# ============================================================================
# Offline Store Mapping
# ============================================================================

def get_offline_store_mapping() -> dict[str, str]:
    """
    Load offline stores mapping from global config.

    Returns mapping of project identifiers to friendly names.

    Returns:
        Dictionary mapping identifier to name (e.g., {'git-a1b2c3': 'my-project'})
        Returns empty dict if no mapping exists.
    """
    if not GLOBAL_CONFIG_PATH.exists():
        return {}

    with open(GLOBAL_CONFIG_PATH) as f:
        data = yaml.safe_load(f) or {}

    return data.get("offline_stores", {}) or {}


def set_offline_store_mapping(identifier: str, name: str) -> None:
    """
    Add or update an offline store mapping in global config.

    Creates ~/.bodega/config.yaml if it doesn't exist.
    Preserves existing configuration settings.

    Args:
        identifier: Project identifier (e.g., 'git-a1b2c3d4e5f6')
        name: Friendly name for the offline store (e.g., 'my-project')
    """
    # Load existing config or create empty dict
    if GLOBAL_CONFIG_PATH.exists():
        with open(GLOBAL_CONFIG_PATH) as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}

    # Ensure offline_stores section exists
    if "offline_stores" not in data:
        data["offline_stores"] = {}

    # Add/update mapping
    data["offline_stores"][identifier] = name

    # Write back to file
    GLOBAL_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(GLOBAL_CONFIG_PATH, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)


def list_offline_stores() -> list[tuple[str, str, Path]]:
    """
    List all offline stores with their metadata.

    Returns list of (identifier, name, path) tuples for all offline stores.
    Includes existence check for each store.

    Returns:
        List of tuples (identifier, name, path) for each offline store.
        Path points to ~/.bodega/<identifier>/ regardless of existence.
    """
    mapping = get_offline_store_mapping()
    home_bodega = Path.home() / ".bodega"

    stores = []
    for identifier, name in mapping.items():
        store_path = home_bodega / identifier
        stores.append((identifier, name, store_path))

    return stores
