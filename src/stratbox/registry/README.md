# Canonical registry resources

Owner directories separate logical source declarations, complete operation
contracts and profile bindings. Records use the JSON subset of YAML.

`core.registry` owns resource loading, schema/ownership checks, catalog assembly
and discovery. `core.execution` binds actual values to source routes and invokes
registered operations. Typed publication rules, reviewed layouts and algorithms
remain with their domain or neutral-core implementation owner.

[Registry API and extension route](../../../docs/current-how/domain-operation-registry.md)
