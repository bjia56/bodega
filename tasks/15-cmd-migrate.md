# Task 15: Migrate Command

## Summary
Implement the `bodega migrate-beads` command to import tickets from a beads repository.

## Dependencies
- Task 01: Project Setup
- Task 02: Models (Ticket)
- Task 03: Utils (generate_id)
- Task 05: Storage (TicketStorage)
- Task 08: CLI Base

## Requirements

### 1. Beads Format

Beads stores issues in `.beads/issues.jsonl` (JSON Lines format). Each line is a JSON object:

```json
{
  "id": "bead-abc123",
  "title": "Fix login bug",
  "issue_type": "bug",
  "status": "open",
  "priority": 1,
  "assignee": "jane",
  "external_ref": "gh-123",
  "created_at": "2026-01-15T10:00:00Z",
  "dependencies": [
    {"type": "blocks", "target": "bead-def456"},
    {"type": "related", "target": "bead-ghi789"},
    {"type": "parent-child", "target": "bead-parent"}
  ],
  "description": "Login fails with invalid credentials",
  "design": "Use proper error handling",
  "acceptance_criteria": "- Login shows error message",
  "notes": "Discussed with team on 2026-01-14"
}
```

### 2. Migrate Command (`src/bodega/commands/migrate.py`)

```python
import click
import json
from pathlib import Path
from datetime import datetime

from ..cli import pass_context, Context, require_repo
from ..models import Ticket, TicketType, TicketStatus
from ..utils import generate_id

@click.command("migrate-beads")
@click.option("--path", "-p", type=click.Path(exists=True),
              help="Path to beads directory (default: .beads)")
@click.option("--dry-run", is_flag=True,
              help="Show what would be imported without writing")
@click.option("--preserve-ids", is_flag=True,
              help="Keep original beads IDs instead of generating new ones")
@pass_context
def migrate_beads(
    ctx: Context,
    path: str | None,
    dry_run: bool,
    preserve_ids: bool,
):
    """
    Import tickets from a beads repository.

    Reads .beads/issues.jsonl and creates bodega tickets.

    Examples:

        bodega migrate-beads

        bodega migrate-beads --path /other/project/.beads

        bodega migrate-beads --dry-run

        bodega migrate-beads --preserve-ids
    """
    storage = require_repo(ctx)

    # Find beads directory
    beads_path = Path(path) if path else Path.cwd() / ".beads"
    issues_file = beads_path / "issues.jsonl"

    if not issues_file.exists():
        click.echo(f"Error: Beads issues file not found: {issues_file}", err=True)
        raise SystemExit(1)

    # Read and parse beads issues
    issues = []
    with open(issues_file) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                issue = json.loads(line)
                issues.append(issue)
            except json.JSONDecodeError as e:
                click.echo(f"Warning: Invalid JSON on line {line_num}: {e}", err=True)

    if not issues:
        click.echo("No issues found to migrate.")
        return

    click.echo(f"Found {len(issues)} beads issues to migrate.")

    # Build ID mapping (old -> new)
    id_map = {}
    for issue in issues:
        old_id = issue.get("id", "")
        if preserve_ids:
            new_id = old_id
        else:
            new_id = generate_id(ctx.config.id_prefix)
        id_map[old_id] = new_id

    # Convert and save tickets
    migrated = 0
    for issue in issues:
        try:
            ticket = convert_beads_issue(issue, id_map, preserve_ids, ctx.config.id_prefix)

            if dry_run:
                click.echo(f"  Would create: {ticket.id} - {ticket.title}")
            else:
                storage.create(ticket)
                click.echo(f"  Created: {ticket.id} - {ticket.title}")

            migrated += 1

        except Exception as e:
            old_id = issue.get("id", "unknown")
            click.echo(f"  Error migrating {old_id}: {e}", err=True)

    if dry_run:
        click.echo(f"\nDry run complete. Would migrate {migrated} tickets.")
    else:
        click.echo(f"\nMigration complete. Created {migrated} tickets.")


def convert_beads_issue(
    issue: dict,
    id_map: dict[str, str],
    preserve_ids: bool,
    prefix: str,
) -> Ticket:
    """Convert a beads issue dict to a Ticket."""

    old_id = issue.get("id", "")
    new_id = id_map.get(old_id, generate_id(prefix))

    # Map status
    status_str = issue.get("status", "open")
    status_map = {
        "open": TicketStatus.OPEN,
        "in-progress": TicketStatus.IN_PROGRESS,
        "in_progress": TicketStatus.IN_PROGRESS,
        "closed": TicketStatus.CLOSED,
        "done": TicketStatus.CLOSED,
    }
    status = status_map.get(status_str, TicketStatus.OPEN)

    # Map type
    type_str = issue.get("issue_type", "task")
    type_map = {
        "bug": TicketType.BUG,
        "feature": TicketType.FEATURE,
        "task": TicketType.TASK,
        "epic": TicketType.EPIC,
        "chore": TicketType.CHORE,
    }
    ticket_type = type_map.get(type_str, TicketType.TASK)

    # Parse dependencies
    deps = []
    links = []
    parent = None

    for dep in issue.get("dependencies", []):
        dep_type = dep.get("type", "")
        target = dep.get("target", "")
        new_target = id_map.get(target, target)

        if dep_type == "blocks":
            deps.append(new_target)
        elif dep_type == "related":
            links.append(new_target)
        elif dep_type == "parent-child":
            parent = new_target

    # Parse timestamps
    created_str = issue.get("created_at")
    created = datetime.fromisoformat(created_str.replace("Z", "+00:00")) if created_str else datetime.utcnow()

    # Parse notes (could be string or list)
    notes_raw = issue.get("notes", [])
    if isinstance(notes_raw, str):
        notes = [notes_raw] if notes_raw else []
    else:
        notes = notes_raw

    return Ticket(
        id=new_id,
        title=issue.get("title", "Untitled"),
        type=ticket_type,
        status=status,
        priority=issue.get("priority", 2),
        assignee=issue.get("assignee"),
        tags=issue.get("tags", []),
        deps=deps,
        links=links,
        parent=parent,
        external_ref=issue.get("external_ref"),
        created=created,
        updated=created,  # Use created as initial updated
        description=issue.get("description"),
        design=issue.get("design"),
        acceptance_criteria=issue.get("acceptance_criteria"),
        notes=notes,
    )
```

## Field Mapping Reference

| Beads Field | Bodega Field | Notes |
|-------------|--------------|-------|
| `id` | `id` | Mapped through id_map |
| `title` | `title` | Direct |
| `issue_type` | `type` | Mapped to enum |
| `status` | `status` | Mapped to enum |
| `priority` | `priority` | Direct (default: 2) |
| `assignee` | `assignee` | Direct |
| `external_ref` | `external_ref` | Direct |
| `created_at` | `created` | Parsed as ISO datetime |
| `dependencies[type=blocks]` | `deps` | IDs remapped |
| `dependencies[type=related]` | `links` | IDs remapped |
| `dependencies[type=parent-child]` | `parent` | ID remapped |
| `description` | `description` | Direct |
| `design` | `design` | Direct |
| `acceptance_criteria` | `acceptance_criteria` | Direct |
| `notes` | `notes` | String or list |

## Acceptance Criteria

- [ ] Reads `.beads/issues.jsonl` correctly
- [ ] Creates bodega tickets with mapped fields
- [ ] Dependencies are remapped to new IDs
- [ ] `--dry-run` shows what would be created
- [ ] `--preserve-ids` keeps original IDs
- [ ] `--path` allows custom beads location
- [ ] Handles missing/invalid fields gracefully
- [ ] Reports progress and errors

## Test Cases

```python
from click.testing import CliRunner
from bodega.cli import main
from pathlib import Path
import json

def test_migrate_beads(tmp_path):
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Initialize bodega
        runner.invoke(main, ["init"])

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
                "status": "closed",
                "dependencies": [
                    {"type": "blocks", "target": "bead-001"}
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
        assert "2 tickets" in result.output

def test_migrate_dry_run(tmp_path):
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(main, ["init"])

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
        assert "No tickets" in result.output

def test_migrate_preserve_ids(tmp_path):
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        runner.invoke(main, ["init"])

        beads_dir = Path(".beads")
        beads_dir.mkdir()
        with open(beads_dir / "issues.jsonl", "w") as f:
            f.write(json.dumps({"id": "bead-abc123", "title": "Test"}) + "\n")

        result = runner.invoke(main, ["migrate-beads", "--preserve-ids"])
        assert result.exit_code == 0

        # Check ticket has original ID
        result = runner.invoke(main, ["show", "bead-abc123"])
        assert result.exit_code == 0
```
