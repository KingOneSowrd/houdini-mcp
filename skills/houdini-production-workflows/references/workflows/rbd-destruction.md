# RBD destruction and stacking

## Use when

Packed rigid bodies, fracture, constraint-driven destruction, or physics-assisted stacking produce a static or animated game product.

## Contracts

- Source pieces declare material class, unique non-empty `name`, packed state, transform/pivot, mass policy, and render/proxy relationship.
- Constraints declare names/types, endpoints, strength/break policy, and whether they may update during simulation.
- Simulation declares scene scale, collision representation, activation/emission, frame range, seed, solver budget, cache path, and product split.

## Stages

Separate material strategies -> fracture or prepare variants -> assign names and physical properties -> build/validate constraints -> create proxy collisions -> low-cost Bullet preview -> approved simulation -> versioned cache -> reconstruct/deform render geometry -> split products -> optional VAT -> validate artifacts.

For stacking, use proxies and bounded random rotation/scale, settle, then freeze a verified frame. For destruction, keep metal, glass, concrete, or other materially different strategies separate until the requested product boundary.

## Acceptance

- Piece names are unique and constraints reference valid pieces.
- Packed/render/proxy transforms agree and no unexpected empty names exist.
- Cache frame range is complete and belongs to the current source revision.
- Final products retain material groups and meet topology/VAT policy.

Common failures are mixed packed/unpacked inputs, stale caches, render geometry used as collision, wrong scale, and exporting before the simulation is validated.
