class WindowConflict(Exception):
    """Same identity with different content or non-monotonic window."""


class PersistenceUnavailable(Exception):
    """No confirmed durable write; retry may be safe with the same identity."""
