"""Exception classes for bodega."""


# ============================================================================
# Base Exceptions
# ============================================================================

class BodegaError(Exception):
    """Base exception for all bodega errors."""
    pass


# ============================================================================
# Storage Exceptions
# ============================================================================

class StorageError(BodegaError):
    """Base exception for storage errors."""
    pass


class TicketNotFoundError(StorageError):
    """Ticket does not exist."""
    pass


class TicketExistsError(StorageError):
    """Ticket already exists."""
    pass


# ============================================================================
# ID Resolution Exceptions
# ============================================================================

class IDResolutionError(BodegaError):
    """Base exception for ID resolution errors."""
    pass


class AmbiguousIDError(IDResolutionError):
    """Multiple tickets match the partial ID."""
    pass
