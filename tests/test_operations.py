"""Tests for bodega.operations shared business logic."""

from bodega.config import BodegaConfig
from bodega.operations import create_ticket
from bodega.storage import TicketStorage


def test_create_ticket_default_uses_storage_config_prefix(temp_repo):
    """Test create_ticket without id_prefix defers to storage's config.id_prefix."""
    project_dir = temp_repo
    config = BodegaConfig(bodega_dir=project_dir / ".bodega", id_prefix="core")
    storage = TicketStorage(config)

    ticket, _ = create_ticket(storage, config, title="Task")

    assert ticket.id.startswith("core-")


def test_create_ticket_explicit_id_prefix_overrides_config(temp_repo):
    """Test create_ticket's id_prefix param bypasses config.id_prefix entirely."""
    project_dir = temp_repo
    config = BodegaConfig(bodega_dir=project_dir / ".bodega", id_prefix="core")
    storage = TicketStorage(config)

    ticket, _ = create_ticket(storage, config, title="Task", id_prefix="svc")

    assert ticket.id.startswith("svc-")
