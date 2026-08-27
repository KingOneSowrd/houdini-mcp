# Modular and data-driven generation

## Use when

A footprint, outline, pattern string, module library, or data table drives buildings, platforms, trains, kitbash assemblies, or similar game assets.

## Contracts

- Input outline declares winding, closure, floor/up axis, unit scale, holes, and cleanup tolerance.
- Module library declares identity, dimensions, pivot, allowed roles, variants, priorities, weights, and engine paths.
- Pattern grammar and data-table schema are versioned inputs. Do not infer a foreign table layout from a tutorial example.

## Stages

Validate source/data -> normalize module metadata -> classify faces/spans/corners/floors -> expand deterministic patterns -> place point/proxy modules -> resolve collisions and remainder policy -> build exceptional geometry such as roofs -> UV/material/collision -> validate products.

Keep the grammar, module metadata, and placement engine separable. Treat left-to-right/right-to-left ordering and coordinate conventions as explicit compatibility rules.

## Acceptance

- Every placement references a valid module and respects its dimensions/pivot.
- Pattern expansion terminates, is deterministic, and handles remainder explicitly.
- No unintended gaps, overlaps, flipped normals, or duplicate corner modules.
- Output separates instances, unique geometry, collision, and metadata as requested.

Common failures are hard-coded engine paths, implicit data-table schemas, mixing guide geometry into render output, and hiding incompatible module sizes with arbitrary scale.
