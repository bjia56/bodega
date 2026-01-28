# Bodega Implementation Tasks

This directory contains implementation tasks for the bodega CLI tool. Each task is a self-contained unit of work with clear requirements and acceptance criteria.

## Task Execution Order

Tasks should be implemented in the following order based on dependencies:

```
Phase 1: Foundation
├── 01-project-setup.md      (no deps)
├── 02-models.md             (depends on 01)
├── 03-utils.md              (depends on 01)
└── 04-config.md             (depends on 01, 03)

Phase 2: Core Infrastructure
├── 05-storage.md            (depends on 01, 02, 03, 04)
├── 06-output.md             (depends on 01, 02, 04)
└── 07-graph.md              (depends on 01, 02, 05)

Phase 3: CLI Framework
└── 08-cli-base.md           (depends on 01, 04, 05)

Phase 4: Commands (can be parallelized after Phase 3)
├── 09-cmd-init.md           (depends on 04, 05, 08)
├── 10-cmd-create.md         (depends on 02, 03, 05, 08)
├── 11-cmd-lifecycle.md      (depends on 02, 05, 08)
├── 12-cmd-view.md           (depends on 02, 05, 06, 08)
├── 13-cmd-list.md           (depends on 02, 05, 06, 07, 08)
├── 14-cmd-deps.md           (depends on 02, 05, 07, 08)
└── 15-cmd-migrate.md        (depends on 02, 03, 05, 08)
```

## Dependency Graph

```
01 ─┬─► 02 ─┬─► 05 ─┬─► 07 ─┬─► 13, 14
    │       │       │       │
    ├─► 03 ─┼───────┤       │
    │       │       │       │
    └─► 04 ─┴───────┴─► 08 ─┼─► 09, 10, 11, 12, 15
                            │
                      06 ───┴─► 12, 13
```

## Recommended Implementation Order

1. **01-project-setup.md** - Set up pyproject.toml and package structure
2. **02-models.md** - Implement Ticket dataclass
3. **03-utils.md** - Implement utility functions
4. **04-config.md** - Implement configuration system
5. **05-storage.md** - Implement file storage layer
6. **16-test-fixtures.md** - Implement shared test fixtures (enables testing)
7. **06-output.md** - Implement output formatting
8. **07-graph.md** - Implement dependency graph operations
9. **08-cli-base.md** - Set up Click CLI structure
10. **09-cmd-init.md** - Implement init command
11. **10-cmd-create.md** - Implement create command
12. **11-cmd-lifecycle.md** - Implement start/close/reopen/status
13. **12-cmd-view.md** - Implement show/edit/note
14. **13-cmd-list.md** - Implement list/ready/blocked/closed/query
15. **14-cmd-deps.md** - Implement dep/undep/link/unlink/tree/cycle
16. **15-cmd-migrate.md** - Implement migrate-beads

## Task File Structure

Each task file contains:

- **Summary**: Brief description of the task
- **Dependencies**: List of prerequisite tasks
- **Requirements**: Detailed implementation requirements with code examples
- **Acceptance Criteria**: Checklist of requirements
- **Test Cases**: Example pytest tests

## Testing Strategy

After implementing each task:

1. Run `pip install -e .` to install the package
2. Run `pytest` to execute tests
3. Manually test the implemented functionality

## Quick Reference

| Task | Component | Commands/Features |
|------|-----------|-------------------|
| 01 | Project | pyproject.toml, package structure |
| 02 | Models | Ticket dataclass, TicketType, TicketStatus |
| 03 | Utils | ID generation, date handling, git utils |
| 04 | Config | BodegaConfig, load_config, env vars |
| 05 | Storage | TicketStorage, read/write, query |
| 06 | Output | format_table, format_json, colors |
| 07 | Graph | DependencyGraph, cycles, tree |
| 08 | CLI | Click setup, context, error handling |
| 09 | Command | `bodega init` |
| 10 | Command | `bodega create` |
| 11 | Command | `bodega start/close/reopen/status` |
| 12 | Command | `bodega show/edit/note` |
| 13 | Command | `bodega list/ready/blocked/closed/query` |
| 14 | Command | `bodega dep/undep/link/unlink/tree/cycle` |
| 15 | Command | `bodega migrate-beads` |
