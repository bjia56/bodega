"""Tests for migrate-beads command."""

from pathlib import Path
import json

from bodega.cli import main


# ============================================================================
# Basic Migration Tests
# ============================================================================

def test_migrate_beads_basic(runner, temp_repo):
    """Test basic migration from beads format."""
    # Create beads directory with test data
    beads_dir = Path(".beads")
    beads_dir.mkdir()

    issues = [
        {
            "id": "bead-001",
            "title": "Test issue 1",
            "issue_type": "bug",
            "status": "open",
            "priority": 1,
        },
        {
            "id": "bead-002",
            "title": "Test issue 2",
            "issue_type": "task",
            "status": "open",
            "dependencies": [
                {"type": "blocks", "depends_on_id": "bead-001"}
            ],
        },
    ]

    with open(beads_dir / "issues.jsonl", "w") as f:
        for issue in issues:
            f.write(json.dumps(issue) + "\n")

    # Run migration
    result = runner.invoke(main, ["migrate-beads"])
    assert result.exit_code == 0
    assert "Created" in result.output
    assert "2" in result.output

    # Verify tickets were created
    result = runner.invoke(main, ["list"])
    assert result.exit_code == 0
    assert "Test issue 1" in result.output
    assert "Test issue 2" in result.output


def test_migrate_beads_dry_run(runner, temp_repo):
    """Test dry run mode doesn't create tickets."""
    beads_dir = Path(".beads")
    beads_dir.mkdir()

    with open(beads_dir / "issues.jsonl", "w") as f:
        f.write(json.dumps({"id": "test", "title": "Test"}) + "\n")

    result = runner.invoke(main, ["migrate-beads", "--dry-run"])
    assert result.exit_code == 0
    assert "Would create" in result.output
    assert "Dry run" in result.output

    # Verify no tickets were actually created
    result = runner.invoke(main, ["list"])
    assert "No tickets" in result.output or "Test" not in result.output


def test_migrate_beads_preserve_ids(runner, temp_repo):
    """Test preserving original beads IDs."""
    beads_dir = Path(".beads")
    beads_dir.mkdir()

    with open(beads_dir / "issues.jsonl", "w") as f:
        f.write(json.dumps({"id": "bead-abc123", "title": "Test"}) + "\n")

    result = runner.invoke(main, ["migrate-beads", "--preserve-ids"])
    assert result.exit_code == 0

    # Check ticket has original ID
    result = runner.invoke(main, ["peek", "bead-abc123"])
    assert result.exit_code == 0
    assert "Test" in result.output


def test_migrate_beads_custom_path(runner, temp_repo):
    """Test migration with custom beads path."""
    # Create beads directory in custom location
    custom_dir = Path("other/.beads")
    custom_dir.mkdir(parents=True)

    with open(custom_dir / "issues.jsonl", "w") as f:
        f.write(json.dumps({"id": "test", "title": "Custom Path Test"}) + "\n")

    result = runner.invoke(main, ["migrate-beads", "--path", "other/.beads"])
    assert result.exit_code == 0
    assert "Created" in result.output


def test_migrate_beads_missing_file(runner, temp_repo):
    """Test error handling when beads file doesn't exist."""
    result = runner.invoke(main, ["migrate-beads"])
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_migrate_beads_empty_file(runner, temp_repo):
    """Test migration with empty beads file."""
    beads_dir = Path(".beads")
    beads_dir.mkdir()

    # Create empty file
    (beads_dir / "issues.jsonl").touch()

    result = runner.invoke(main, ["migrate-beads"])
    assert result.exit_code == 0
    assert "No issues found" in result.output


# ============================================================================
# Field Mapping Tests
# ============================================================================

def test_migrate_beads_all_fields(runner, temp_repo):
    """Test migration with all fields populated."""
    beads_dir = Path(".beads")
    beads_dir.mkdir()

    issue = {
        "id": "bead-full",
        "title": "Full Issue",
        "issue_type": "feature",
        "status": "in-progress",
        "priority": 3,
        "owner": "john",
        "external_ref": "gh-456",
        "created_at": "2026-01-15T10:00:00Z",
        "labels": ["urgent", "backend"],
        "description": "Detailed description",
        "design": "Design notes",
        "acceptance_criteria": "AC notes",
        "notes": ["Note 1", "Note 2"],
    }

    with open(beads_dir / "issues.jsonl", "w") as f:
        f.write(json.dumps(issue) + "\n")

    result = runner.invoke(main, ["migrate-beads", "--preserve-ids"])
    assert result.exit_code == 0

    # Verify all fields
    result = runner.invoke(main, ["peek", "--json", "bead-full"])
    assert result.exit_code == 0
    data = json.loads(result.output)

    assert data["title"] == "Full Issue"
    assert data["type"] == "feature"
    assert data["status"] == "in-progress"
    assert data["priority"] == 3
    assert data["assignee"] == "john"
    assert data["external_ref"] == "gh-456"
    assert "urgent" in data["tags"]
    assert "backend" in data["tags"]


def test_migrate_beads_status_mapping(runner, temp_repo):
    """Test status field mapping."""
    beads_dir = Path(".beads")
    beads_dir.mkdir()

    test_cases = [
        ("open", "open"),
        ("in-progress", "in-progress"),
        ("in_progress", "in-progress"),
        ("closed", "closed"),
        ("done", "closed"),
    ]

    for beads_status, expected_status in test_cases:
        issue_id = f"bead-{beads_status}"
        issue = {
            "id": issue_id,
            "title": f"Test {beads_status}",
            "status": beads_status,
        }

        with open(beads_dir / "issues.jsonl", "a") as f:
            f.write(json.dumps(issue) + "\n")

    result = runner.invoke(main, ["migrate-beads", "--preserve-ids"])
    assert result.exit_code == 0

    # Verify status mappings
    for beads_status, expected_status in test_cases:
        issue_id = f"bead-{beads_status}"
        result = runner.invoke(main, ["peek", "--json", issue_id])
        if result.exit_code == 0:
            data = json.loads(result.output)
            assert data["status"] == expected_status


def test_migrate_beads_type_mapping(runner, temp_repo):
    """Test issue type field mapping."""
    beads_dir = Path(".beads")
    beads_dir.mkdir()

    issue_types = ["bug", "feature", "task", "epic", "chore"]

    for issue_type in issue_types:
        issue = {
            "id": f"bead-{issue_type}",
            "title": f"Test {issue_type}",
            "issue_type": issue_type,
        }

        with open(beads_dir / "issues.jsonl", "a") as f:
            f.write(json.dumps(issue) + "\n")

    result = runner.invoke(main, ["migrate-beads", "--preserve-ids"])
    assert result.exit_code == 0

    # Verify type mappings
    for issue_type in issue_types:
        issue_id = f"bead-{issue_type}"
        result = runner.invoke(main, ["peek", "--json", issue_id])
        if result.exit_code == 0:
            data = json.loads(result.output)
            assert data["type"] == issue_type


# ============================================================================
# Dependency Migration Tests
# ============================================================================

def test_migrate_beads_dependencies(runner, temp_repo):
    """Test migration of dependencies with ID remapping."""
    beads_dir = Path(".beads")
    beads_dir.mkdir()

    issues = [
        {
            "id": "bead-001",
            "title": "Blocker",
        },
        {
            "id": "bead-002",
            "title": "Blocked",
            "dependencies": [
                {"type": "blocks", "depends_on_id": "bead-001"}
            ],
        },
    ]

    with open(beads_dir / "issues.jsonl", "w") as f:
        for issue in issues:
            f.write(json.dumps(issue) + "\n")

    result = runner.invoke(main, ["migrate-beads"])
    assert result.exit_code == 0

    # Get the new IDs from output
    lines = [line.strip() for line in result.output.split("\n") if "Created:" in line]
    assert len(lines) == 2


def test_migrate_beads_links(runner, temp_repo):
    """Test migration of related links."""
    beads_dir = Path(".beads")
    beads_dir.mkdir()

    issues = [
        {
            "id": "bead-001",
            "title": "Issue 1",
        },
        {
            "id": "bead-002",
            "title": "Issue 2",
            "dependencies": [
                {"type": "related", "depends_on_id": "bead-001"}
            ],
        },
    ]

    with open(beads_dir / "issues.jsonl", "w") as f:
        for issue in issues:
            f.write(json.dumps(issue) + "\n")

    result = runner.invoke(main, ["migrate-beads", "--preserve-ids"])
    assert result.exit_code == 0

    # Verify link was created
    result = runner.invoke(main, ["peek", "--json", "bead-002"])
    data = json.loads(result.output)
    assert "bead-001" in data["links"]


def test_migrate_beads_parent_child(runner, temp_repo):
    """Test migration of parent-child relationships."""
    beads_dir = Path(".beads")
    beads_dir.mkdir()

    issues = [
        {
            "id": "bead-parent",
            "title": "Parent",
        },
        {
            "id": "bead-child",
            "title": "Child",
            "dependencies": [
                {"type": "parent-child", "depends_on_id": "bead-parent"}
            ],
        },
    ]

    with open(beads_dir / "issues.jsonl", "w") as f:
        for issue in issues:
            f.write(json.dumps(issue) + "\n")

    result = runner.invoke(main, ["migrate-beads", "--preserve-ids"])
    assert result.exit_code == 0

    # Verify parent was set
    result = runner.invoke(main, ["peek", "--json", "bead-child"])
    data = json.loads(result.output)
    assert data["parent"] == "bead-parent"


# ============================================================================
# Error Handling Tests
# ============================================================================

def test_migrate_beads_invalid_json(runner, temp_repo):
    """Test handling of invalid JSON lines."""
    beads_dir = Path(".beads")
    beads_dir.mkdir()

    with open(beads_dir / "issues.jsonl", "w") as f:
        f.write(json.dumps({"id": "good", "title": "Good"}) + "\n")
        f.write("{ invalid json }\n")
        f.write(json.dumps({"id": "good2", "title": "Good 2"}) + "\n")

    result = runner.invoke(main, ["migrate-beads"])
    # Should succeed but show warning
    assert result.exit_code == 0
    assert "Warning" in result.output or "Invalid" in result.output
    assert "2 tickets" in result.output or "Created" in result.output


def test_migrate_beads_notes_string(runner, temp_repo):
    """Test migration with notes as string instead of list."""
    beads_dir = Path(".beads")
    beads_dir.mkdir()

    issue = {
        "id": "bead-notes",
        "title": "Notes Test",
        "notes": "Single note string",
    }

    with open(beads_dir / "issues.jsonl", "w") as f:
        f.write(json.dumps(issue) + "\n")

    result = runner.invoke(main, ["migrate-beads", "--preserve-ids"])
    assert result.exit_code == 0

    # Verify notes were converted to list
    result = runner.invoke(main, ["peek", "--json", "bead-notes"])
    data = json.loads(result.output)
    assert isinstance(data["notes"], list)
    assert "Single note string" in data["notes"]


def test_migrate_beads_minimal_fields(runner, temp_repo):
    """Test migration with only required fields."""
    beads_dir = Path(".beads")
    beads_dir.mkdir()

    issue = {
        "id": "bead-minimal",
        "title": "Minimal",
    }

    with open(beads_dir / "issues.jsonl", "w") as f:
        f.write(json.dumps(issue) + "\n")

    result = runner.invoke(main, ["migrate-beads", "--preserve-ids"])
    assert result.exit_code == 0

    # Verify defaults were applied
    result = runner.invoke(main, ["peek", "--json", "bead-minimal"])
    data = json.loads(result.output)
    assert data["title"] == "Minimal"
    assert data["status"] == "open"
    assert data["type"] == "task"
    assert data["priority"] == 2
