# Real-time animation, KineFX, and VAT

## Use when

FBX animation, a KineFX rig, deforming geometry, particles, fluids, or rigid simulations must play in a game engine through bones or Vertex Animation Textures.

## Contracts

- Source declares skeleton/point identity, rest pose, capture data, topology policy, FPS, frame range, clips, units, and axis conversion.
- VAT declares mode, stable point/order requirements, texture size/format, mesh output, data JSON, material/shader version, and engine target.
- Multiple clips using one mesh declare how the identical reference frame is enforced.

## Stages

Import/inspect source -> validate rest pose and topology -> normalize units/axes -> isolate clips/products -> preview deformation -> choose skeletal export or VAT mode -> validate texture limits -> export to a new versioned directory -> inspect FBX/textures/JSON/material data.

Do not assume that a successful FBX import exposes stable topology. Sample the full contractual range or use a mode whose identity rules match the source.

## Acceptance

- Skeleton hierarchy/capture or VAT topology contract passes.
- Clip ranges and FPS match the engine contract.
- Mesh, textures, JSON, and material/shader data refer to one current run.
- Texture dimensions and point counts remain within engine limits.

Common failures are inconsistent first frames across clips, stale data JSON, axis/unit mismatch, missing material integration, and mixing artifacts from different exports.
