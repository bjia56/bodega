---
created: '2026-02-04T14:33:58.328448+00:00'
deps:
- bg-0f30d1
- bg-e20ced
id: bg-c4be4d
parent: bg-92325e
priority: 1
status: open
tags:
- offline
- storage
title: Update TicketStorage to detect and handle offline mode
type: task
updated: '2026-02-04T14:33:58.328766+00:00'
---

## Description

Update src/bodega/storage.py to properly handle offline mode:

## Changes to TicketStorage.__init__() (lines 56-82)
After line 69:
```python
# Check if using offline mode
if self.config.offline_mode:
    # Offline mode - use ~/.bodega/<project>/ store
    self.tickets_dir = self.config.bodega_dir
    self.worktree_path = None
    self.use_worktree = False
    self.is_offline = True
elif self.config.git_branch:
    # Worktree mode - use separate branch
    # ... existing code ...
    self.is_offline = False
else:
    # Direct mode - store in .bodega/ on current branch
    # ... existing code ...
    self.is_offline = False
```

## Add is_offline field
- Add to __init__ signature or as instance variable
- Used to disable git operations in offline mode

## Disable git auto-commit for offline mode
Lines 165-171 and 208-216:
- Add check: `if self.use_worktree and not self.is_offline and self.config.git_auto_commit:`

## Optional: Add indicator
Consider showing "(offline)" in output when using offline store