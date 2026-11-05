---
name: houdini-production-workflows
description: Build and validate multi-stage Houdini production workflows through Houdini MCP, including PCG, HDAs, simulation, caching, and game-engine export. Not for simple questions or MCP server development.
---

# Houdini Production Workflows

Guide production Houdini work by the requested output and its acceptance criteria. Prefer existing project conventions and semantic geometry or artifact contracts over a prescribed node graph.

## Route only what the task needs

- For a supported multi-stage workflow, read [routing.md](references/routing.md), then load only the selected workflow file. Load a second workflow only when the requested output genuinely crosses domains.
- For scene inspection, a bounded parameter or graph edit, or an unsupported workflow, work directly through Houdini MCP without forcing a recipe.
- Read [mcp-usage.md](references/mcp-usage.md) before an unfamiliar or risky mutation, or when tool discovery is required.
- Read [geometry-contracts.md](references/geometry-contracts.md) when attributes, packed geometry, instancing, animation topology, or engine export determine correctness.
- Read [validation.md](references/validation.md) before simulation, cache, export, or final production acceptance.
- Read [template-authoring.md](references/template-authoring.md) when creating or merging a HIP/HDA template.
- Read [experience-lifecycle.md](references/experience-lifecycle.md) only when ingesting cases, changing recipes, or promoting reusable knowledge. Read [constitution.md](references/constitution.md) only when changing this skill's architecture or resolving a rule conflict.

`references/workflow-index.json` provides machine-readable routing for the case-ingestion tools.

## Decision boundaries

- Inspect enough current state to identify the target and protect existing work; do not require a full scene inventory for a small, well-bounded change.
- Infer harmless implementation details. Do not invent project paths, engine assets, budgets, or overwrite permission.
- Prefer typed MCP capabilities. Use arbitrary Houdini code only when no suitable typed capability exists and explain why the escape hatch is needed.
- Continue through reversible inspection, preview, and Undo-scoped graph edits when they are clearly part of the request. Treat long cooks, simulations, cache writes, renders, exports, package installs, external HDA writes, and overwrites as separate effect scopes; proceed only when the request includes them and their targets are resolved.
- Preserve locked or third-party HDAs, expressions, keyframes, multiparms, spare parameters, user data, and project-scoped conventions unless the task explicitly changes them.
- Keep random processes reproducible and expensive branches disabled or bypassed in previews and templates.

## Completion

Finish when the requested scene state or artifacts exist and the relevant acceptance checks pass. A created node or successful tool call is intermediate evidence, not completion. Report skipped checks, warnings, unavailable dependencies, and any partial result precisely.

## Experience tools

When maintaining this skill, use `scripts/inspect_houdini_case.py` for bounded HIP/HDA inspection and `scripts/experience_cli.py` to validate, reindex, or assess records. Candidate records stay non-canonical until their declared scope is independently verified.
