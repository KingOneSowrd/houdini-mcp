# Production workflow constitution

These principles govern conflicts between cases, recipes, templates, and MCP behavior.

1. **Evidence before generalization.** A HIP, tutorial, correction, or successful run is evidence in a context, not a universal instruction.
2. **Scope every claim.** Record the Houdini and plugin versions, engine, input domain, output product, and known exceptions that bound an experience.
3. **Encode at the lowest adequate layer.** Keep judgment in the skill, deterministic operations in MCP, reusable structure in templates, and observable truth in validators.
4. **Contracts outrank graph shape.** Prefer input, attribute, output, budget, and artifact contracts over insisting on a specific node sequence.
5. **Execution must be observable and recoverable.** Use bounded snapshots, revisions, Undo or backups, explicit expensive stages, and artifact manifests.
6. **Safety includes cost.** Unexpected long cooks, cache writes, renders, exports, HDA definition edits, and path overwrites are material side effects.
7. **Learn from corrections without overfitting.** Classify a correction as a universal invariant, engine convention, project preference, tool defect, version workaround, or one-off asset issue before encoding it.
8. **Deprecate rather than erase.** Preserve provenance, replacement links, and compatibility history so an old project can still explain why a decision existed.
9. **Tests arbitrate promotion.** Knowledge becomes canonical because independent cases and acceptance checks support it, not because its wording sounds convincing.
10. **Optimize production outcomes.** Measure first-pass acceptance, repeated correction rate, manual intervention, rollback success, cache reuse, engine rework, and time to verified output—not tool or template count.

The stable formula is:

`reliable workflow = transferable principle x explicit contract x executable recipe x observable execution x repeatable acceptance`

If any factor is missing, keep the knowledge at candidate status.
