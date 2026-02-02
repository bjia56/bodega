import pytest
from pathlib import Path
from bodega.config import (
    BodegaConfig,
    load_config,
    write_default_config,
    validate_config,
    GLOBAL_CONFIG_PATH,
    DEFAULT_CONFIG_TEMPLATE,
)


# ============================================================================
# Default Configuration Tests
# ============================================================================


def test_default_config():
    """Test that default configuration has sensible values."""
    config = BodegaConfig()

    assert config.default_type == "task"
    assert config.default_priority == 2
    assert config.default_assignee == ""
    assert config.id_prefix == "bg"
    assert config.editor is None
    assert config.list_format == "table"
    assert config.date_format == "%Y-%m-%d %H:%M"
    assert config.bodega_dir is None


def test_effective_editor_fallback():
    """Test effective_editor property falls back correctly."""
    config = BodegaConfig()

    # With explicit editor
    config.editor = "nano"
    assert config.effective_editor == "nano"

    # Without explicit editor, falls back to $EDITOR or "vi"
    config.editor = None
    assert config.effective_editor in ["vi"] or len(config.effective_editor) > 0


def test_effective_editor_with_env(monkeypatch):
    """Test effective_editor respects EDITOR environment variable."""
    config = BodegaConfig()

    # Set EDITOR environment variable
    monkeypatch.setenv("EDITOR", "emacs")

    assert config.effective_editor == "emacs"

    # Explicit editor overrides EDITOR
    config.editor = "vim"
    assert config.effective_editor == "vim"


# ============================================================================
# Configuration Loading Tests
# ============================================================================


def test_load_config_no_files(tmp_path, monkeypatch, runner):
    """Test loading config when no config files exist."""
    with runner.isolated_filesystem():
        # Point to non-existent paths
        monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", tmp_path / "nonexistent" / "config.yaml")

        config = load_config()

        # Should return defaults
        assert config.default_type == "task"
        assert config.default_priority == 2
        assert config.id_prefix == "bg"


def test_load_global_config(tmp_path, monkeypatch, runner):
    """Test loading global configuration."""
    with runner.isolated_filesystem():
        # Create global config
        global_dir = tmp_path / ".bodega"
        global_dir.mkdir()
        global_config = global_dir / "config.yaml"
        global_config.write_text("id_prefix: myproj\n")

        monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", global_config)

        config = load_config()
        assert config.id_prefix == "myproj"


def test_load_global_config_with_defaults(tmp_path, monkeypatch, runner):
    """Test loading global config with defaults section."""
    with runner.isolated_filesystem():
        # Create global config with defaults
        global_dir = tmp_path / ".bodega"
        global_dir.mkdir()
        global_config = global_dir / "config.yaml"
        global_config.write_text("""
defaults:
  type: bug
  priority: 4
  assignee: alice
id_prefix: proj
editor: vim
list_format: compact
date_format: "%Y-%m-%d"
""")

        monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", global_config)

        config = load_config()
        assert config.default_type == "bug"
        assert config.default_priority == 4
        assert config.default_assignee == "alice"
        assert config.id_prefix == "proj"
        assert config.editor == "vim"
        assert config.list_format == "compact"
        assert config.date_format == "%Y-%m-%d"


def test_project_overrides_global(tmp_path, monkeypatch, runner):
    """Test that project config overrides global config."""
    with runner.isolated_filesystem():
        # Setup global config
        global_dir = tmp_path / "home" / ".bodega"
        global_dir.mkdir(parents=True)
        global_config = global_dir / "config.yaml"
        global_config.write_text("id_prefix: global\nlist_format: compact\n")

        # Setup project config
        project_dir = tmp_path / "project" / ".bodega"
        project_dir.mkdir(parents=True)
        project_config = project_dir / "config.yaml"
        project_config.write_text("id_prefix: project\n")

        monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", global_config)

        config = load_config(project_dir)

        # Project value overrides global
        assert config.id_prefix == "project"
        # Global value used when not in project config
        assert config.list_format == "compact"


def test_env_var_override(tmp_path, monkeypatch):
    """Test that environment variables override config files."""
    # Setup project config
    project_dir = tmp_path / ".bodega"
    project_dir.mkdir()

    # Set environment variable
    monkeypatch.setenv("BODEGA_DIR", str(tmp_path / "custom"))

    config = load_config()

    assert config.bodega_dir == tmp_path / "custom"


def test_load_config_finds_bodega_dir(tmp_path, monkeypatch):
    """Test that load_config finds .bodega directory."""
    # Create .bodega directory
    bodega_dir = tmp_path / ".bodega"
    bodega_dir.mkdir()
    (bodega_dir / "config.yaml").write_text("id_prefix: found\n")

    # Change to subdirectory
    subdir = tmp_path / "src" / "module"
    subdir.mkdir(parents=True)

    # Mock the current directory search
    import bodega.utils
    original_find = bodega.utils.find_bodega_dir

    def mock_find(start=None):
        return bodega_dir

    monkeypatch.setattr("bodega.utils.find_bodega_dir", mock_find)
    monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", tmp_path / "nonexistent")

    config = load_config()

    assert config.bodega_dir == bodega_dir
    assert config.id_prefix == "found"


def test_load_config_empty_yaml(tmp_path, monkeypatch):
    """Test loading config with empty YAML file."""
    global_dir = tmp_path / ".bodega"
    global_dir.mkdir()
    global_config = global_dir / "config.yaml"
    global_config.write_text("")  # Empty file

    monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", global_config)

    config = load_config()

    # Should use defaults
    assert config.default_type == "task"
    assert config.id_prefix == "bg"


# ============================================================================
# Config File Management Tests
# ============================================================================


def test_write_default_config(tmp_path):
    """Test writing default config template."""
    config_path = tmp_path / "test" / "config.yaml"

    write_default_config(config_path)

    # File should exist
    assert config_path.exists()

    # Parent directory should be created
    assert config_path.parent.exists()

    # Content should match template
    content = config_path.read_text()
    assert content == DEFAULT_CONFIG_TEMPLATE

    # Should be valid YAML
    import yaml
    data = yaml.safe_load(content)
    assert "defaults" in data
    assert data["defaults"]["type"] == "task"
    assert data["defaults"]["priority"] == 2


def test_write_default_config_creates_parent_dirs(tmp_path):
    """Test that write_default_config creates parent directories."""
    config_path = tmp_path / "deep" / "nested" / "path" / "config.yaml"

    write_default_config(config_path)

    assert config_path.exists()
    assert config_path.parent.exists()


# ============================================================================
# Config Validation Tests
# ============================================================================


def test_validate_config_valid():
    """Test validating a valid configuration."""
    config = BodegaConfig()

    errors = validate_config(config)

    assert errors == []


def test_validate_config_invalid_priority():
    """Test validation catches invalid priority."""
    config = BodegaConfig(default_priority=5)
    errors = validate_config(config)

    assert len(errors) == 1
    assert "default_priority" in errors[0]
    assert "0-4" in errors[0]


def test_validate_config_invalid_priority_negative():
    """Test validation catches negative priority."""
    config = BodegaConfig(default_priority=-1)
    errors = validate_config(config)

    assert len(errors) == 1
    assert "default_priority" in errors[0]


def test_validate_config_invalid_type():
    """Test validation catches invalid ticket type."""
    config = BodegaConfig(default_type="invalid")
    errors = validate_config(config)

    assert len(errors) == 1
    assert "default_type" in errors[0]
    assert "invalid" in errors[0]


def test_validate_config_invalid_list_format():
    """Test validation catches invalid list format."""
    config = BodegaConfig(list_format="json")
    errors = validate_config(config)

    assert len(errors) == 1
    assert "list_format" in errors[0]


def test_validate_config_multiple_errors():
    """Test validation catches multiple errors."""
    config = BodegaConfig(
        default_priority=10,
        default_type="invalid_type",
        list_format="xml"
    )
    errors = validate_config(config)

    assert len(errors) == 3
    assert any("default_priority" in e for e in errors)
    assert any("default_type" in e for e in errors)
    assert any("list_format" in e for e in errors)


def test_validate_config_all_valid_types():
    """Test that all valid ticket types pass validation."""
    valid_types = ["bug", "feature", "task", "epic", "chore"]

    for ticket_type in valid_types:
        config = BodegaConfig(default_type=ticket_type)
        errors = validate_config(config)
        assert errors == [], f"Type {ticket_type} should be valid"


def test_validate_config_all_valid_priorities():
    """Test that all valid priorities pass validation."""
    for priority in range(5):  # 0-4
        config = BodegaConfig(default_priority=priority)
        errors = validate_config(config)
        assert errors == [], f"Priority {priority} should be valid"


def test_validate_config_all_valid_formats():
    """Test that all valid list formats pass validation."""
    valid_formats = ["table", "compact", "ids"]

    for fmt in valid_formats:
        config = BodegaConfig(list_format=fmt)
        errors = validate_config(config)
        assert errors == [], f"Format {fmt} should be valid"
