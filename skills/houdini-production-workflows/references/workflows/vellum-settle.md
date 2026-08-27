# Vellum settle and freeze

## Use when

Cloth, cables, or flexible geometry should settle into a static or cached result. Do not keep a live Vellum network in the final game asset unless the requested product is an animation cache.

## Contracts

- Source geometry declares topology, resolution budget, thickness/pscale, rest state, UV preservation, and material groups.
- Pin and collision inputs are separate, validated products with clear animation policy.
- Simulation declares FPS, frame range, solver scale, seed, substeps/iterations budget, and target frozen frame or animation output.

## Stages

Validate/remesh -> define constraints and pins -> prepare collision -> low-cost preview sim -> inspect stability/intersections -> approved-quality sim -> postprocess -> choose/freeze frame or cache range -> optimize/UV/material -> validate.

Do not use a Timeshift to conceal an unstable simulation. The chosen frame must pass velocity, intersection, and shape checks.

## Acceptance

- Pin group exists and collision scale is correct.
- Preview proves the intended motion before high-quality cook.
- Frozen result has acceptable intersections and finite attributes.
- UV/material groups survive remesh and postprocess; optimized mesh meets budget.

Common failures are excessive remesh density, wrong scene scale, missing animated-collider policy, and recooking the full simulation on every parameter edit.
