# MCP collaboration contract

Houdini MCP uses a compact Hybrid surface. Keep the skill independent of the exact catalog size.

## Capability selection

1. Use a known direct tool for a high-frequency primitive operation.
2. Otherwise call `search_tools` with the desired effect and relevant domain terms.
3. Read `get_tool_schema` before the first call or whenever arguments, availability, risk, effect scope, rollback, or prerequisites are uncertain.
4. Execute through `call_tool` with validated arguments.
5. Use `execute_houdini_code` only as a high-risk escape hatch when a repeatable typed capability does not exist. State why it is required and do not turn it into an undocumented normal path.

## Read before write

Capture a bounded scene or network snapshot, current revision, target node identities, relevant parameter state, and external references. Re-check the revision before applying a planned patch when intervening edits are possible.

## Mutation boundaries

- Group related graph changes into one understandable Undo unit when supported.
- Preserve expressions, keyframes, multiparms, spare parameters, locked definitions, and user data unless the contract explicitly changes them.
- Do not unlock a third-party or production HDA merely to reach an internal node.
- Save to a new HIP unless overwrite is explicitly requested.
- Treat render, simulation, cache, export, package installation, and external HDA writes as separate effect scopes.

## Result handling

Interpret success envelopes as execution evidence, not production acceptance. Validate the scene and requested artifacts separately. On error, preserve the failing operation, origin, last safe revision, and whether a retry would be idempotent.
