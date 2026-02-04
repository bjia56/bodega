---
created: '2026-02-04T14:34:44.983008+00:00'
deps:
- bg-c22fda
id: bg-7ce5ec
parent: bg-92325e
priority: 4
status: open
tags:
- offline
- sync
- enhancement
- future
title: Add offline store sync capabilities
type: feature
updated: '2026-02-04T14:35:04.870631+00:00'
---

## Description

Implement bidirectional sync between offline and local stores:

## Command
```bash
bodega sync [--strategy=merge|offline-wins|local-wins]
```

## Sync strategy
- **merge**: Combine tickets, resolve conflicts by timestamp
- **offline-wins**: Offline tickets take precedence
- **local-wins**: Local tickets take precedence

## Conflict detection
- Same ticket ID exists in both stores
- Compare updated timestamps
- Show diff and prompt for resolution

## Implementation considerations
- Use ticket.updated field for conflict resolution
- Consider three-way merge based on common ancestor
- Handle deleted tickets (tombstones?)
- Atomic operation - rollback on failure

## Future enhancements
- Auto-sync on commands (opt-in)
- Sync history/log
- Remote sync (beyond scope of initial offline mode)

## Dependencies
Requires stable offline mode and migration commands first