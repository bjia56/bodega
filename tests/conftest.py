import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def tmp_bodega_dir(tmp_path):
    """Create a temporary .bodega directory for tests."""
    bodega_dir = tmp_path / ".bodega"
    bodega_dir.mkdir()
    yield bodega_dir
    # Cleanup is handled automatically by tmp_path


@pytest.fixture
def sample_ticket():
    """A sample ticket dict for testing."""
    return {
        "id": "TASK-001",
        "title": "Sample Task",
        "status": "open",
        "description": "This is a sample task for testing",
        "created": "2026-01-28T10:00:00Z",
        "updated": "2026-01-28T10:00:00Z",
        "tags": ["test", "sample"],
        "dependencies": [],
    }
