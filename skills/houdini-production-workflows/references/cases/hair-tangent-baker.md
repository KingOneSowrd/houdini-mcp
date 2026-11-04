# Hair Tangent Baker — successful HDA delivery

Recorded 2026-11-04 after Agent review and the user's explicit confirmation:
“这次是个成功经验”. Outcome: **user-accepted success**. Knowledge maturity:
**candidate**, pending independent reuse. These are separate dimensions.

## Source and scope

Source locator `Hair_Tangent_Baker_HDA/` is relative to the user's project
collection, not this MCP repository. Resolve it against the supplied source
root. Development entry: `hair_tangent_baker_dev.hip`; asset library:
`hda/Mahua_Hair_Tangent_Baker_2.0.hda`; functional version 2.11.0, type
`mahua::hair_tangent_baker::2.0`. Reported environment: Houdini FX 21.0.440,
Python 3.11, NumPy and Pillow; Labs not required.

This is a retrospective source/report review, not a newly executed HDA run.
The Case, Experience and derived Recipe describe the same source project;
they must not be counted as independent cases. No binary template was imported.

## Why this delivery succeeded

1. `tools/python_module.py` loads embedded `Python/*.py` sections and keys the
   module namespace/cache by their content signature. Runtime logic belongs
   to the asset rather than the original development source directory.
2. `src/hair_tangent_baker/shape_adapter.py` connects native parameters, seed,
   phases and ramps to the algorithm. Constant ramps retain their exact value,
   preserving neutral behavior instead of introducing sampling roundoff.
3. Original, rebuilt and deformed mesh outputs have distinct contracts. Original
   geometry remains available; UV/topology preservation depends on the mode.
4. `houdini_adapter.py` separates checks, explicit baking and preview status.
   `baker.py` writes a staging directory, checks cancellation and renames the
   completed batch. Result paths do not replace base inputs.
5. Regression evidence measures artist-visible behavior: defaults, geometry,
   UV, Mikk basis, mask preservation and independent reopening.

This supports embedded Python computation and explicit asset tasks when they
are reproducible and controllable. It does not justify opaque one-off scripts
or imply Python is always preferable to native nodes/VEX.

## Evidence boundaries

| Source-relative evidence | What it supports |
|---|---|
| `reports/amplitude_profile_unit_report.json` | Historical report: 100 tests, zero failures/errors |
| `reports/amplitude_profile_hython_report.json` | 2.11.0: neutral geometry exact, source unchanged, rebuild/deform checks, 512 bakes, fresh external HDA and HIP reopen |
| `reports/hip_entry_validation.json` | Entry organization preserved geometry, parameters, expressions, curves, definition and layout; fresh reopen passed |
| `reports/standalone_report.json` | Standalone behavior for **2.4.0** only |
| `reports/portable_report.json` | Historical delivered ZIP portability; not latest development release acceptance |
| `reports/texture_seam_diagnostic.json` | Measured seam differences; Unreal lighting verification explicitly false |
| `tools/README.md` | Historical upgrades are version-dependent; latest external HDA/YY Normal/UV preprocessing has not received fresh package acceptance |

Known boundaries: automatic flow can have local direction-sign discontinuities;
UV seams remain ongoing work; Normal does not uniquely determine strand flow;
shared UVs can demand conflicting directions; no UDIM or independent Unreal
appearance acceptance is claimed. New geometry/UV versions require matching
rebakes and model exports. Old reports must not silently promote new binaries.

## Reuse

Reuse the delivery pattern: embedded modules, explicit controls, input/result
separation, neutral compatibility, staged outputs, and versioned acceptance.
Do not rerun `build_hda.py`, `upgrade_*`, `fix_*`, or archive tools as import
initialization. They have historical prerequisites and may write assets.

Records: Case `hair-tangent-baker-2-11-success`, Experience
`exp-hair-tangent-baker-2-11-success`, candidate Recipe `hda-authoring-v1`.

## Intake snapshot fingerprints

These identify files reviewed at intake, not a new runtime validation.

| Source-relative file | SHA256 |
|---|---|
| `hair_tangent_baker_dev.hip` | `6c79b4f3d83b00edb8141782caa2dc9c1ddbe6bda1c23bfef5bbf5959ac04551` |
| `hda/Mahua_Hair_Tangent_Baker_2.0.hda` | `ed9731ea3e1205b2f72f494b1102803b59efc2b3f8bdaf8d9571831370c22122` |
| `reports/amplitude_profile_unit_report.json` | `86de99a5dad25dc2800c19778ddd185bd511fe033eb95b47e62f3a44d5fe98f4` |
| `reports/amplitude_profile_hython_report.json` | `e8a868fca4f717afecf874af52afd003e75f2e528dafe7570f90bbc9e8455fa2` |
| `reports/hip_entry_validation.json` | `ceb8464af5d5b5c3c7faa87b690419590f7beef5fb30b469bde3257f5a171d67` |
| `reports/standalone_report.json` | `3edb026270e8992dbe70f04852aebf7325f84f864bd605e0ea33567fcadd61ee` |
| `reports/portable_report.json` | `d0094548b5dfd063da641c775a2d5aef39be0de295808b0fd5a880e31f2c6ac8` |
| `reports/texture_seam_diagnostic.json` | `a962c43e8b2d67474c80184a7748acb3829dd78b92de95424db4a2766980114e` |
| `tools/python_module.py` | `ecf9ebbb722544321b9f3f8dc9fb6c50d736459b423fd652b9c18a72a05e2fb0` |
| `src/hair_tangent_baker/shape_adapter.py` | `ad8aeb7c6300916fe1aff0f1f76418e60d8b105f35ebd32545cbe09ca7b60963` |
| `src/hair_tangent_baker/houdini_adapter.py` | `647be07edb308b018a550797146e6740044f0fcf76a1b0594b011bf4dba3beb5` |
| `src/hair_tangent_baker/baker.py` | `d23511c87d4eb76a241cfcdbc6667407b7f9347409aee1b1360fa2fd0035e3c8` |
| `tools/README.md` | `57c7de73f75e82ab0fdc0b3a9e8546eadbd6e4dc60c605f6b27875e07153923b` |
