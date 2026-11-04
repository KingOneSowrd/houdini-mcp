# Geometry attribute observation

The catalog now supports reading all four attribute owners and comparing
detached, session-local observations. This is SOP geometry observation; it is
not a universal inspector for DOP, USD, packed payloads, or volume voxels.

Use `search_tools`, `get_tool_schema`, then `call_tool`. The compact Hybrid
direct surface is unchanged. Legacy `get_geometry_data` accepts the new options.
Restart the Houdini Shelf MCP server **with the updated module loaded**, and
reconnect/restart the external MCP bridge to obtain the new schemas. If the
Shelf command merely stops/starts an existing Python object, reload its modules
or restart Houdini after saving your work.

## Read values

`get_geometry_data` accepts `element="points" | "primitives" | "vertices" |
"detail"`, explicit `attributes`, `start`, and `limit` (default 100, maximum
500). `output_index` selects a SOP output. `frame` evaluates that frame using
`geometryAtFrame` without changing the global timeline frame.

Vertex rows include `number` (linear vertex id), `primitive_number`,
`vertex_index` (within primitive), and `point_number`. Pagination traverses
primitive/local-vertex order, which need not equal linear vertex order.
Detail has one row. Attribute owner matters: point UV cannot substitute for
vertex UV at a seam. Prefer explicit attribute lists.

Live pages preserve the legacy flattened values. An attribute whose name
collides with a locator such as `number` can shadow that locator in this legacy
shape; snapshot pages avoid this by nesting values under `attributes`.

Values are JSON-safe: nonfinite floats become `{"__nonfinite__":"nan"}` or
`inf`/`-inf`. Arrays/dictionaries and strings have configurable limits
(`max_value_items`, `max_string_length`); truncation is explicit. `max_bytes`
bounds row data, not the entire enclosing response. A single oversized row
returns an error instead of silently dropping it. Use `next_start` for paging.
Live pages can observe different cooks; use snapshots for stable pagination.

## Capture before changing the node

For example, call `capture_geometry_snapshot` with:

```json
{
  "path": "/obj/geo1/OUT_UV_READY",
  "element": "vertices",
  "attributes": ["uv"],
  "allow_cook": false,
  "max_elements": 10000,
  "max_bytes": 1048576
}
```

Save its returned `snapshot_id`, make the intended edit, then capture another
snapshot. Compare IDs with `compare_geometry_snapshots`. The tool also supports
upstream/downstream comparisons by capturing two nodes. Captured values are
detached JSON, not references to geometry that can later change.

`allow_cook=false` is the snapshot default. It requires clean, previously cooked
output 0 at the current frame; dirty/error nodes, other outputs and other frames
return an explicit error. This is a conservative Cook preflight, not a sandbox
for arbitrary node callbacks. Use `allow_cook=true` only when evaluating the
chosen graph is within the task's intended costs/effects. Live
`get_geometry_data` defaults to true for compatibility. Neither tool changes
display/render flags or saves the HIP. Do not scan expensive networks blindly.

The runtime retains at most **8 snapshots / 16 MiB**, evicting the oldest first.
IDs expire when released, evicted, or the server restarts. Capture results report
evicted IDs. `get_geometry_snapshot_data(snapshot_id, start, limit, max_bytes)`
pages through captured values without recooking. Its rows use an `attributes`
mapping, with separate locator and `truncated_attributes` fields.
`release_geometry_snapshot(snapshot_id)` frees session memory.

## Establish correspondence before comparing

- Prefer a captured unique scalar integer/string attribute via `key_attribute`
  (for example point `id`, primitive `name`, or an authored unique vertex key).
  Duplicate, absent, truncated or non-scalar keys are rejected in captured rows.
  Unmatched rows are reported. Partial capture cannot establish global key
  uniqueness or equality.
- Index comparison requires `assume_index_correspondence=true` **and** equal,
  complete topology summaries. This is a caller assertion of stable identity;
  equal connectivity and counts cannot prove that points were not reordered.
- Detail values need no matching key. Different owners cannot be compared
  directly; all-owner schema additions/removals still expose owner changes.
- Topology scanning is capped at 100,000 points/primitives/vertices. Above that
  bound, topology equality is unknown and index matching is unavailable; use
  reliable keys. The hash covers primitive types and ordered vertex-to-point
  connectivity, not primitive intrinsics or identity.

Results include owner/type/size/array schema changes, counts, matched/unmatched
rows, changed rows and fractions, maximum absolute and RMS component deltas,
nonfinite components, and bounded examples. Set finite nonnegative
`absolute_tolerance` and `relative_tolerance`; both default to `1e-6`.
Value examples/details may be omitted to bound comparison responses; flags and
counts explain omissions.

`equal_selected_values=true` concerns **only selected, fully captured values**;
it is not whole-geometry equivalence. Truncated rows/values, unmatched elements,
empty attribute selections or incompatible selected schema cannot establish
that equality. A changed schema outside the selection can coexist with equal
selected values. Snapshots capture one owner at a time and bounded prefix rows,
not random samples. Large single HOM attribute values must still be materialized
before truncation; these bounds are not a hard ceiling on Houdini's Cook memory.

Group membership diffs, vector-angle metrics, automatic cross-topology spatial
correspondence and disk-persistent snapshots remain future extensions. Use
`get_geometry_info` separately for group names and bounding boxes.

## Validation

Unit tests: `python -m unittest tests/test_geometry_observation.py`.
Real geometry tests: `hython tests/test_geometry_observation_hython.py` in an
isolated process. Framed TCP/catalog test: start `tests/headless_host.py` on an
isolated port, then run `python tests/test_geometry_catalog.py <port>`.
