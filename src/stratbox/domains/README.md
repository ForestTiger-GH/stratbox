# Business domains

Source-specific business logic lives under `stratbox.domains.<publisher>`.
Functional owners contain substantive publication families and statistical series.

Publishers are `cbr`, `fns`, `frank_rg`, `minfin`, and `rosstat`. Publications,
documents, tables, integration, analytics and products have independent
responsibilities; operation facades compose them explicitly.

Canonical source and profile declarations live under `domains.registry`;
operation declarations and their immutable catalog live under `operations`.
Supplied source workflows in `composition.builtins` connect independent stages
and share the same session executor as user-defined scenarios.
Handlers and lightweight request/result types live in the owning publisher's
functional packages. Registry admission verifies their ownership and exact
contract identities. Python package nesting alone creates no operation owner.

[Independent processing and replay](../../../docs/current-how/independent-domain-data-routes.md)

The domain-layer structure is independent of storage taxonomy: original
publications, normalized datasets and views may use different classifications.
Source-specific geography, observation periods and publication layouts remain
in the owning domain. Shared statistical contracts and neutral execution/storage
logic belong to `shared` and `core` respectively.

[Functional ownership and semantic invariants](../../../docs/architecture/domain-functional-semantics.md)
