"""Tests for dependency graph module."""

import pytest

from bodega.graph import DependencyGraph
from bodega.models.ticket import Ticket, TicketStatus


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def graph_with_simple_deps(storage):
    """
    Create a graph with simple dependencies:
    A depends on B (open)
    C depends on D (closed)
    """
    storage.save(Ticket(
        id="bg-aaa",
        title="Task A",
        deps=["bg-bbb"],
        status=TicketStatus.OPEN,
    ))
    storage.save(Ticket(
        id="bg-bbb",
        title="Task B",
        status=TicketStatus.OPEN,
    ))
    storage.save(Ticket(
        id="bg-ccc",
        title="Task C",
        deps=["bg-ddd"],
        status=TicketStatus.OPEN,
    ))
    storage.save(Ticket(
        id="bg-ddd",
        title="Task D",
        status=TicketStatus.CLOSED,
    ))

    return DependencyGraph(storage)


# ============================================================================
# Basic Initialization Tests
# ============================================================================

def test_graph_initialization_empty(storage):
    """Test initializing graph with no tickets."""
    graph = DependencyGraph(storage)

    assert len(graph._tickets) == 0
    assert len(graph._adjacency) == 0
    assert len(graph._reverse) == 0


def test_graph_initialization_with_tickets(storage):
    """Test that graph builds adjacency lists correctly."""
    storage.save(Ticket(id="bg-aaa", title="A", deps=["bg-bbb"]))
    storage.save(Ticket(id="bg-bbb", title="B"))

    graph = DependencyGraph(storage)

    assert len(graph._tickets) == 2
    assert "bg-bbb" in graph._adjacency["bg-aaa"]
    assert "bg-aaa" in graph._reverse["bg-bbb"]


# ============================================================================
# Blocked/Ready Query Tests
# ============================================================================

def test_is_blocked_with_open_dep(storage):
    """Test that ticket is blocked by open dependency."""
    storage.save(Ticket(id="bg-aaa", title="A", deps=["bg-bbb"], status=TicketStatus.OPEN))
    storage.save(Ticket(id="bg-bbb", title="B", status=TicketStatus.OPEN))

    graph = DependencyGraph(storage)

    assert graph.is_blocked("bg-aaa") is True
    assert graph.is_blocked("bg-bbb") is False


def test_is_blocked_with_closed_dep(storage):
    """Test that ticket is not blocked by closed dependency."""
    storage.save(Ticket(id="bg-aaa", title="A", deps=["bg-bbb"]))
    storage.save(Ticket(id="bg-bbb", title="B", status=TicketStatus.CLOSED))

    graph = DependencyGraph(storage)

    assert graph.is_blocked("bg-aaa") is False


def test_is_blocked_with_multiple_deps(storage):
    """Test blocking with multiple dependencies."""
    storage.save(Ticket(
        id="bg-aaa",
        title="A",
        deps=["bg-bbb", "bg-ccc"],
        status=TicketStatus.OPEN,
    ))
    storage.save(Ticket(id="bg-bbb", title="B", status=TicketStatus.CLOSED))
    storage.save(Ticket(id="bg-ccc", title="C", status=TicketStatus.OPEN))

    graph = DependencyGraph(storage)

    # Should be blocked because bg-ccc is still open
    assert graph.is_blocked("bg-aaa") is True


def test_is_blocked_nonexistent_ticket(storage):
    """Test is_blocked with nonexistent ticket."""
    graph = DependencyGraph(storage)

    assert graph.is_blocked("bg-nonexistent") is False


def test_get_blockers(graph_with_simple_deps):
    """Test getting list of blockers."""
    blockers = graph_with_simple_deps.get_blockers("bg-aaa")

    assert len(blockers) == 1
    assert "bg-bbb" in blockers


def test_get_blockers_multiple(storage):
    """Test getting multiple blockers."""
    storage.save(Ticket(
        id="bg-aaa",
        title="A",
        deps=["bg-bbb", "bg-ccc", "bg-ddd"],
    ))
    storage.save(Ticket(id="bg-bbb", title="B", status=TicketStatus.OPEN))
    storage.save(Ticket(id="bg-ccc", title="C", status=TicketStatus.CLOSED))
    storage.save(Ticket(id="bg-ddd", title="D", status=TicketStatus.OPEN))

    graph = DependencyGraph(storage)
    blockers = graph.get_blockers("bg-aaa")

    assert len(blockers) == 2
    assert "bg-bbb" in blockers
    assert "bg-ddd" in blockers
    assert "bg-ccc" not in blockers  # Closed, so not blocking


def test_get_blockers_nonexistent(storage):
    """Test get_blockers with nonexistent ticket."""
    graph = DependencyGraph(storage)

    assert graph.get_blockers("bg-nonexistent") == []


def test_get_blocked_tickets(graph_with_simple_deps):
    """Test getting all blocked tickets."""
    blocked = graph_with_simple_deps.get_blocked_tickets()

    assert len(blocked) == 1
    assert blocked[0].id == "bg-aaa"


def test_get_ready_tickets(graph_with_simple_deps):
    """Test getting all ready tickets."""
    ready = graph_with_simple_deps.get_ready_tickets()

    # bg-bbb and bg-ccc are ready (bg-ddd is closed, bg-aaa is blocked)
    assert len(ready) == 2
    ready_ids = {t.id for t in ready}
    assert "bg-bbb" in ready_ids
    assert "bg-ccc" in ready_ids


def test_get_ready_tickets_excludes_closed(storage):
    """Test that get_ready_tickets excludes closed tickets."""
    storage.save(Ticket(id="bg-aaa", title="A", status=TicketStatus.CLOSED))
    storage.save(Ticket(id="bg-bbb", title="B", status=TicketStatus.OPEN))

    graph = DependencyGraph(storage)
    ready = graph.get_ready_tickets()

    assert len(ready) == 1
    assert ready[0].id == "bg-bbb"


# ============================================================================
# Cycle Detection Tests
# ============================================================================

def test_find_cycles_no_cycle(graph_with_simple_deps):
    """Test that no cycles are found in acyclic graph."""
    cycles = graph_with_simple_deps.find_cycles()

    assert len(cycles) == 0


def test_find_cycles_simple_cycle(storage):
    """Test detecting a simple 2-node cycle."""
    storage.save(Ticket(id="bg-aaa", title="A", deps=["bg-bbb"]))
    storage.save(Ticket(id="bg-bbb", title="B", deps=["bg-aaa"]))

    graph = DependencyGraph(storage)
    cycles = graph.find_cycles()

    assert len(cycles) > 0
    # Should find at least one cycle involving bg-aaa and bg-bbb
    assert any("bg-aaa" in cycle and "bg-bbb" in cycle for cycle in cycles)


def test_find_cycles_three_node_cycle(storage):
    """Test detecting a 3-node cycle: A -> B -> C -> A."""
    storage.save(Ticket(id="bg-aaa", title="A", deps=["bg-bbb"]))
    storage.save(Ticket(id="bg-bbb", title="B", deps=["bg-ccc"]))
    storage.save(Ticket(id="bg-ccc", title="C", deps=["bg-aaa"]))

    graph = DependencyGraph(storage)
    cycles = graph.find_cycles()

    assert len(cycles) > 0
    # Should detect the cycle
    assert any(
        "bg-aaa" in cycle and "bg-bbb" in cycle and "bg-ccc" in cycle
        for cycle in cycles
    )


def test_has_cycle_true(storage):
    """Test has_cycle returns True when cycle exists."""
    storage.save(Ticket(id="bg-aaa", title="A", deps=["bg-bbb"]))
    storage.save(Ticket(id="bg-bbb", title="B", deps=["bg-aaa"]))

    graph = DependencyGraph(storage)

    assert graph.has_cycle() is True


def test_has_cycle_false(graph_with_simple_deps):
    """Test has_cycle returns False when no cycle exists."""
    assert graph_with_simple_deps.has_cycle() is False


def test_find_cycles_handles_missing_tickets(storage):
    """Test that cycle detection handles missing ticket references."""
    storage.save(Ticket(id="bg-aaa", title="A", deps=["bg-nonexistent"]))

    graph = DependencyGraph(storage)
    cycles = graph.find_cycles()

    # Should not crash, should find no cycles
    assert len(cycles) == 0


# ============================================================================
# Tree Visualization Tests
# ============================================================================

def test_format_tree_simple(storage):
    """Test formatting a simple tree."""
    storage.save(Ticket(id="bg-root", title="Root"))
    storage.save(Ticket(id="bg-child", title="Child", deps=["bg-root"]))

    graph = DependencyGraph(storage)
    tree = graph.format_tree("bg-root")

    assert "bg-root" in tree
    assert "bg-child" in tree
    assert "Root" in tree
    assert "Child" in tree
    # Should have tree connectors
    assert "└──" in tree or "├──" in tree


def test_format_tree_multiple_children(storage):
    """Test formatting tree with multiple children."""
    storage.save(Ticket(id="bg-root", title="Root"))
    storage.save(Ticket(id="bg-child1", title="Child 1", deps=["bg-root"]))
    storage.save(Ticket(id="bg-child2", title="Child 2", deps=["bg-root"]))

    graph = DependencyGraph(storage)
    tree = graph.format_tree("bg-root")

    assert "bg-root" in tree
    assert "bg-child1" in tree
    assert "bg-child2" in tree
    assert "├──" in tree  # Should have branch connector
    assert "└──" in tree  # Should have last child connector


def test_format_tree_nested(storage):
    """Test formatting nested tree."""
    storage.save(Ticket(id="bg-root", title="Root"))
    storage.save(Ticket(id="bg-child", title="Child", deps=["bg-root"]))
    storage.save(Ticket(id="bg-grandchild", title="Grandchild", deps=["bg-child"]))

    graph = DependencyGraph(storage)
    tree = graph.format_tree("bg-root")

    assert "bg-root" in tree
    assert "bg-child" in tree
    assert "bg-grandchild" in tree


def test_format_tree_shows_status(storage):
    """Test that tree shows ticket status."""
    storage.save(Ticket(id="bg-aaa", title="Open", status=TicketStatus.OPEN))
    storage.save(Ticket(id="bg-bbb", title="Closed", status=TicketStatus.CLOSED))

    graph = DependencyGraph(storage)
    tree = graph.format_tree("bg-aaa")

    assert "[open]" in tree


def test_format_tree_missing_ticket(storage):
    """Test formatting tree with missing ticket reference."""
    storage.save(Ticket(id="bg-aaa", title="A", deps=["bg-nonexistent"]))

    graph = DependencyGraph(storage)
    tree = graph.format_tree("bg-nonexistent")

    assert "not found" in tree


def test_format_tree_cycle_detection(storage):
    """Test that tree formatting detects cycles."""
    storage.save(Ticket(id="bg-aaa", title="A", deps=["bg-bbb"]))
    storage.save(Ticket(id="bg-bbb", title="B", deps=["bg-aaa"]))

    graph = DependencyGraph(storage)
    tree = graph.format_tree("bg-aaa")

    assert "(cycle)" in tree


def test_format_tree_all_roots(storage):
    """Test formatting all root tickets."""
    storage.save(Ticket(id="bg-root1", title="Root 1"))
    storage.save(Ticket(id="bg-root2", title="Root 2"))
    storage.save(Ticket(id="bg-child", title="Child", deps=["bg-root1"]))

    graph = DependencyGraph(storage)
    tree = graph.format_tree()  # No root specified

    assert "bg-root1" in tree
    assert "bg-root2" in tree


def test_format_tree_empty_graph(storage):
    """Test formatting tree with no tickets."""
    graph = DependencyGraph(storage)
    tree = graph.format_tree()

    assert tree == ""


# ============================================================================
# Dependency Modification Helper Tests
# ============================================================================

def test_would_create_cycle_simple(storage):
    """Test would_create_cycle with simple case."""
    storage.save(Ticket(id="bg-aaa", title="A", deps=["bg-bbb"]))
    storage.save(Ticket(id="bg-bbb", title="B"))

    graph = DependencyGraph(storage)

    # Adding bg-aaa as dep of bg-bbb would create cycle
    assert graph.would_create_cycle("bg-bbb", "bg-aaa") is True


def test_would_create_cycle_false(storage):
    """Test would_create_cycle when no cycle would be created."""
    storage.save(Ticket(id="bg-aaa", title="A", deps=["bg-bbb"]))
    storage.save(Ticket(id="bg-bbb", title="B"))
    storage.save(Ticket(id="bg-ccc", title="C"))

    graph = DependencyGraph(storage)

    # Adding bg-ccc as dep of bg-aaa would not create cycle
    assert graph.would_create_cycle("bg-aaa", "bg-ccc") is False


def test_would_create_cycle_transitive(storage):
    """Test would_create_cycle with transitive dependencies."""
    storage.save(Ticket(id="bg-aaa", title="A", deps=["bg-bbb"]))
    storage.save(Ticket(id="bg-bbb", title="B", deps=["bg-ccc"]))
    storage.save(Ticket(id="bg-ccc", title="C"))

    graph = DependencyGraph(storage)

    # Adding bg-aaa as dep of bg-ccc would create cycle (A->B->C->A)
    assert graph.would_create_cycle("bg-ccc", "bg-aaa") is True


def test_would_create_cycle_self(storage):
    """Test that adding ticket as its own dep would create cycle."""
    storage.save(Ticket(id="bg-aaa", title="A"))

    graph = DependencyGraph(storage)

    assert graph.would_create_cycle("bg-aaa", "bg-aaa") is True


def test_get_all_blockers_direct(storage):
    """Test getting all blockers with only direct deps."""
    storage.save(Ticket(id="bg-aaa", title="A", deps=["bg-bbb"]))
    storage.save(Ticket(id="bg-bbb", title="B"))

    graph = DependencyGraph(storage)
    blockers = graph.get_all_blockers("bg-aaa")

    assert "bg-bbb" in blockers


def test_get_all_blockers_transitive(storage):
    """Test getting all transitive blockers."""
    storage.save(Ticket(id="bg-aaa", title="A", deps=["bg-bbb"]))
    storage.save(Ticket(id="bg-bbb", title="B", deps=["bg-ccc"]))
    storage.save(Ticket(id="bg-ccc", title="C", deps=["bg-ddd"]))
    storage.save(Ticket(id="bg-ddd", title="D"))

    graph = DependencyGraph(storage)
    blockers = graph.get_all_blockers("bg-aaa")

    # Should get all transitive blockers
    assert "bg-bbb" in blockers
    assert "bg-ccc" in blockers
    assert "bg-ddd" in blockers
    assert len(blockers) == 3


def test_get_all_blockers_none(storage):
    """Test get_all_blockers with no blockers."""
    storage.save(Ticket(id="bg-aaa", title="A"))

    graph = DependencyGraph(storage)
    blockers = graph.get_all_blockers("bg-aaa")

    assert len(blockers) == 0


def test_get_all_blockers_handles_cycles(storage):
    """Test that get_all_blockers handles cycles gracefully."""
    storage.save(Ticket(id="bg-aaa", title="A", deps=["bg-bbb"]))
    storage.save(Ticket(id="bg-bbb", title="B", deps=["bg-aaa"]))

    graph = DependencyGraph(storage)
    blockers = graph.get_all_blockers("bg-aaa")

    # Should not infinite loop, should find both
    assert "bg-bbb" in blockers
    assert "bg-aaa" in blockers


# ============================================================================
# Integration Tests
# ============================================================================

def test_complex_dependency_graph(storage):
    """Test with a more complex dependency graph."""
    # Create a DAG:
    #     A
    #    / \
    #   B   C
    #    \ /
    #     D
    storage.save(Ticket(id="bg-aaa", title="A", deps=["bg-bbb", "bg-ccc"]))
    storage.save(Ticket(id="bg-bbb", title="B", deps=["bg-ddd"]))
    storage.save(Ticket(id="bg-ccc", title="C", deps=["bg-ddd"]))
    storage.save(Ticket(id="bg-ddd", title="D", status=TicketStatus.OPEN))

    graph = DependencyGraph(storage)

    # All are blocked by D
    assert graph.is_blocked("bg-aaa") is True
    assert graph.is_blocked("bg-bbb") is True
    assert graph.is_blocked("bg-ccc") is True
    assert graph.is_blocked("bg-ddd") is False

    # Only D is ready
    ready = graph.get_ready_tickets()
    assert len(ready) == 1
    assert ready[0].id == "bg-ddd"

    # No cycles
    assert graph.has_cycle() is False

    # Tree should show structure
    tree = graph.format_tree("bg-ddd")
    assert "bg-ddd" in tree
    assert "bg-bbb" in tree
    assert "bg-ccc" in tree
