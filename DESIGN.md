# Bodega Design Document

A git-native issue/task tracking CLI for developers and AI agents, written in Python.

## Overview

Bodega is a local-first issue tracker that stores tickets as markdown files with YAML frontmatter. Inspired by [ticket](https://github.com/wedow/ticket), it provides dependency management, flexible querying, and seamless git integration without requiring databases or external services.

### Design Goals

1. **Git-native**: All data stored as plain text files, version-controlled alongside code
2. **AI-agent friendly**: Searchable markdown format, JSON output for scripting
3. **Zero setup**: Works immediately after `bodega init`
4. **Simple workflow**: Minimal commands for common operations
5. **Dependency tracking**: First-class support for blocking relationships and dependency graphs

## Data Model

### Ticket Structure

Tickets are stored as markdown files with YAML frontmatter in the `.bodega/` directory.

**File format:** `.bodega/{id}.md`

```yaml
---
id: bg-a1b2c3
title: Implement user authentication
type: task
status: open
priority: 2
assignee: jane
tags:
  - backend
  - security
deps:
  - bg-d4e5f6
links:
  - bg-g7h8i9
parent: bg-j0k1l2
external_ref: gh-123
created: 2026-01-28T10:00:00Z
updated: 2026-01-28T14:30:00Z
---
## Description

Implement JWT-based authentication for the API endpoints.

## Design

Use the `pyjwt` library with RS256 signing.

## Acceptance Criteria

- [ ] Login endpoint returns JWT token
- [ ] Protected routes validate token
- [ ] Token expiration handled gracefully

## Notes

- 2026-01-28 10:00: Created ticket
- 2026-01-28 14:30: Added design section
```

### Field Definitions

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | string | yes | auto-generated | Unique identifier (format: `bg-{6 hex chars}`) |
| `title` | string | yes | - | Short description of the ticket |
| `type` | enum | yes | `task` | One of: `bug`, `feature`, `task`, `epic`, `chore` |
| `status` | enum | yes | `open` | One of: `open`, `in-progress`, `closed` |
| `priority` | int | no | `2` | Priority level 0-4 (0 = highest/critical) |
| `assignee` | string | no | git user.name | Person responsible for the ticket |
| `tags` | list[string] | no | `[]` | Classification tags |
| `deps` | list[string] | no | `[]` | Ticket IDs that block this ticket |
| `links` | list[string] | no | `[]` | Related ticket IDs (symmetric) |
| `parent` | string | no | - | Parent ticket ID for hierarchies |
| `external_ref` | string | no | - | External reference (e.g., `gh-123`, `JIRA-456`) |
| `created` | datetime | yes | auto | ISO 8601 creation timestamp |
| `updated` | datetime | yes | auto | ISO 8601 last modified timestamp |

### ID Generation

IDs use the format `bg-{hash}` where:
- `bg` is the bodega prefix
- `{hash}` is 6 lowercase hexadecimal characters derived from UUID4

Partial ID matching is supported - `bg-a1b` matches `bg-a1b2c3` if unambiguous.

### Status Workflow

```
    +--------+
    |  open  |
    +--------+
        |
        v
  +-------------+
  | in-progress |
  +-------------+
        |
        v
    +--------+
    | closed |
    +--------+
        |
        v (reopen)
    +--------+
    |  open  |
    +--------+
```

### Priority Levels

| Level | Meaning |
|-------|---------|
| 0 | Critical - drop everything |
| 1 | High - address soon |
| 2 | Normal - standard priority (default) |
| 3 | Low - when time permits |
| 4 | Backlog - someday/maybe |

## Configuration

Bodega uses a layered configuration system with the following precedence (highest to lowest):

1. **Environment variables**
2. **Project config**: `.bodega/config.yaml`
3. **Global config**: `~/.bodega/config.yaml`
4. **Built-in defaults**

### Configuration File Format

```yaml
# ~/.bodega/config.yaml or .bodega/config.yaml

# Default values for new tickets
defaults:
  type: task
  priority: 2
  assignee: ""  # empty = use git user.name

# ID prefix (default: bg)
id_prefix: bg

# Editor command (overrides $EDITOR)
editor: vim

# Output format for list commands
list_format: table  # table, compact, ids

# Date format for display
date_format: "%Y-%m-%d %H:%M"
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BODEGA_DIR` | Override ticket storage location | `.bodega` |
| `EDITOR` | Editor for `bodega edit` command | `vi` |
| `NO_COLOR` | Disable colored output | unset |

## CLI Commands

### Initialization

#### `bodega init`

Initialize a new bodega repository in the current directory.

```bash
bodega init
# Creates .bodega/ directory with config.yaml template
```

**Options:**
- `--force`: Reinitialize existing directory

---

### Ticket Lifecycle

#### `bodega create`

Create a new ticket.

```bash
bodega create "Fix login bug"
bodega create -t bug -p 1 "Fix login bug"
bodega create -t feature --tag api --tag v2 "Add user profiles"
bodega create  # Opens $EDITOR for interactive creation
```

**Options:**
| Option | Short | Description |
|--------|-------|-------------|
| `--type` | `-t` | Ticket type (bug/feature/task/epic/chore) |
| `--priority` | `-p` | Priority level (0-4) |
| `--assignee` | `-a` | Assignee name |
| `--tag` | | Tag (repeatable) |
| `--parent` | | Parent ticket ID |
| `--external-ref` | `-e` | External reference |
| `--dep` | `-d` | Blocking ticket ID (repeatable) |

**Output:** Prints the created ticket ID.

#### `bodega start <id>`

Set ticket status to `in-progress`.

```bash
bodega start bg-a1b2c3
bodega start a1b  # Partial ID match
```

#### `bodega close <id>`

Set ticket status to `closed`.

```bash
bodega close bg-a1b2c3
```

#### `bodega reopen <id>`

Set ticket status back to `open`.

```bash
bodega reopen bg-a1b2c3
```

#### `bodega status <id>`

Get ticket status.

```bash
bodega status bg-a1b2c3
```

---

### Viewing & Editing

#### `bodega show <id>`

Display full ticket details.

```bash
bodega show bg-a1b2c3
bodega show a1b  # Partial ID
```

**Options:**
| Option | Description |
|--------|-------------|
| `--json` | Output as JSON |
| `--raw` | Output raw markdown file |

#### `bodega edit <id>`

Open ticket in `$EDITOR` for editing.

```bash
bodega edit bg-a1b2c3
```

#### `bodega note <id> <text>`

Append a timestamped note to the ticket.

```bash
bodega note bg-a1b2c3 "Blocked waiting for API spec"
```

Appends to the `## Notes` section:
```markdown
- 2026-01-28 14:30: Blocked waiting for API spec
```

---

### Listing & Querying

#### `bodega list`

List tickets with optional filters.

```bash
bodega list                          # All open tickets
bodega list --all                    # All tickets including closed
bodega list --status in-progress     # Filter by status
bodega list --type bug               # Filter by type
bodega list --tag api                # Filter by tag
bodega list --assignee jane          # Filter by assignee
bodega list --priority 0             # Filter by priority
bodega list -s open -t bug --tag api # Combined filters
```

**Options:**
| Option | Short | Description |
|--------|-------|-------------|
| `--all` | `-a` | Include closed tickets |
| `--status` | `-s` | Filter by status |
| `--type` | `-t` | Filter by type |
| `--tag` | | Filter by tag |
| `--assignee` | | Filter by assignee |
| `--priority` | `-p` | Filter by priority |
| `--sort` | | Sort by: priority, created, updated (default: priority) |
| `--reverse` | `-r` | Reverse sort order |
| `--format` | `-f` | Output format: table, compact, ids |

**Output formats:**

*table (default):*
```
ID          TYPE    PRI  STATUS       TITLE
bg-a1b2c3   bug     1    open         Fix login bug
bg-d4e5f6   task    2    in-progress  Update documentation
```

*compact:*
```
bg-a1b2c3 [bug/1] Fix login bug
bg-d4e5f6 [task/2] Update documentation
```

*ids:*
```
bg-a1b2c3
bg-d4e5f6
```

#### `bodega ready`

List tickets that are unblocked and ready to work on.

```bash
bodega ready
```

Shows open tickets where all dependencies are closed.

#### `bodega blocked`

List tickets that are blocked by dependencies.

```bash
bodega blocked
```

Shows open tickets with unresolved dependencies.

#### `bodega closed`

List recently closed tickets.

```bash
bodega closed         # Last 10 closed
bodega closed -n 20   # Last 20 closed
```

**Options:**
| Option | Short | Description |
|--------|-------|-------------|
| `--count` | `-n` | Number of tickets to show (default: 10) |

#### `bodega query`

Output tickets as JSON for scripting and jq integration.

```bash
bodega query                           # All open tickets as JSON array
bodega query --all                     # All tickets
bodega query --status closed           # Filtered
bodega query | jq '.[].title'          # Pipe to jq
bodega query --id bg-a1b2c3            # Single ticket
```

**Options:**
Same filters as `bodega list`, plus:
| Option | Description |
|--------|-------------|
| `--id` | Query single ticket by ID |
| `--pretty` | Pretty-print JSON (default if stdout is TTY) |

**Output:**
```json
[
  {
    "id": "bg-a1b2c3",
    "title": "Fix login bug",
    "type": "bug",
    "status": "open",
    "priority": 1,
    "assignee": "jane",
    "tags": ["backend"],
    "deps": [],
    "links": [],
    "parent": null,
    "external_ref": null,
    "created": "2026-01-28T10:00:00Z",
    "updated": "2026-01-28T10:00:00Z",
    "description": "...",
    "design": null,
    "acceptance_criteria": null,
    "notes": ["2026-01-28 10:00: Created"]
  }
]
```

---

### Dependencies & Links

#### `bodega dep <id> <blocker-id>`

Add a dependency (blocker-id blocks id).

```bash
bodega dep bg-a1b2c3 bg-d4e5f6
# bg-d4e5f6 now blocks bg-a1b2c3
```

#### `bodega undep <id> <blocker-id>`

Remove a dependency.

```bash
bodega undep bg-a1b2c3 bg-d4e5f6
```

#### `bodega link <id1> <id2>`

Create a symmetric link between tickets.

```bash
bodega link bg-a1b2c3 bg-d4e5f6
# Both tickets now reference each other in 'links'
```

#### `bodega unlink <id1> <id2>`

Remove a link between tickets.

```bash
bodega unlink bg-a1b2c3 bg-d4e5f6
```

#### `bodega tree [id]`

Display dependency tree.

```bash
bodega tree              # Show all dependency trees
bodega tree bg-a1b2c3    # Show tree for specific ticket
```

**Output:**
```
bg-a1b2c3 [open] Implement auth
├── bg-d4e5f6 [closed] Design auth flow
└── bg-g7h8i9 [open] Set up JWT library
    └── bg-j0k1l2 [closed] Research JWT options
```

#### `bodega cycle`

Detect circular dependencies.

```bash
bodega cycle
```

**Output:**
```
Cycle detected: bg-a1b2c3 -> bg-d4e5f6 -> bg-g7h8i9 -> bg-a1b2c3
```

Or: `No dependency cycles found.`

---

### Migration

#### `bodega migrate-beads`

Import tickets from a beads repository.

```bash
bodega migrate-beads                    # From .beads/issues.jsonl
bodega migrate-beads --path /other/dir  # Custom path
bodega migrate-beads --dry-run          # Preview without writing
```

**Options:**
| Option | Description |
|--------|-------------|
| `--path` | Path to beads directory (default: `.beads`) |
| `--dry-run` | Show what would be imported without writing |
| `--preserve-ids` | Keep original beads IDs instead of generating new ones |

**Field Mapping:**

| Beads Field | Bodega Field |
|-------------|--------------|
| `id` | `id` (with `bg-` prefix unless `--preserve-ids`) |
| `title` | `title` |
| `issue_type` | `type` |
| `status` | `status` |
| `priority` | `priority` |
| `assignee` | `assignee` |
| `external_ref` | `external_ref` |
| `created_at` | `created` |
| `dependencies[type=blocks]` | `deps` |
| `dependencies[type=related]` | `links` |
| `dependencies[type=parent-child]` | `parent` |
| `description` | Description section |
| `design` | Design section |
| `acceptance_criteria` | Acceptance Criteria section |
| `notes` | Notes section |

---

### Utilities

#### `bodega help [command]`

Show help information.

```bash
bodega help
bodega help create
bodega --help
bodega create --help
```

#### `bodega version`

Show version information.

```bash
bodega version
# bodega 0.1.0
```

## Project Structure

```
bodega/
├── pyproject.toml          # Package configuration
├── README.md               # User documentation
├── DESIGN.md               # This file
├── LICENSE                 # MIT license
├── src/
│   └── bodega/
│       ├── __init__.py     # Package init, version
│       ├── cli.py          # Click command definitions
│       ├── commands/       # Command implementations
│       │   ├── __init__.py
│       │   ├── create.py
│       │   ├── lifecycle.py  # start, close, reopen, status
│       │   ├── view.py       # show, edit, note
│       │   ├── list.py       # list, ready, blocked, closed, query
│       │   ├── deps.py       # dep, undep, link, unlink, tree, cycle
│       │   └── migrate.py    # migrate-beads
│       ├── models/
│       │   ├── __init__.py
│       │   └── ticket.py   # Ticket dataclass
│       ├── storage.py      # File I/O, frontmatter parsing
│       ├── config.py       # Configuration loading
│       ├── graph.py        # Dependency graph operations
│       ├── output.py       # Formatting and display
│       └── utils.py        # ID generation, date handling
└── tests/
    ├── __init__.py
    ├── conftest.py         # Pytest fixtures
    ├── test_cli.py         # CLI integration tests
    ├── test_storage.py     # Storage unit tests
    ├── test_graph.py       # Graph algorithm tests
    └── test_migrate.py     # Migration tests
```

## Dependencies

### Required

| Package | Version | Purpose |
|---------|---------|---------|
| `click` | >=8.0 | CLI framework |
| `python-frontmatter` | >=1.0 | Markdown + YAML parsing |
| `pyyaml` | >=6.0 | YAML configuration |

### Development

| Package | Purpose |
|---------|---------|
| `pytest` | Testing framework |
| `pytest-cov` | Coverage reporting |
| `black` | Code formatting |
| `ruff` | Linting |
| `mypy` | Type checking |

## Implementation Notes

### Partial ID Matching

When resolving ticket IDs:
1. If exact match found, use it
2. If input is prefix of exactly one ID, use that ID
3. If multiple matches, error with list of matching IDs
4. If no matches, error with suggestion to check ID

### Dependency Graph

- Use adjacency list representation
- Cycle detection via DFS with coloring (white/gray/black)
- Tree rendering via recursive traversal with prefix tracking

### File Locking

- Use `fcntl.flock()` for advisory locking during writes
- Prevents corruption from concurrent operations
- Lock timeout of 5 seconds with clear error message

### Timestamps

- All timestamps stored in UTC as ISO 8601
- Display in local timezone
- `updated` field auto-updated on any modification

### Error Handling

- Clear, actionable error messages
- Exit codes: 0 = success, 1 = error, 2 = usage error
- No stack traces unless `--debug` flag

## Future Considerations

These features are explicitly out of scope for v1 but may be added later:

- **Templates**: Predefined ticket templates for common types
- **Time tracking**: Start/stop timers for tickets
- **Hooks**: Git-style hooks for ticket events
- **Sync**: Two-way sync with GitHub Issues, Jira, etc.
- **TUI**: Terminal UI for interactive browsing
- **Bulk operations**: Apply changes to multiple tickets
