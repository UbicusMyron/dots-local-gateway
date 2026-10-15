"""Transport-independent, read-only gateway core (experimental internal API)."""

from .core import Gateway, ConfigurationError

__all__ = ["Gateway", "ConfigurationError"]
