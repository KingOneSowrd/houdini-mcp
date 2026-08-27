# Surface growth and foliage

## Use when

Branches, vines, shrubs, or foliage must grow across or within an input shape. Do not use it for ordinary scatter-only dressing when no growth path or hierarchy is needed.

## Contracts

- Input surface declares scale, watertight expectations, normals, start/end masks, obstacles, and coverage target.
- Growth points and curves preserve a deterministic seed, branch identity, cost/distance measure, radius or scale, and hierarchy when animation needs it.
- Leaves declare variant, orientation, atlas/material, scale range, and dry/live classification when applicable.

## Stages

Prepare/remesh input -> derive growth region and costs -> choose deterministic starts/targets -> solve and clean paths -> construct branch curves/mesh -> create leaf points and variants -> material and engine attributes -> optional Pivot Painter preparation.

Keep branch curves as the authoritative intermediate product. Generate leaf instances late and avoid baking project-specific Megascans paths into the recipe.

## Acceptance

- Paths stay on or within the allowed region and do not contain disconnected micro-branches.
- Branch radius and leaf scale remain finite and within budget.
- Hierarchy is acyclic and deterministic when present.
- Materials and instance paths resolve through the project profile.

Common failures are over-remeshing, dependence on accidental point order, non-reproducible starts, and copying full leaf geometry too early.
