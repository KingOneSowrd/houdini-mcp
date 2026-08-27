# HoudiniMCP – Connect Houdini to Claude via Model Context Protocol

**HoudiniMCP** allows you to control **SideFX Houdini** from **Claude** using the **Model Context Protocol (MCP)**. It consists of:

1. A **Houdini plugin** (Python package) that listens on a local port (default `localhost:9900`, configurable with `HOUDINI_MCP_PORT`) and handles commands (creating and modifying nodes, executing code, etc.).
2. An **MCP bridge script** you run via **uv** (or system Python) that communicates via **std**in/**std**out with Claude and **TCP** with Houdini.

## Project structure

Compatibility entry points intentionally remain at the repository root so the
existing Houdini package, Shelf Tool, imports, and `uv run` workflows keep
working. Runtime implementation lives in focused subpackages.

```text
houdini-mcp/
├── houdini_mcp_server.py       # Backward-compatible MCP launcher
├── server.py                   # Backward-compatible Houdini server import
├── __init__.py                 # Houdini package start/stop lifecycle
├── houdini_mcp_bridge/         # Runs outside Houdini
│   ├── bridge.py               # FastMCP stdio bridge and direct tools
│   ├── catalog.py              # Typed catalog capability declarations
│   ├── registry.py             # Discovery, validation, risk, and dispatch
│   └── sidefx_docs.py          # Installed SideFX docs provider
├── houdinimcp_runtime/         # Runs inside Houdini
│   ├── server.py               # TCP server, dispatcher, and HOM handlers
│   └── render.py               # Viewport/render helper routines
├── scripts/
│   └── shelf/
│       ├── start_server.py     # Shelf Tool example: start server
│       └── stop_server.py      # Shelf Tool example: stop server
├── skills/
│   └── houdini-production-workflows/
│       ├── SKILL.md            # Production routing and execution policy
│       ├── references/         # Contracts, workflows, cases, and records
│       └── scripts/            # Case ingestion and experience validation
├── tests/
│   ├── headless_host.py        # hython integration-test host
│   ├── test_tools.py           # Original/live Houdini capability tests
│   ├── test_catalog_tools.py   # Catalog, material, USD, and HIP tests
│   ├── test_expansion_tools.py # Graph Patch and HDA integration tests
│   ├── test_registry_unit.py   # Registry and safety unit tests
│   ├── test_hybrid_surface.py  # Hybrid/Legacy MCP exposure tests
│   ├── test_sidefx_docs.py     # Portable SideFX help discovery tests
│   └── test_experience_system.py # Skill records and lifecycle tests
├── CAPABILITY_TODO.md          # Prioritized capability and workflow backlog
├── AGENTS.md                   # Repository development constraints
├── urls.env.example            # Optional OPUS configuration template
├── pyproject.toml              # Python project metadata and dependencies
├── uv.lock                     # Reproducible dependency lock
├── .python-version             # Preferred Python version
├── .gitignore
├── LICENSE
└── README.md
```

Local generated directories such as `.venv/`, `__pycache__/`, and uv caches
are not part of the source layout and must remain untracked.

## Production workflow skill

The repository includes a source-controlled
`houdini-production-workflows` skill that turns the MCP execution layer into a
case-driven production system. It keeps routing and safety rules in a compact
entry point, loads domain workflows only when relevant, and stores cases,
recipes, execution experiences, and future template manifests as strict,
versioned records.

The initial knowledge set contains five bounded Project Titan evidence records
and eight candidate workflow recipes covering curve instancing, surface growth,
modular generation, Vellum settle, RBD destruction, Pyro flipbooks, real-time
animation/VAT, and Pivot Painter. Candidate status is intentional: inspecting a
successful tutorial does not prove production acceptance in every project.

Useful maintenance commands:

```powershell
python skills/houdini-production-workflows/scripts/experience_cli.py validate
python skills/houdini-production-workflows/scripts/experience_cli.py assess
python skills/houdini-production-workflows/scripts/experience_cli.py reindex

# Run with the active Houdini installation's hython executable.
hython skills/houdini-production-workflows/scripts/inspect_houdini_case.py `<case.hip-or-hda>` --source-root `<portable-root>` --output `<candidate.json>`
```

The Hython inspector uses manual update mode and does not save, cache, render,
or export. Its output is always a candidate case with acceptance left false.
Review and validate evidence before promoting any record. Binary HIP/HDA
templates will be added only when a real recipe has a safe, reusable skeleton;
the skill does not ship empty placeholder templates.

## Hybrid tool catalog

HoudiniMCP uses a compact, documented tool surface by default. Frequently used
operations remain direct MCP tools, while the complete capability set is
available through a typed catalog:

- `search_tools` searches executable capabilities together with the official
  HOM and node help bundled with the active Houdini installation.
- `get_tool_schema` returns validated arguments, risk/undo metadata, examples,
  and traceable SideFX documentation references.
- `call_tool` validates dynamic arguments before relaying a catalog command to
  Houdini.

The default `hybrid` mode exposes eight direct Houdini tools plus these three
catalog tools. Existing clients can restore the original expanded surface by
setting `HOUDINI_MCP_TOOL_MODE=legacy` in the MCP server environment. The
installation command, stdio transport, TCP port, shelf tools, and Houdini
package layout are identical in both modes.

The catalog currently contains 43 capabilities. In addition to node, graph,
geometry, material, render, HIP, and HDA creation operations, it includes:

- `apply_hda_interface_patch` for planned, revision-checked parameter promotion
  into an existing external HDA, with an on-disk backup rollback path;
- `get_material_assignments` for OBJ parameters, Material SOP assignments,
  primitive `shop_materialpath` values, and USD material relationships;
- `get_stage_snapshot` for bounded, revisioned USD prim, layer, edit-target,
  purpose, kind, and material-binding inspection.

Tool schemas report effect scope, rollback strategy, prerequisites, expected
result size, risk, and three-state availability. `search_tools` can filter by
effect scope and rollback strategy. When Houdini has not connected yet, its
session-dependent capabilities are reported as `unknown` rather than falsely
claiming to be available.

### SideFX documentation binding

Catalog metadata is grounded in the official documentation installed with the
currently connected Houdini version. The bridge asks Houdini for its runtime
version and `$HFS`/`$HH`, then reads `hom.zip` and `nodes.zip` directly without
extracting or copying them. It also returns canonical `sidefx.com` links for
human reference.

Discovery is portable and never assumes a drive letter or username. The order
is: optional `HOUDINI_MCP_DOC_ROOT`, connected Houdini, inherited `$HFS`/`$HH`,
then platform installation discovery. If local help is unavailable, tools
continue working with `docs_status: degraded`; the MCP server never requires a
runtime web request.

Example catalog workflow:

```text
search_tools(query="material")
get_tool_schema(name="set_material")
call_tool(name="set_material", arguments={"node_path": "/obj/geo1"})
```

`execute_houdini_code` remains available as a high-risk last resort. Calling it
through `call_tool` requires `allow_unsafe=true`; prefer documented dedicated
tools because they validate inputs and preserve Houdini undo behavior.

Below are the complete instructions for setting up Houdini, uv, and Claude Desktop.

---

## Table of Contents

1. [Requirements](#requirements)  
2. [Houdini MCP Plugin Installation](#houdini-mcp-plugin-installation)  
   1. [Folder Layout](#folder-layout)  
   2. [Shelf Tool (Optional)](#shelf-tool-optional)  
   3. [Packages Integration (Optional)](#packages-integration-optional)  
3. [Installing the `mcp` Python Package](#installing-the-mcp-python-package)  
   1. [Using uv on Windows](#using-uv-on-windows)  
   2. [Using pip Directly](#using-pip-directly)  
4. [Bridging Script and Claude for Desktop](#bridging-script-and-claude-for-desktop)  
   1. [The Bridging Script](#the-bridging-script)  
   2. [Telling Claude Desktop to Use Your Script](#telling-claude-desktop-to-use-your-script)  
5. [Testing & Usage](#testing--usage)  
6. [Troubleshooting](#troubleshooting)

---

## Requirements

- **SideFX Houdini**  
- **uv** 
- **Claude Desktop** (latest version)

---

## 1. Houdini MCP Plugin Installation

### 1.1 Folder Layout

Create a folder in your Houdini scripts directory:
C:/Users/YourUserName/Documents/houdini19.5/scripts/python/houdinimcp/

Inside **`houdinimcp/`**, place:

- **`__init__.py`** – handles plugin initialization (start/stop server)  
- **`server.py`** – compatibility import for the Houdini server
- **`houdinimcp_runtime/`** – Houdini-side server and render implementation
- **`houdini_mcp_server.py`** – backward-compatible bridge launcher
- **`houdini_mcp_bridge/`** – bridge, catalog, registry, and docs implementation
- **`pyproject.toml`** – Python dependencies


Copy the complete repository layout rather than copying only the three root
Python files. The root launchers depend on the two implementation subpackages.

### 1.2 Shelf Tool 

Ready-to-copy start and stop examples are available under `scripts/shelf/`.

create a **Shelf Tool** to toggle the server in Houdini:

1. **Right-click** a shelf → **"New Shelf..."** 

Name it "MCP" or something similar



2. **Right-click** again → **"New Tool..."** 
Name: "Toggle MCP Server"
Label: "MCP"

3. Under **Script**, insert something like:

```python
   import hou
   import houdinimcp

   if hasattr(hou.session, "houdinimcp_server") and hou.session.houdinimcp_server:
       houdinimcp.stop_server()
       hou.ui.displayMessage("Houdini MCP Server stopped")
   else:
       houdinimcp.start_server()
       hou.ui.displayMessage("Houdini MCP Server started on localhost:9900")

```


### 1.3 Packages Integration 

If you want Houdini to auto-load your plugin at startup, create a package file named houdinimcp.json in the Houdini packages folder (e.g. C:/Users/YourUserName/Documents/houdini19.5/packages/):
```json
{
  "path": "$HOME/houdini19.5/scripts/python/houdinimcp",
  "load_package_once": true,
  "version": "0.1",
  "env": [
    {
      "PYTHONPATH": "$PYTHONPATH;$HOME/houdini19.5/scripts/python"
    }
  ]
}
```

### 2 Using uv on Windows
```powershell
  # 1) Install uv 
  powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

  # 2) add uv to your PATH (depends on the user instructions) from cmd
  set Path=C:\Users\<YourUserName>\.local\bin;%Path%

  # 3) In a uv project or the plugin directory
  cd C:/Users/<YourUserName>/Documents/houdini19.5/scripts/python/houdinimcp/
  uv add "mcp[cli]"

  # 4) Verify
  uv run python -c "import mcp.server.fastmcp; print('MCP is installed!')"
```
### 3 Telling Claude for Desktop to Use Your Script
Go to File > Settings > Developer > Edit Config > 
Open or create:
claude_desktop_config.json

Add an entry:

```json
{
  "mcpServers": {
    "houdini": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "C:/Users/<YourUserName>/Documents/houdini19.5/scripts/python/houdinimcp/houdini_mcp_server.py"
      ]
    }
  }
}
```
if uv run was successful and claude failed to load mcp, make sure claude is using the same python version, use:
```cmd
  python -c "import sys; print(sys.executable)"
``` 
to find python, and replace "python" with the path you got. 

### 4 Use Cursor
Go to Settings > MCP > add new MCP server
add the same entry in claude_desktop_config.json
you might need to stop claude and restart houdini and the server

### 5 OPUS integration

OPUS provide a large set of furniture and environmental procedural assets.
you will need a Rapid API key to log in. Create an account at: [RapidAPI](https://rapidapi.com/)
Subscribe to OPUS API at: [OPUS API Subscribe](https://rapidapi.com/genel-gi78OM1rB/api/opus5/pricing)
Get your Rapid API key at [OPUS API](https://rapidapi.com/genel-gi78OM1rB/api/opus5)
copy `urls.env.example` to `urls.env` and add your key (the file is gitignored).
OPUS integration is optional — without a key the server still starts, only the OPUS tools are disabled.
### 6 Acknowledgement

Houdini-MCP was built following [blender-mcp](https://github.com/ahujasid/blender-mcp). We thank them for the contribution.
