---
created: '2026-02-04T14:34:44.951938+00:00'
deps:
- bg-c4be4d
id: bg-c22fda
parent: bg-92325e
priority: 3
status: open
tags:
- offline
- migration
- enhancement
title: Implement offline to local migration
type: feature
updated: '2026-02-04T14:35:04.863149+00:00'
---

## Description

Add command to migrate tickets from offline store to local .bodega/:

## Command
```bash
bodega migrate --from-offline [--preserve]
```

## Behavior
- Check current directory has offline store
- Check if local .bodega/ exists
  - If not: Run `bodega init` first
  - If exists: Confirm merge/overwrite
- Copy all tickets from ~/.bodega/<project>/ to ./.bodega/
- Handle ID conflicts (error or skip)
- Options:
  - `--preserve`: Keep offline store after migration
  - Default: Remove offline store after successful migration

## Implementation
Create src/bodega/commands/migrate.py:
```python
@click.command()
@click.option("--from-offline", is_flag=True)
@click.option("--preserve", is_flag=True)
def migrate(from_offline, preserve):
    """Migrate tickets between stores"""
    # Implementation
```

## Edge cases
- ID conflicts between stores
- Partial migration failures
- Git commit during migration (if worktree mode)

## Future: bidirectional sync
This is foundation for future --to-offline and sync commands