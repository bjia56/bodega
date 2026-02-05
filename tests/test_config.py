import yaml

from bodega.config import (
    BodegaConfig,
    load_config,
    write_default_config,
    validate_config,
    DEFAULT_CONFIG_TEMPLATE,
    get_offline_store_mapping,
    set_offline_store_mapping,
    list_offline_stores,
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
    monkeypatch.chdir(subdir)
    monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", tmp_path / "nonexistent")

    config = load_config()

    assert config.bodega_dir == bodega_dir
    assert config.id_prefix == "found"


def test_load_config_empty_yaml(tmp_path, monkeypatch, runner):
    """Test loading config with empty YAML file."""
    with runner.isolated_filesystem():
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


def test_write_default_config(tmp_path, runner):
    """Test writing default config template."""
    with runner.isolated_filesystem():
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
        data = yaml.safe_load(content)
        assert "defaults" in data
        assert data["defaults"]["type"] == "task"
        assert data["defaults"]["priority"] == 2


def test_write_default_config_creates_parent_dirs(tmp_path, runner):
    """Test that write_default_config creates parent directories."""
    with runner.isolated_filesystem():
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


# ============================================================================
# ID Prefix Derivation Tests
# ============================================================================


def test_id_prefix_derived_from_folder_name(tmp_path, monkeypatch, runner):
    """Test that id_prefix is derived from folder name when not explicitly set."""
    with runner.isolated_filesystem():
        # Create .bodega directory in a folder named "myproject"
        project_dir = tmp_path / "myproject" / ".bodega"
        project_dir.mkdir(parents=True)

        monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", tmp_path / "nonexistent")

        config = load_config(project_dir)

        # Should derive "myproject" as the prefix
        assert config.id_prefix == "myproject"


def test_id_prefix_explicit_overrides_derivation(tmp_path, monkeypatch, runner):
    """Test that explicit id_prefix in config overrides folder name derivation."""
    with runner.isolated_filesystem():
        # Create .bodega directory in a folder named "myproject"
        project_dir = tmp_path / "myproject" / ".bodega"
        project_dir.mkdir(parents=True)

        # Set explicit id_prefix in config
        config_file = project_dir / "config.yaml"
        config_file.write_text("id_prefix: bg\n")

        monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", tmp_path / "nonexistent")

        config = load_config(project_dir)

        # Should use explicit "bg", not derive "myproject"
        assert config.id_prefix == "bg"


def test_id_prefix_derivation_with_special_chars(tmp_path, monkeypatch, runner):
    """Test that id_prefix derivation strips special characters."""
    with runner.isolated_filesystem():
        # Create .bodega directory in a folder with special characters
        project_dir = tmp_path / "my-cool_project.v2" / ".bodega"
        project_dir.mkdir(parents=True)

        monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", tmp_path / "nonexistent")

        config = load_config(project_dir)

        # Should derive "mycoolprojectv2" (alphanumeric only)
        assert config.id_prefix == "mycoolprojectv2"


def test_id_prefix_derivation_falls_back_to_bg(tmp_path, monkeypatch, runner):
    """Test that id_prefix falls back to 'bg' when folder name is invalid."""
    with runner.isolated_filesystem():
        # Create .bodega directory in a folder starting with number
        project_dir = tmp_path / "123-project" / ".bodega"
        project_dir.mkdir(parents=True)

        monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", tmp_path / "nonexistent")

        config = load_config(project_dir)

        # Should fall back to "bg" since name starts with digit
        assert config.id_prefix == "bg"


def test_id_prefix_derivation_no_bodega_dir(tmp_path, monkeypatch, runner):
    """Test that id_prefix falls back to 'bg' when no bodega dir found."""
    with runner.isolated_filesystem():
        monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", tmp_path / "nonexistent")

        config = load_config()

        # Should fall back to "bg" when no bodega dir
        assert config.id_prefix == "bg"


def test_id_prefix_global_config_overrides_derivation(tmp_path, monkeypatch, runner):
    """Test that global config id_prefix overrides folder name derivation."""
    with runner.isolated_filesystem():
        # Create global config with explicit id_prefix
        global_dir = tmp_path / "global" / ".bodega"
        global_dir.mkdir(parents=True)
        global_config = global_dir / "config.yaml"
        global_config.write_text("id_prefix: custom\n")

        # Create project in folder named "myproject"
        project_dir = tmp_path / "myproject" / ".bodega"
        project_dir.mkdir(parents=True)

        monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", global_config)

        config = load_config(project_dir)

        # Should use global config "custom", not derive "myproject"
        assert config.id_prefix == "custom"


def test_id_prefix_derivation_mixed_case(tmp_path, monkeypatch, runner):
    """Test that id_prefix derivation converts to lowercase."""
    with runner.isolated_filesystem():
        # Create .bodega directory in a folder with mixed case
        project_dir = tmp_path / "MyAwesomeProject" / ".bodega"
        project_dir.mkdir(parents=True)

        monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", tmp_path / "nonexistent")

        config = load_config(project_dir)

        # Should derive "myawesomeproject" (all lowercase)
        assert config.id_prefix == "myawesomeproject"


# ============================================================================
# Offline Mode Tests
# ============================================================================


def test_offline_mode_default_values():
    """Test that offline mode fields have correct default values."""
    config = BodegaConfig()

    assert config.offline_mode is False
    assert config.offline_store_path is None


def test_offline_mode_detected_under_home_bodega(tmp_path, monkeypatch, runner):
    """Test that offline mode is detected when bodega_dir is under ~/.bodega/."""
    with runner.isolated_filesystem():
        # Create a bodega directory under ~/.bodega/project-name/
        home_bodega = tmp_path / ".bodega"
        project_dir = home_bodega / "myproject" / ".bodega"
        project_dir.mkdir(parents=True)

        # Mock Path.home() to return tmp_path
        monkeypatch.setattr("bodega.config.Path.home", lambda: tmp_path)
        monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", tmp_path / "nonexistent")

        config = load_config(project_dir)

        # Should detect offline mode
        assert config.offline_mode is True
        assert config.offline_store_path == project_dir


def test_offline_mode_not_detected_outside_home_bodega(tmp_path, monkeypatch, runner):
    """Test that offline mode is not detected for normal project repositories."""
    with runner.isolated_filesystem():
        # Create a bodega directory in a regular project location
        project_dir = tmp_path / "workspace" / "myproject" / ".bodega"
        project_dir.mkdir(parents=True)

        # Mock Path.home() to something different
        monkeypatch.setattr("bodega.config.Path.home", lambda: tmp_path / "home")
        monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", tmp_path / "nonexistent")

        config = load_config(project_dir)

        # Should NOT detect offline mode
        assert config.offline_mode is False
        assert config.offline_store_path is None


def test_offline_mode_no_bodega_dir_found(tmp_path, monkeypatch, runner):
    """Test that offline mode is False when no bodega_dir is found."""
    with runner.isolated_filesystem():
        monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", tmp_path / "nonexistent")

        config = load_config()

        # Should not have offline mode enabled
        assert config.offline_mode is False
        assert config.offline_store_path is None


# ============================================================================
# Offline Store Mapping Tests
# ============================================================================


def test_get_offline_store_mapping_no_config(tmp_path, monkeypatch):
    """Test getting offline store mapping when no config exists."""
    # Point to non-existent config file
    monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", tmp_path / "nonexistent" / "config.yaml")

    mapping = get_offline_store_mapping()

    assert mapping == {}


def test_get_offline_store_mapping_empty_config(tmp_path, monkeypatch):
    """Test getting offline store mapping from empty config."""
    # Create empty config
    config_file = tmp_path / "config.yaml"
    config_file.write_text("")

    monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", config_file)

    mapping = get_offline_store_mapping()

    assert mapping == {}


def test_get_offline_store_mapping_no_stores_section(tmp_path, monkeypatch):
    """Test getting offline store mapping when config has no offline_stores section."""
    # Create config without offline_stores
    config_file = tmp_path / "config.yaml"
    config_file.write_text("id_prefix: bg\n")

    monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", config_file)

    mapping = get_offline_store_mapping()

    assert mapping == {}


def test_get_offline_store_mapping_with_stores(tmp_path, monkeypatch):
    """Test getting offline store mapping with existing stores."""
    # Create config with offline_stores
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
offline_stores:
  git-a1b2c3d4e5f6: my-project
  path-9f8e7d6c5b4a: personal-tasks
""")

    monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", config_file)

    mapping = get_offline_store_mapping()

    assert mapping == {
        "git-a1b2c3d4e5f6": "my-project",
        "path-9f8e7d6c5b4a": "personal-tasks"
    }


def test_set_offline_store_mapping_new_config(tmp_path, monkeypatch):
    """Test setting offline store mapping creates new config if it doesn't exist."""
    config_file = tmp_path / ".bodega" / "config.yaml"

    monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", config_file)

    set_offline_store_mapping("git-abc123", "test-project")

    # Verify file was created
    assert config_file.exists()

    # Verify content
    with open(config_file) as f:
        data = yaml.safe_load(f)

    assert data["offline_stores"]["git-abc123"] == "test-project"


def test_set_offline_store_mapping_existing_config(tmp_path, monkeypatch):
    """Test setting offline store mapping preserves existing config."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
id_prefix: custom
defaults:
  type: bug
""")

    monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", config_file)

    set_offline_store_mapping("git-def456", "another-project")

    # Verify content was preserved and mapping added
    with open(config_file) as f:
        data = yaml.safe_load(f)

    assert data["id_prefix"] == "custom"
    assert data["defaults"]["type"] == "bug"
    assert data["offline_stores"]["git-def456"] == "another-project"


def test_set_offline_store_mapping_update_existing(tmp_path, monkeypatch):
    """Test updating an existing offline store mapping."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
offline_stores:
  git-abc123: old-name
""")

    monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", config_file)

    set_offline_store_mapping("git-abc123", "new-name")

    # Verify mapping was updated
    with open(config_file) as f:
        data = yaml.safe_load(f)

    assert data["offline_stores"]["git-abc123"] == "new-name"


def test_set_offline_store_mapping_add_to_existing_stores(tmp_path, monkeypatch):
    """Test adding a new mapping to existing offline_stores section."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
offline_stores:
  git-existing: existing-project
""")

    monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", config_file)

    set_offline_store_mapping("git-new", "new-project")

    # Verify both mappings exist
    with open(config_file) as f:
        data = yaml.safe_load(f)

    assert data["offline_stores"]["git-existing"] == "existing-project"
    assert data["offline_stores"]["git-new"] == "new-project"


def test_list_offline_stores_empty(tmp_path, monkeypatch):
    """Test listing offline stores when none exist."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("")

    monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", config_file)
    monkeypatch.setattr("bodega.config.Path.home", lambda: tmp_path)

    stores = list_offline_stores()

    assert stores == []


def test_list_offline_stores_with_stores(tmp_path, monkeypatch):
    """Test listing offline stores returns correct metadata."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
offline_stores:
  git-abc123: my-project
  path-def456: another-project
""")

    monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", config_file)
    monkeypatch.setattr("bodega.config.Path.home", lambda: tmp_path)

    stores = list_offline_stores()

    # Should return list of tuples
    assert len(stores) == 2

    # Check first store
    identifier1, name1, path1 = stores[0]
    assert identifier1 == "git-abc123"
    assert name1 == "my-project"
    assert path1 == tmp_path / ".bodega" / "git-abc123"

    # Check second store
    identifier2, name2, path2 = stores[1]
    assert identifier2 == "path-def456"
    assert name2 == "another-project"
    assert path2 == tmp_path / ".bodega" / "path-def456"


def test_list_offline_stores_paths_regardless_of_existence(tmp_path, monkeypatch):
    """Test that list_offline_stores returns paths even if directories don't exist."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
offline_stores:
  git-abc123: my-project
""")

    monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", config_file)
    monkeypatch.setattr("bodega.config.Path.home", lambda: tmp_path)

    stores = list_offline_stores()

    assert len(stores) == 1
    identifier, name, path = stores[0]

    # Path should be returned even though it doesn't exist
    assert path == tmp_path / ".bodega" / "git-abc123"
    assert not path.exists()
