"""Graph module for dependency management."""

from typing import Optional
from collections import defaultdict

from bodega.models.ticket import Ticket, TicketStatus
from bodega.storage import TicketStorage


# ============================================================================
# Dependency Graph
# ============================================================================

class DependencyGraph:
    """
    Manages dependency relationships between tickets.

    deps relationship: A depends on B means B blocks A
    - A.deps = [B] means A is blocked until B is closed
    """

    def __init__(self, storage: TicketStorage):
        """
        Initialize the dependency graph.

        Args:
            storage: The ticket storage to load tickets from
        """
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

    # ========================================================================
    # Blocked/Ready Queries
    # ========================================================================

    def is_blocked(self, ticket_id: str) -> bool:
        """
        Check if a ticket is blocked by unresolved dependencies.

        A ticket is blocked if any of its deps are not closed.

        Args:
            ticket_id: The ticket ID to check

        Returns:
            True if the ticket is blocked
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
        """
        Get list of open tickets blocking this one.

        Args:
            ticket_id: The ticket ID to check

        Returns:
            List of ticket IDs that are blocking this ticket
        """
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
        """
        Get all open tickets that are blocked.

        Returns:
            List of tickets that are blocked
        """
        blocked = []
        for ticket in self._tickets.values():
            if ticket.status == TicketStatus.CLOSED:
                continue
            if self.is_blocked(ticket.id):
                blocked.append(ticket)
        return blocked

    def get_ready_tickets(self) -> list[Ticket]:
        """
        Get all open tickets that are ready to work on (not blocked).

        Returns:
            List of tickets that are ready to work on
        """
        ready = []
        for ticket in self._tickets.values():
            if ticket.status == TicketStatus.CLOSED:
                continue
            if not self.is_blocked(ticket.id):
                ready.append(ticket)
        return ready

    # ========================================================================
    # Cycle Detection
    # ========================================================================

    def find_cycles(self) -> list[list[str]]:
        """
        Find all dependency cycles using DFS.

        Returns:
            List of cycles, where each cycle is a list of ticket IDs
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
        """
        Check if any dependency cycle exists.

        Returns:
            True if at least one cycle exists
        """
        return len(self.find_cycles()) > 0

    # ========================================================================
    # Tree Visualization
    # ========================================================================

    def format_tree(self, root_id: Optional[str] = None) -> str:
        """
        Format dependency tree as ASCII art.

        Example:
            bg-a1b2c3 [open] Implement auth
            ├── bg-d4e5f6 [closed] Design auth flow
            └── bg-g7h8i9 [open] Set up JWT library
                └── bg-j0k1l2 [closed] Research JWT options

        If root_id is None, shows all root tickets (those with no dependencies).

        Args:
            root_id: Optional root ticket ID. If None, shows all roots.

        Returns:
            ASCII tree representation
        """
        if root_id:
            return self._format_subtree(root_id, "", True)

        # Find all roots (tickets that have no dependencies themselves)
        roots = [tid for tid in self._tickets if len(self._adjacency.get(tid, set())) == 0]

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
        """
        Recursively format a subtree.

        Args:
            ticket_id: The current ticket ID
            prefix: The prefix string for indentation
            is_last: Whether this is the last child
            visited: Set of already visited ticket IDs (for cycle detection)

        Returns:
            Formatted subtree string
        """
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

    # ========================================================================
    # Dependency Modification Helpers
    # ========================================================================

    def would_create_cycle(self, ticket_id: str, new_dep_id: str) -> bool:
        """
        Check if adding new_dep_id to ticket_id's deps would create a cycle.

        This checks if new_dep_id depends (directly or transitively) on ticket_id.

        Args:
            ticket_id: The ticket that would get a new dependency
            new_dep_id: The proposed new dependency

        Returns:
            True if adding the dependency would create a cycle
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
        """
        Get all transitive blockers (not just direct deps).

        Args:
            ticket_id: The ticket ID to check

        Returns:
            List of all tickets that transitively block this one
        """
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
