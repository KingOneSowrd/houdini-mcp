# Pyro and flipbook production

## Use when

Density, temperature, burn, velocity, or similar sources drive smoke/fire that must become a loop, volume cache, or engine flipbook.

## Contracts

- Source declares fields, emission ranges, scale, seed, bounds, and animation policy.
- Simulation declares voxel size, sparse bounds behavior, FPS/frame range, disturbance/turbulence policy, and memory/time budget.
- Flipbook declares camera/capture bounds, rows/columns, channel packing, color space, texture size, output format, and engine material contract.

## Stages

Prepare source points/attributes -> rasterize fields -> low-resolution sparse preview -> validate bounds and motion -> approved simulation/cache -> optional loop construction -> look/bake fields -> capture guide/camera -> flipbook render -> texture and metadata validation.

Keep simulation quality separate from presentation density. Use a guide for capture bounds and never start a full flipbook render before a representative frame and channel preview pass.

## Acceptance

- Required fields exist and remain inside the intended bounds.
- Memory/voxel budget and frame range are explicit.
- Loop transition meets the defined tolerance when looping is requested.
- Every texture channel, tile, metadata value, and material reference is present and correctly packed.

Common failures are clipped capture bounds, mismatched FPS, render density used to compensate for poor source fields, and silent color-space/channel-packing mistakes.
