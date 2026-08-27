---
name: houdini-production-workflows
description: Plan, inspect, build, validate, cache, and package multi-step Houdini procedural and game-content workflows through Houdini MCP. Use for PCG modeling, HDA authoring, simulations, VAT, Pivot Painter, and engine-ready asset production; not for simple Houdini questions or development of the MCP server itself.
---

# Houdini Production Workflows

Use this skill as the decision and validation layer above Houdini MCP. Treat cases as evidence, references as scoped knowledge, recipes as executable intent, templates as inert structure, MCP as the only normal execution path, and acceptance checks as the definition of completion.

## Operating loop

1. **Discover** the connected Houdini version, license, SideFX Labs availability, current HIP path and dirty state, target engine, frame range, external references, relevant network, and requested output.
2. **Contract** the inputs, required geometry attributes, outputs, budgets, file writes, expensive cooks, and acceptance checks. Infer harmless details, but do not invent project paths, engine assets, budgets, or overwrite permission.
3. **Route** to one workflow below and read only its reference. If no route fits, use the common loop without forcing a case analogy.
4. **Plan** a bounded preview path and rollback boundary before mutation. Prefer existing project conventions and live node definitions over remembered parameter names.
5. **Build preview** through direct MCP tools or `search_tools` -> `get_tool_schema` -> `call_tool`. Do not use arbitrary Houdini Python for a repeatable operation unless no typed capability exists and the user-authorized task cannot otherwise proceed.
6. **Validate** at stage boundaries. A created node is not a completed production result.
7. **Cook, cache, or export** only when the requested scope includes it, prerequisites pass, paths are resolved, and overwrite behavior is explicit.
8. **Verify** the scene contract and every requested artifact. Report partial success precisely.
9. **Capture experience** as a candidate record when this skill lives in a writable project checkout. Record decisions, corrections, failures, and acceptance results; never auto-promote the record to a canonical rule.

The state progression is `DISCOVER -> CONTRACT -> PLAN -> BUILD_PREVIEW -> VALIDATE -> COOK_OR_CACHE -> EXPORT -> VERIFY`. Return to the nearest safe state after failure instead of blindly replaying the full workflow.

## Workflow routing

- Curves, fences, rails, cables, roads, or path modules: read [curve-instancing.md](references/workflows/curve-instancing.md).
- Ivy, shrubs, branches, foliage, or surface growth: read [surface-growth.md](references/workflows/surface-growth.md).
- Buildings, module libraries, patterns, or data tables: read [modular-generation.md](references/workflows/modular-generation.md).
- Cloth settling or cable relaxation: read [vellum-settle.md](references/workflows/vellum-settle.md).
- Fracture, stacking, destruction, or Bullet: read [rbd-destruction.md](references/workflows/rbd-destruction.md).
- Smoke, looping volumes, flipbooks, or pyro baking: read [pyro-flipbook.md](references/workflows/pyro-flipbook.md).
- KineFX, FBX animation, VAT, or real-time animation export: read [realtime-animation.md](references/workflows/realtime-animation.md).
- Tree hierarchy, wind deformation, or Pivot Painter: read [pivot-painter.md](references/workflows/pivot-painter.md).

Use [workflow-index.json](references/workflow-index.json) for machine-readable routing and compatibility with the case-ingestion script.

## Shared contracts

- Read [mcp-usage.md](references/mcp-usage.md) before unfamiliar, risky, or catalog-driven operations.
- Read [geometry-contracts.md](references/geometry-contracts.md) whenever attributes, packed geometry, instancing, animation topology, or engine export are involved.
- Read [validation.md](references/validation.md) before simulation, cache, export, or final acceptance.
- Read [template-authoring.md](references/template-authoring.md) before creating or merging a HIP/HDA template.
- Read [experience-lifecycle.md](references/experience-lifecycle.md) when ingesting a new case, mining repeated corrections, changing a recipe, or promoting knowledge.
- Read [constitution.md](references/constitution.md) when changing this skill's architecture or resolving a conflict between a case and a general rule.

## Invariants

- Preserve user scope and existing scene work. Inspect before mutation and do not silently unlock or rewrite third-party HDAs.
- Prefer semantic contracts over a fixed node graph. Equivalent networks are acceptable when outputs and budgets pass.
- Keep random processes reproducible with explicit seeds.
- Keep expensive simulation, cache, and export branches disabled or bypassed in templates and previews.
- Use `$HIP`, `$JOB`, project profiles, or user-provided roots instead of machine-specific absolute paths.
- Keep engine asset paths and artistic preferences project-scoped, not universal.
- Never treat a single successful case or user correction as a canonical rule.
- Completion requires observable acceptance evidence, not merely successful tool calls.

## Experience automation

Run `scripts/inspect_houdini_case.py` under Hython to produce a bounded candidate record from a HIP or HDA without saving or exporting it. Run `scripts/experience_cli.py validate` before committing records, `reindex` after record changes, and `assess` to see what evidence is still missing. Generated records remain `candidate` until verified across their declared scope.
