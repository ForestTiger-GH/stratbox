# Business domains

Source-specific business logic lives under `stratbox.domains.<publisher>`.
Functional owners contain substantive publication families and statistical series.

Publishers are `cbr`, `fns`, `frank_rg`, `minfin`, and `rosstat`. Publications,
documents, tables, integration, analytics and products have independent
responsibilities; operation facades compose them explicitly.

An owner publishes exactly one `_registration.py` containing its immutable
`OperationRegistration`. The owner ID is its full dotted package path relative
to `stratbox.domains`. Only manifest-bearing packages own operations.
The `domains.registry` discovers bundled manifests recursively and validates
that definition, handler and codec belong to the *nearest* owner. Executable entry points live in the publisher's `operations` package.

[Independent processing and replay](../../../docs/current-how/independent-domain-data-routes.md)

The domain-layer structure is independent of storage taxonomy: original
publications, normalized datasets and views may use different classifications.
Source-specific geography, observation periods and publication layouts remain
in the owning domain. Shared statistical contracts and neutral execution/storage
logic belong to `shared` and `core` respectively.

[Functional ownership and semantic invariants](../../../docs/architecture/domain-functional-semantics.md)
