"""Tests for init command."""

import pytest
from pathlib import Path
import yaml

from bodega.cli import main
from bodega.config import get_offline_store_mapping


# ============================================================================
# Basic Init Tests
# ============================================================================

def test_init_creates_bodega_directory(runner):
    """Test that init creates .bodega directory."""
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init"])

        assert result.exit_code == 0
        assert Path(".bodega").exists()
        assert Path(".bodega/config.yaml").exists()


def test_init_with_reset_flag(runner):
    """Test that init --reset reinitializes existing repository."""
    with runner.isolated_filesystem():
        # First init
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        # Second init with --reset
        result = runner.invoke(main, ["init", "--reset"])
        assert result.exit_code == 0
        assert Path(".bodega").exists()


def test_init_without_reset_shows_existing(runner):
    """Test that init without --reset detects existing repository."""
    with runner.isolated_filesystem():
        # First init
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        # Second init without --reset
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert "existing" in result.output.lower()


# ============================================================================
# Offline Mode Tests
# ============================================================================

def test_init_offline_creates_store(runner, tmp_path, monkeypatch):
    """Test that init --offline creates offline store in ~/.bodega/."""
    with runner.isolated_filesystem():
        # Mock Path.home() to use tmp_path
        monkeypatch.setattr("bodega.commands.init.Path.home", lambda: tmp_path)
        monkeypatch.setattr("bodega.config.Path.home", lambda: tmp_path)

        result = runner.invoke(main, ["init", "--offline"])

        assert result.exit_code == 0
        assert "offline store" in result.output.lower()

        # Check that offline store was created
        offline_stores = list(tmp_path.glob(".bodega/*"))
        assert len(offline_stores) > 0


def test_init_offline_with_custom_name(runner, tmp_path, monkeypatch):
    """Test that init --offline --name uses custom name."""
    with runner.isolated_filesystem():
        # Mock Path.home() to use tmp_path
        monkeypatch.setattr("bodega.commands.init.Path.home", lambda: tmp_path)
        monkeypatch.setattr("bodega.config.Path.home", lambda: tmp_path)
        monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", tmp_path / ".bodega" / "config.yaml")

        result = runner.invoke(main, ["init", "--offline", "--name", "my-project"])

        assert result.exit_code == 0
        assert "offline store" in result.output.lower()

        # Check that store was created with custom name
        store_path = tmp_path / ".bodega" / "my-project"
        assert store_path.exists()
        assert (store_path / ".bodega").exists()


def test_init_offline_registers_in_global_config(runner, tmp_path, monkeypatch):
    """Test that init --offline registers store in global config."""
    with runner.isolated_filesystem():
        # Mock paths
        monkeypatch.setattr("bodega.commands.init.Path.home", lambda: tmp_path)
        monkeypatch.setattr("bodega.config.Path.home", lambda: tmp_path)
        global_config_path = tmp_path / ".bodega" / "config.yaml"
        monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", global_config_path)

        result = runner.invoke(main, ["init", "--offline", "--name", "test-proj"])

        assert result.exit_code == 0

        # Verify global config was updated
        mapping = get_offline_store_mapping()
        assert "test-proj" in mapping.values()


def test_init_offline_existing_without_reset_fails(runner, tmp_path, monkeypatch):
    """Test that init --offline fails if store exists without --reset."""
    with runner.isolated_filesystem():
        # Mock paths
        monkeypatch.setattr("bodega.commands.init.Path.home", lambda: tmp_path)
        monkeypatch.setattr("bodega.config.Path.home", lambda: tmp_path)
        monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", tmp_path / ".bodega" / "config.yaml")

        # First init
        result = runner.invoke(main, ["init", "--offline", "--name", "test"])
        assert result.exit_code == 0

        # Second init without --reset should fail
        result = runner.invoke(main, ["init", "--offline", "--name", "test"])
        assert result.exit_code == 1
        assert "already exists" in result.output.lower()


def test_init_offline_with_reset_reinitializes(runner, tmp_path, monkeypatch):
    """Test that init --offline --reset reinitializes existing store."""
    with runner.isolated_filesystem():
        # Mock paths
        monkeypatch.setattr("bodega.commands.init.Path.home", lambda: tmp_path)
        monkeypatch.setattr("bodega.config.Path.home", lambda: tmp_path)
        monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", tmp_path / ".bodega" / "config.yaml")

        # First init
        result = runner.invoke(main, ["init", "--offline", "--name", "test"])
        assert result.exit_code == 0

        # Second init with --reset should succeed
        result = runner.invoke(main, ["init", "--offline", "--name", "test", "--reset"])
        assert result.exit_code == 0
        assert "initialized" in result.output.lower()


# ============================================================================
# Flag Validation Tests
# ============================================================================

def test_init_offline_and_branch_conflict(runner):
    """Test that --offline and --branch cannot be used together."""
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init", "--offline", "--branch", "bodega"])

        assert result.exit_code == 1
        assert "cannot use --offline with --branch" in result.output.lower()


def test_init_name_without_offline_warning(runner):
    """Test that --name without --offline shows warning."""
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["init", "--name", "test"])

        # Should complete but show warning
        assert result.exit_code == 0
        assert "ignored" in result.output.lower() or "warning" in result.output.lower()


def test_init_offline_custom_name_findable(runner, tmp_path, monkeypatch):
    """Test that offline store with custom name can be found by identifier."""
    with runner.isolated_filesystem():
        # Mock paths
        monkeypatch.setattr("bodega.commands.init.Path.home", lambda: tmp_path)
        monkeypatch.setattr("bodega.config.Path.home", lambda: tmp_path)
        monkeypatch.setattr("bodega.utils.Path.home", lambda: tmp_path)
        monkeypatch.setattr("bodega.config.GLOBAL_CONFIG_PATH", tmp_path / ".bodega" / "config.yaml")

        # Create offline store with custom name
        result = runner.invoke(main, ["init", "--offline", "--name", "my-project"])
        assert result.exit_code == 0

        # Verify the store was created with custom name
        store_path = tmp_path / ".bodega" / "my-project"
        assert store_path.exists()

        # Verify the mapping uses the auto-generated identifier as key
        from bodega.config import get_offline_store_mapping
        mapping = get_offline_store_mapping()

        # Should have one entry
        assert len(mapping) == 1

        # The value should be the custom name
        assert "my-project" in mapping.values()
