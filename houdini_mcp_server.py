#!/usr/bin/env python
"""Backward-compatible launcher for the packaged MCP bridge implementation."""

import sys

from houdini_mcp_bridge import bridge as _implementation


if __name__ == "__main__":
    _implementation.main()
else:
    # Preserve historical imports, including callers that set bridge test
    # globals such as ``_houdini_port`` before opening a connection.
    sys.modules[__name__] = _implementation
