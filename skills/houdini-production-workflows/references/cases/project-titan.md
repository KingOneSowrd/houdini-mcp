# Project Titan evidence summary

Project Titan is a SideFX game-content case corpus, not a universal template. The inspected local corpus contains twelve HDA definitions, three standalone tutorial HIPs, and one train-destruction workflow with many backups. It demonstrates fifteen useful workflow families.

Shared evidence includes contract-first inputs, point/attribute-driven instancing, deterministic seeds, proxy-first construction, simulation followed by a frozen or cached result, engine-specific material/instance attributes, and multi-artifact outputs such as FBX, EXR, JSON, and `.bgeo.sc`.

Important local limitations include older SideFX Labs node versions, hard-coded Unreal `/Game/...` references, a hard-coded advertisement JSON path, mostly empty HDA Help sections, mixed source/cache/export directories, and license-mode warnings while loading some assets. Preserve these as case limitations rather than copying them into recipes.

The main extracted routes are:

- cable, fence, and rail -> curve instancing, with optional Vellum relaxation for cable;
- ivy and shrub -> surface growth and foliage instances;
- platform and building -> modular generation from outlines, corners, patterns, or data tables;
- cloth -> Vellum settle, optimize, freeze, material contract;
- stacking and train destruction -> RBD preparation, Bullet, cache, product split, optional VAT;
- smoke -> source attributes, sparse Pyro, loop, bake, flipbook;
- modular train and character animation -> KineFX/FBX and VAT;
- procedural trees -> hierarchy construction and Pivot Painter export.

Use the curated machine-readable records under `references/records/cases/` for evidence and provenance. Do not treat backup HIPs as independent cases.
