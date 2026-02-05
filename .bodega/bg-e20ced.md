---
assignee: Brett Jia
created: '2026-02-04T14:33:15.399886+00:00'
deps:
- bg-92325e
- bg-23b639
id: bg-e20ced
parent: bg-92325e
priority: 1
status: closed
tags:
- offline
- utils
title: Add offline store discovery to find_bodega_dir()
type: task
updated: '2026-02-05T14:17:09.057087+00:00'
---

## Description

Update find_bodega_dir() in src/bodega/utils.py to support offline store fallback:

## Changes needed
1. Add `find_offline_store(project_path: Path) -> Optional[Path]`:
   - Get project identifier using get_project_identifier()
   - Check if ~/.bodega/<identifier>/.bodega/ exists
   - Return path if found, None otherwise

2. Update `find_bodega_dir()`:
   - Keep existing logic to search up for .bodega/ (lines 257-271)
   - If not found, call find_offline_store(Path.cwd())
   - Return offline store path if found
   - Return None only if both local and offline not found

## Testing considerations
- Test local .bodega/ takes precedence
- Test offline fallback works
- Test None returned when neither exists