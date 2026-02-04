---
created: '2026-02-04T14:34:51.484995+00:00'
id: bg-dd63e2
parent: bg-92325e
priority: 2
status: open
tags:
- offline
- documentation
title: Document offline mode in README and docs
type: task
updated: '2026-02-04T14:34:51.485100+00:00'
---

## Description

Add comprehensive offline mode documentation:

## Files to update
1. **README.md**: Add offline mode section
2. **AGENTS.md**: Update with offline mode patterns
3. Create **docs/offline-mode.md** (if docs/ exists)

## Documentation sections
### Quick Start
```bash
# Initialize offline mode
bodega init --offline

# Use normally
bodega create "Personal task"
bodega list

# Later, migrate to local
cd /path/to/repo
bodega init
bodega migrate --from-offline
```

### Use Cases
- Personal task tracking without committing to repo
- Working across multiple clones
- Prototyping workflow before team adoption

### Architecture
- Storage location: ~/.bodega/<project-hash>/
- Precedence: local > offline
- No git integration in offline mode

### Commands
- `bodega init --offline [--name NAME]`
- `bodega offline list`
- `bodega migrate --from-offline`

### FAQ
- Q: Can I use worktree mode with offline?
  A: No, offline mode is file-based only
- Q: What happens if I have both local and offline stores?
  A: Local always takes precedence
- Q: How do I share offline tickets?
  A: Migrate to local repo first

## Code examples
Include examples in docstrings and help text