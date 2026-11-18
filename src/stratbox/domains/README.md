# Business domains

Source-specific business logic lives under `stratbox.domains.<publisher>`,
then substantive publication families and independently owned statistical series.

Current publishers are `cbr`, `fns`, and `frank_rg`. Grouping packages may
contain source-level helpers but never claim child operations implicitly.

An owner publishes exactly one `_registration.py` containing its immutable
`OperationRegistration`. The owner ID is its full dotted package path relative
to `stratbox.domains`. Only manifest-bearing packages own operations.
The `domains.registry` discovers bundled manifests recursively and validates
that definition, handler and codec belong to the *nearest* owner. The ordinary
`operations.py` and `api.py` contain executable implementations.

The domain-layer structure is independent of storage taxonomy: original
publications, normalized datasets and views may use different classifications.
Source-specific geography, observation periods and publication layouts remain
in the owning domain. Shared statistical contracts and neutral execution/storage
logic belong to `shared` and `core` respectively.

[Functional ownership and semantic invariants](../../../docs/architecture/domain-functional-semantics.md)
