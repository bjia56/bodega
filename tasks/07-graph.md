# Task 07: Dependency Graph Operations

## Summary
Implement dependency graph algorithms for cycle detection, tree visualization, and blocked/ready queries.

## Dependencies
- Task 01: Project Setup
- Task 02: Models (Ticket class)
- Task 05: Storage (TicketStorage)

## Requirements

### 1. Graph Module (`src/bodega/graph.py`)

```python
from typing import Optional
from collections import defaultdict

from .models import Ticket, TicketStatus
from .storage import TicketStorage

class DependencyGraph:
    """
    Manages dependency relationships between tickets.

    deps relationship: A depends on B means B blocks A
    - A.deps = [B] means A is blocked until B is closed
    """

    def __init__(self, storage: TicketStorage):
        self.storage = storage
        self._adjacency: dict[str, set[str]] = defaultdict(set)  # id -> blockers
        self._reverse: dict[str, set[str]] = defaultdict(set)    # id -> blocked by this
        self._tickets: dict[str, Ticket] = {}
        self._build_graph()

    def _build_graph(self) -> None:
        """Build adjacency lists from all tickets."""
        for ticket in self.storage.list_all():
            self._tickets[ticket.id] = ticket
            for dep_id in ticket.deps:
                self._adjacency[ticket.id].add(dep_id)
                self._reverse[dep_id].add(ticket.id)
```

### 2. Blocked/Ready Queries

```python
def is_blocked(self, ticket_id: str) -> bool:
    """
    Check if a ticket is blocked by unresolved dependencies.

    A ticket is blocked if any of its deps are not closed.
    """
    ticket = self._tickets.get(ticket_id)
    if not ticket:
        return False

    for dep_id in ticket.deps:
        dep = self._tickets.get(dep_id)
        if dep and dep.status != TicketStatus.CLOSED:
            return True
    return False

def get_blockers(self, ticket_id: str) -> list[str]:
    """Get list of open tickets blocking this one."""
    ticket = self._tickets.get(ticket_id)
    if not ticket:
        return []

    blockers = []
    for dep_id in ticket.deps:
        dep = self._tickets.get(dep_id)
        if dep and dep.status != TicketStatus.CLOSED:
            blockers.append(dep_id)
    return blockers

def get_blocked_tickets(self) -> list[Ticket]:
    """Get all open tickets that are blocked."""
    blocked = []
    for ticket in self._tickets.values():
        if ticket.status == TicketStatus.CLOSED:
            continue
        if self.is_blocked(ticket.id):
            blocked.append(ticket)
    return blocked

def get_ready_tickets(self) -> list[Ticket]:
    """Get all open tickets that are ready to work on (not blocked)."""
    ready = []
    for ticket in self._tickets.values():
        if ticket.status == TicketStatus.CLOSED:
            continue
        if not self.is_blocked(ticket.id):
            ready.append(ticket)
    return ready
```

### 3. Cycle Detection

```python
def find_cycles(self) -> list[list[str]]:
    """
    Find all dependency cycles using DFS.

    Returns list of cycles, where each cycle is a list of ticket IDs.
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {tid: WHITE for tid in self._tickets}
    cycles = []

    def dfs(node: str, path: list[str]) -> None:
        color[node] = GRAY
        path.append(node)

        for neighbor in self._adjacency.get(node, []):
            if neighbor not in color:
                continue  # Skip missing tickets

            if color[neighbor] == GRAY:
                # Found cycle - extract it from path
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                cycles.append(cycle)
            elif color[neighbor] == WHITE:
                dfs(neighbor, path)

        path.pop()
        color[node] = BLACK

    for ticket_id in self._tickets:
        if color[ticket_id] == WHITE:
            dfs(ticket_id, [])

    return cycles

def has_cycle(self) -> bool:
    """Check if any dependency cycle exists."""
    return len(self.find_cycles()) > 0
```

### 4. Tree Visualization

```python
def format_tree(self, root_id: Optional[str] = None) -> str:
    """
    Format dependency tree as ASCII art.

    bg-a1b2c3 [open] Implement auth
    ├── bg-d4e5f6 [closed] Design auth flow
    └── bg-g7h8i9 [open] Set up JWT library
        └── bg-j0k1l2 [closed] Research JWT options

    If root_id is None, shows all root tickets (those not blocked by others).
    """
    if root_id:
        return self._format_subtree(root_id, "", True)

    # Find all roots (tickets that don't appear in anyone's deps)
    all_deps = set()
    for ticket in self._tickets.values():
        all_deps.update(ticket.deps)

    roots = [tid for tid in self._tickets if tid not in all_deps]

    if not roots:
        # All tickets have dependencies, pick any as starting points
        # or there might be cycles
        roots = list(self._tickets.keys())[:5]  # Limit to avoid huge output

    lines = []
    for root in sorted(roots):
        lines.append(self._format_subtree(root, "", True))

    return "\n".join(lines)

def _format_subtree(
    self,
    ticket_id: str,
    prefix: str,
    is_last: bool,
    visited: Optional[set] = None
) -> str:
    """Recursively format a subtree."""
    if visited is None:
        visited = set()

    ticket = self._tickets.get(ticket_id)
    if not ticket:
        return f"{prefix}{'└── ' if is_last else '├── '}{ticket_id} (not found)"

    # Detect cycles
    if ticket_id in visited:
        return f"{prefix}{'└── ' if is_last else '├── '}{ticket_id} (cycle)"

    visited = visited | {ticket_id}

    # Format this node
    connector = "└── " if is_last else "├── "
    status_str = f"[{ticket.status.value}]"
    node_line = f"{prefix}{connector}{ticket_id} {status_str} {ticket.title}"

    # Get children (tickets blocked by this one)
    children = sorted(self._reverse.get(ticket_id, []))

    if not children:
        return node_line

    lines = [node_line]
    child_prefix = prefix + ("    " if is_last else "│   ")

    for i, child_id in enumerate(children):
        is_child_last = (i == len(children) - 1)
        lines.append(self._format_subtree(child_id, child_prefix, is_child_last, visited))

    return "\n".join(lines)
```

### 5. Dependency Modification Helpers

```python
def would_create_cycle(self, ticket_id: str, new_dep_id: str) -> bool:
    """
    Check if adding new_dep_id to ticket_id's deps would create a cycle.

    This checks if new_dep_id depends (directly or transitively) on ticket_id.
    """
    # If ticket_id is reachable from new_dep_id, adding the dep creates a cycle
    visited = set()
    stack = [new_dep_id]

    while stack:
        current = stack.pop()
        if current == ticket_id:
            return True
        if current in visited:
            continue
        visited.add(current)

        # Add dependencies of current to stack
        current_ticket = self._tickets.get(current)
        if current_ticket:
            stack.extend(current_ticket.deps)

    return False

def get_all_blockers(self, ticket_id: str) -> list[str]:
    """Get all transitive blockers (not just direct deps)."""
    visited = set()
    stack = list(self._adjacency.get(ticket_id, []))
    result = []

    while stack:
        current = stack.pop()
        if current in visited:
            continue
        visited.add(current)
        result.append(current)
        stack.extend(self._adjacency.get(current, []))

    return result
```

## Acceptance Criteria

- [ ] `is_blocked()` correctly identifies blocked tickets
- [ ] `get_ready_tickets()` returns only unblocked open tickets
- [ ] `find_cycles()` detects all cycles in the graph
- [ ] `format_tree()` produces readable ASCII tree
- [ ] `would_create_cycle()` prevents cycle creation
- [ ] Handles missing ticket references gracefully
- [ ] Works with empty ticket sets

## Test Cases

```python
def test_is_blocked(storage_fixture):
    # Create tickets: A depends on B (open)
    storage_fixture.create(Ticket(id="bg-aaa", title="A", deps=["bg-bbb"]))
    storage_fixture.create(Ticket(id="bg-bbb", title="B", status=TicketStatus.OPEN))

    graph = DependencyGraph(storage_fixture)
    assert graph.is_blocked("bg-aaa") is True
    assert graph.is_blocked("bg-bbb") is False

def test_is_blocked_closed_dep(storage_fixture):
    # A depends on B (closed) - not blocked
    storage_fixture.create(Ticket(id="bg-aaa", title="A", deps=["bg-bbb"]))
    storage_fixture.create(Ticket(id="bg-bbb", title="B", status=TicketStatus.CLOSED))

    graph = DependencyGraph(storage_fixture)
    assert graph.is_blocked("bg-aaa") is False

def test_find_cycles(storage_fixture):
    # A -> B -> C -> A (cycle)
    storage_fixture.create(Ticket(id="bg-aaa", title="A", deps=["bg-bbb"]))
    storage_fixture.create(Ticket(id="bg-bbb", title="B", deps=["bg-ccc"]))
    storage_fixture.create(Ticket(id="bg-ccc", title="C", deps=["bg-aaa"]))

    graph = DependencyGraph(storage_fixture)
    cycles = graph.find_cycles()
    assert len(cycles) > 0

def test_would_create_cycle(storage_fixture):
    # A -> B, check if B -> A would create cycle
    storage_fixture.create(Ticket(id="bg-aaa", title="A", deps=["bg-bbb"]))
    storage_fixture.create(Ticket(id="bg-bbb", title="B"))

    graph = DependencyGraph(storage_fixture)
    assert graph.would_create_cycle("bg-bbb", "bg-aaa") is True
    assert graph.would_create_cycle("bg-aaa", "bg-ccc") is False

def test_format_tree(storage_fixture):
    storage_fixture.create(Ticket(id="bg-root", title="Root"))
    storage_fixture.create(Ticket(id="bg-child", title="Child", deps=["bg-root"]))

    graph = DependencyGraph(storage_fixture)
    tree = graph.format_tree("bg-root")
    assert "bg-root" in tree
    assert "bg-child" in tree
    assert "└──" in tree or "├──" in tree
```
