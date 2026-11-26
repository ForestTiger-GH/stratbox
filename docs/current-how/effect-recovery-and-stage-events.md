# Effects and uncertain outcomes

External writes and notification handoffs have deterministic effect identities derived from their logical purpose and actual input basis. The service records an intent as unknown before invoking a mutation. A confirmed receipt establishes the corresponding effect; a lost response does not authorize blind retry.

`lookup_effect()` exposes retained evidence. `reconcile_effect()` accepts verified provider evidence and preserves the same effect identity. `FileEffectState` makes records available after service restart; guarantees beyond the provider's actual persistence contract belong to the host.

Independent output and scope journal facts remain available even when an effect prevents whole-scenario completion. Storage uses create-only or compare-and-set operations with explicit preconditions.
