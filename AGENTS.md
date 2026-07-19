# AGENTS.md

## Scope

These instructions apply to the entire repository. This repository is a fork of
`capoomgit/houdini-mcp` and is intentionally kept easy to deploy for upstream
users.

## Project architecture

Keep the existing two-process design:

1. `houdini_mcp_server.py` is the FastMCP bridge. It runs outside Houdini,
   exposes MCP tools over stdio, validates requests, and relays commands over
   TCP.
2. `server.py` runs inside Houdini, listens on `127.0.0.1:9876`, dispatches JSON
   commands on Houdini's main thread, and performs the actual `hou` operations.
3. `houdini_catalog.py` declares typed catalog capabilities and their metadata.
4. `tool_registry.py` owns discovery, schema generation, availability checks,
   risk gates, validation, and dispatch.
5. `sidefx_docs.py` discovers and searches the official documentation bundled
   with the active Houdini installation.

The default tool mode is `hybrid`: keep the compact direct MCP surface and make
less-common capabilities available through `search_tools`, `get_tool_schema`,
and `call_tool`. `HOUDINI_MCP_TOOL_MODE=legacy` must continue to expose the
expanded compatibility surface.

## Compatibility invariants

Do not change these without an explicit user request:

- The repository/package deployment layout.
- The `uv run` MCP launch workflow.
- MCP stdio transport.
- The Shelf Tool start/stop workflow.
- The default Houdini TCP endpoint, `127.0.0.1:9876`.
- The length-prefixed JSON TCP protocol and existing command names.
- Existing Codex, Claude Desktop, or Houdini package registration procedures.

Avoid large rewrites of upstream files when a focused extension is sufficient.
Keep Windows, macOS, and Linux support.

## Adding or changing a capability

For a normal catalog capability:

1. Add or update a strict Pydantic argument model in `houdini_catalog.py`.
2. Register a `ToolSpec` with category, description, keywords, mutation flag,
   Undo support, risk level, availability, examples when useful, and at least
   one valid SideFX `DocRef`.
3. Implement the Houdini-side handler in `server.py` using live `hou` data.
4. Add the command to the dispatcher in `server.py`.
5. Add mutating commands to `MUTATING_COMMANDS` so one agent action maps to one
   Houdini Undo step whenever the operation supports Undo.
6. Add a direct `@mcp.tool()` wrapper only for a genuinely high-frequency
   operation. Prefer catalog discovery and `call_tool` for other capabilities.
7. Add unit tests and, when the handler touches `hou`, headless integration
   coverage.

Do not duplicate complete node-type or parameter lists in source. Validate node
types through the connected session's `hou.nodeTypeCategories()` and derive
parameter definitions from live `hou.ParmTemplate` objects. Return useful
category/type/parameter suggestions when validation fails.

## SideFX documentation rules

Every registered capability must cite relevant official SideFX documentation.
The local documentation shipped with the connected Houdini version is the
execution authority; public SideFX URLs are traceability links and may point to
the current online version.

- Never hardcode usernames, drive letters, full Houdini install paths, or
  complete version directories.
- Preserve discovery priority: `HOUDINI_MCP_DOC_ROOT`, connected Houdini
  `HFS`/`HH`, inherited environment, platform discovery, degraded mode.
- Read `hom.zip` and `nodes.zip` in place with the standard library. Do not
  extract or commit SideFX documentation.
- Store portable archive/entry references, not machine-specific absolute paths.
- Runtime execution must continue when local documentation is unavailable.
- Do not add a runtime network dependency for documentation search.

## Safety and response contracts

- Reject unexpected arguments before sending TCP commands.
- Keep high-risk catalog calls behind `allow_unsafe=true`.
- Treat arbitrary Houdini Python as a last-resort escape hatch, not the default
  implementation for repeatable operations.
- Prefer live capability checks and clear error messages over silent fallback.
- Preserve the response envelopes:

  - Success: `{"status": "success", "result": ...}`
  - Error: `{"status": "error", "message": "...", "origin": "..."}`

- HIP saving must not overwrite an existing target unless the caller explicitly
  opts in.
- Do not expose secrets or commit `urls.env`; OPUS remains optional and must
  report why it is unavailable when credentials are absent.

## Tests

Run focused tests while iterating, then the relevant full suite before a major
commit.

Bridge-only unit tests:

```powershell
uv run python -m unittest -v tests/test_registry_unit.py tests/test_sidefx_docs.py tests/test_hybrid_surface.py
```

Houdini integration tests require two terminals and the `hython` executable
from the Houdini version being tested. Do not encode its machine-specific path
in repository files.

```powershell
# Terminal 1
hython tests/headless_host.py 19878

# Terminal 2
uv run python tests/test_tools.py 19878
uv run python tests/test_catalog_tools.py 19878
```

At minimum, test argument validation, risk gates, Hybrid/Legacy exposure,
DocRefs, portable help discovery, degraded behavior, live node context,
parameter failures, Undo-eligible mutations, and HIP overwrite protection when
those areas are changed.

## Git workflow

- Preserve unrelated user changes and inspect `git status` before editing.
- Work on the current feature branch unless the user requests another branch.
- Make one focused commit for each substantial architectural or feature change.
- Use conventional commit subjects such as `feat:`, `fix:`, `refactor:`,
  `test:`, and `docs:`.
- Run the relevant tests before each substantial commit.
- Do not merge, rebase, push, publish, or change remotes unless the user
  explicitly requests it.
- Finish with a clean worktree when the requested work is fully committed.

## Completion report

Report the user-visible capability change, tests run and their results, commit
hashes created, any unavailable optional integration, and whether Houdini must
restart its Shelf MCP server to load modified plugin code.
