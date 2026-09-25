"""Connect to DaVinci Resolve 21 through its Python scripting API."""

from .connection import REQUIRED_MAJOR_VERSION, ResolveConnectionError, connect

__all__ = ["REQUIRED_MAJOR_VERSION", "ResolveConnectionError", "connect"]
