# Curve instancing

## Use when

The input is a curve or path and the product is repeated modules, swept cables, supports, borders, or engine instance points. Do not use it for unconstrained surface scattering or a unique sculpted mesh.

## Contracts

- Input curves declare open/closed state, direction, units, discontinuities, and allowed corner behavior.
- Module variants declare physical length, pivot convention, forward axis, scale policy, and engine path.
- Outputs declare whether they are points, packed primitives, render geometry, collision, or several products.

## Stages

Clean and orient curves -> measure and classify spans/corners -> resample or partition -> create deterministic variant/orientation/scale attributes -> preview proxies -> instance or sweep -> UV/material/collision -> validate outputs.

Use points and proxies until real geometry is required. Separate straight spans, convex/concave corners, endpoints, and supports when they need different assets. Optional Vellum relaxation belongs in a distinct branch before final geometry.

## Acceptance

- No invalid or empty instance paths; finite transforms and stable seed.
- Module coverage respects gap/overlap tolerance and corner policy.
- Closed seams do not duplicate or omit a module unexpectedly.
- Output attributes match the engine profile and point count stays within budget.

Common failures are reversed curve direction, non-uniform module pivots, scale used to hide an incorrect length classification, and generating full geometry before the layout is stable.
