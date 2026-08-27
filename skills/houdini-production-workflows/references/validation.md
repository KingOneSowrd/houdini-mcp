# Validation and acceptance

Use the cheapest validation that can falsify the next expensive step.

## Before building

- Confirm Houdini/Labs/node-type availability, license state, units, FPS, frame range, target engine, input node identity, and external references.
- Confirm whether output files, cache directories, or external HDA definitions may be written.

## Before simulation or cache

- Validate input groups and attributes, packed state, unique names, collision inputs, pin or constraint groups, finite transforms, and a small preview range.
- Establish a time or frame budget and a cancellation/status path when asynchronous jobs are available.

## Before export

- Validate output node, topology policy, material and instance paths, coordinate/unit conversion, filenames, directory existence, collision/LOD policy, and overwrite behavior.
- Evaluate the exact export frame range rather than relying on the global playbar implicitly.

## Final acceptance

- Re-inspect output geometry contracts.
- Verify every requested artifact exists, is non-empty, and belongs to the current run.
- Report cook warnings, missing optional outputs, degraded documentation, unavailable dependencies, and any validation skipped.
- Record measurable results: primitive/point counts, instance count, frame range, artifact paths, elapsed time when available, and acceptance pass/fail.

Do not accept a workflow because its nodes were created or a render button returned without error.
