# HIP and HDA template authoring

Templates are executable structure, not universal solutions.

Use stable stage prefixes such as `IN_`, `PREP_`, `GUIDE_`, `PREVIEW_`, `SIM_`, `CACHE_`, `VALIDATE_`, `OUT_`, and `EXPORT_`. Expose inputs, outputs, seeds, units, frame range, engine profile, cache path, and expensive-stage switches at the semantic boundary.

Every template must:

- open without automatically cooking a long simulation, writing a cache, rendering, or exporting;
- avoid machine-specific absolute paths and project-specific engine assets;
- define named entry and output nodes;
- separate preview, high-quality, simulation, cache, and export branches;
- declare Houdini/Labs compatibility and expensive nodes in a template manifest;
- preserve a clean insertion namespace and collision policy;
- contain validation markers for its input and output contracts;
- be tested in a fresh temporary HIP through Hython.

Do not copy thousands of embedded solver or third-party HDA nodes into a template. Reference the installed node type and validate availability. Prefer several composable stage templates over many nearly identical full HIP files.
