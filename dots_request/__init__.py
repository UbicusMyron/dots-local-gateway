"""Shared dots request client with an injected, explicitly configured transport."""
from .client import Client, RequestError, Transport

__all__ = ["Client", "RequestError", "Transport"]
