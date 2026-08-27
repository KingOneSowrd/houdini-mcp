# Geometry and engine contracts

Validate attribute owner, storage type, tuple size, cardinality, value domain, and time stability—not names alone.

| Product | Typical required contracts |
|---|---|
| Instance points | `orient` or valid `N`/`up`, `pscale` or `scale`, variant/instance path, finite transforms |
| Unreal instances | `unreal_instance` or the project-approved instance path attribute, valid `/Game/...` target |
| Material assignment | primitive `shop_materialpath`, `unreal_material`, or USD material relationship according to output domain |
| Modular pieces | unique `name`/module identity, dimensions, priority, variation weights, orientation convention |
| Packed RBD | unique non-empty `name`, packed pieces, valid transforms, collision proxy policy, constraint schema |
| KineFX | stable joint names and parent hierarchy, transforms and `rest_transform`, matching capture data |
| VAT | stable point count/order and topology for the selected VAT mode, explicit frame range/FPS, bounded texture dimensions |
| Pivot Painter | deterministic hierarchy and parent indices, valid pivots/bases, engine-specific element limit |
| Volume/flipbook | named fields, voxel and capture bounds, frame range, channel packing and color-space contract |

Project-specific asset paths, material paths, coordinate conversions, units, and naming prefixes belong in a project profile. Do not promote them into universal workflow rules.

For time-dependent outputs, sample at least the contractually important frames: start, end, known transition frames, and any frame used as a frozen result. Do not infer stability from a single frame.
