# Frank RG explicit file maintenance

File maintenance is separate from source refresh, table interpretation,
calculations and publication. Recognizing an older delivered file does not
authorize deletion. A normal refresh performs no automatic cleanup.

The standard actions are:

| Command | Input | Output and effect |
| --- | --- | --- |
| `command.material.maintenance_plan` | Actual inventory and explicitly requested actions/scope | Pure reviewable plan |
| `command.material.maintenance_apply` | Exact plan and current expected state | Per-action effect receipts from the selected filestore |

Requested actions identify the source locator, operation, destination when
applicable, and expected exact content identity. Application verifies the
current source state before a mutation. A changed source or conflicting
destination stops the corresponding effect. Unknown confirmations remain
addressable in the effect ledger and require reconciliation before retry.

Canonical filenames are constructed with the shared domain naming rules;
building a destination name is a pure action. Moving or deleting the actual
material requires the explicit maintenance command and provider authority.
Same-issue competing originals need an explicit resolution before one can be
selected for a destructive action.

Runtime facts distinguish planning, command completion and confirmed effects.
A notification may subscribe to retained facts through
`command.notification.prepare`, then use the independent deliver/reconcile
commands. Delivery failure does not repeat parsing, calculations or maintenance.

See [the main data route](frank-rg-data-route.md) and
[archive construction](frg-streaming-archive.md).
