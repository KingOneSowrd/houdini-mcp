# HDA authoring and delivery

Use for reusable artist-facing HDAs with parameterized computation, preview,
explicit bake/export actions, and reproducible acceptance. Load
[template-authoring](../template-authoring.md) for asset delivery boundaries.

## Successful project evidence

[Hair Tangent Baker](../cases/hair-tangent-baker.md) is a user-accepted success:
embedded Python modules, native artist controls, SOP computation, and explicit
bake/export actions formed a reusable HDA. It supports the candidate
`hda-authoring-v1` recipe; it is one project, not independent cross-project proof.

[Titan EVO](../cases/titan-evo.md) adds a user-designated authority reference:
18 HDA definitions inspected as one related collection. Consult its asset
inventory for curve sag/collision controls, DataTable module selection, stable
local transforms, foliage controls, and simulation frame selection. This is
structural evidence with pending target-version and engine acceptance; it does
not promote the recipe or establish a new execution of it.

## Decision guidance

- Assess native nodes and reasonable node combinations in the target version.
  The user identified a native algorithm gap as the core reason for Python in
  Hair Tangent Baker. Distinguish that from a missing MCP wrapper for an
  existing native operation; unfamiliarity alone is not evidence of absence.
- Judge Python by ownership, reproducibility, artist control, and side effects.
  Embedded Python SOP algorithms and explicit asset commands are legitimate
  implementation choices. This does not authorize arbitrary Agent Python calls
  or relax MCP risk gates.
- Keep computation inputs and controls explicit. Store executable algorithms
  in the delivered asset or declared versioned dependencies, not only in an
  Agent session. Test the actual delivered definition, not just loose sources.
- Preserve the original input output when offering destructive reconstruction.
  Expose artistic intent through parameters and ramps rather than code edits.
- Treat neutral defaults and upgrades as compatibility contracts. Preserve
  instance values, expressions, ramps, layout, and lock state as applicable;
  do not absorb an artist's current values into factory defaults.
- Separate ordinary evaluation from explicit expensive bake/export commands.
  Optional geometry analysis can run during Cook when enabled and bounded;
  do not claim that all ordinary Cook is computationally free.
- Validate before writing; publish unique completed batches; preserve the last
  valid result on failure. Keep base input and result paths separate.
- Bind each report to its tested version and inputs. A historical success is
  evidence for that scope, not proof that the current release or engine passed.
- For interactive tools, evaluate whether curve deformation and collision
  post-processing meet the intended look before choosing a solver. Titan EVO's
  Cable documents this tradeoff; its collision thickness limits still apply.
- Separate DataTable field mapping, stable local transforms, module selection
  and project asset-path resolution. Keep these conventions explicit rather
  than copying Titan-specific paths or assuming all table schemas match.
- Inspect actual attribute schema and selected values at stage boundaries.
  Declarations in VEX/parameters are hypotheses until a bounded Cook confirms
  them. A TimeShift is frame selection, not a persistent cache.

## Acceptance

Check parameter response, neutral equivalence, input preservation, geometry/UV
contracts, explicit writes, cancellation, fresh definition instantiation and
HIP reopen. Verify engine appearance separately when required. Record pending
seams, direction ambiguity, dependencies, and version-specific limitations.
