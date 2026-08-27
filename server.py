"""Compatibility import for existing ``houdinimcp.server`` integrations."""

try:
    from .houdinimcp_runtime.server import HoudiniMCPServer
except ImportError:  # Preserve historical direct module loading in Houdini.
    from houdinimcp_runtime.server import HoudiniMCPServer

__all__ = ["HoudiniMCPServer"]
