# Pivot Painter hierarchy export

## Use when

Vegetation or modular rigid parts need hierarchical wind or local pivot animation in a game-engine shader.

## Contracts

- Source pieces declare deterministic identity, hierarchy level, parent relation, local pivot/basis, and render geometry membership.
- Export declares Pivot Painter version/mode, animatable-element limit, texture packing, engine axes, mesh output, and material/shader expectations.

## Stages

Prepare clean pieces -> derive or validate hierarchy -> generate pivots and parent relationships -> validate acyclic deterministic ordering -> build local bases -> pack data -> export mesh and textures -> engine-side verification.

Index animatable hierarchy levels before non-animatable terminal elements when the engine/tool version requires that limit behavior. Keep this as a compatibility rule, not a universal ordering rule.

## Acceptance

- Every non-root element has one valid parent and the hierarchy is acyclic.
- Pivots/bases are finite and visibly correspond to intended deformation joints.
- Element/index limits and texture dimensions pass.
- Exported geometry and textures share the same hierarchy revision.

Common failures are hierarchy inferred from unstable primitive order, duplicated names, incorrect local bases, and exporting geometry after the packed textures were generated from an older revision.
