# Experience lifecycle

## Record types

- **Case:** contextual evidence from a HIP/HDA, tutorial, production task, or failure.
- **Recipe:** a reusable workflow contract with stages and acceptance checks.
- **Experience:** one execution, its decisions, corrections, outputs, and measured acceptance.
- **Template manifest:** the machine-readable contract for an inert HIP/HDA skeleton.

## Statuses

`candidate -> validated -> canonical -> deprecated`

- Candidate records may be generated automatically.
- Validated records have reproducible evidence in their declared environment.
- Canonical records have independent supporting cases or runs, defined exceptions, and passing acceptance checks across their declared scope.
- Deprecated records remain traceable and name their replacement when one exists.

Never promote only because the same user repeated a preference in one project. Classify corrections as Houdini invariant, engine convention, project convention, version workaround, tool defect, artistic preference, or one-off asset issue.

## Automated ingestion

Run `inspect_houdini_case.py` under Hython with manual update mode. It may inspect definitions, node types, parameter interfaces, sticky notes, and external references, but it must not cook expensive branches, save the source, write caches, export, install packages, or declare acceptance.

Run `experience_cli.py validate` and `reindex` after adding records. `assess` reports missing evidence but does not change status. Promotion remains an explicit repository change backed by evidence.

## What to capture from repeated corrections

Record the goal, context, original decision, user correction, root-cause classification, graph or parameter delta, result, and acceptance. Prefer a normalized patch summary over a full chat transcript. Repeated correction clusters should first improve routing, contracts, validation, recipes, or project profiles; only deterministic cross-workflow operations should become MCP capabilities.
