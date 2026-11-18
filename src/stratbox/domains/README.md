# Business domains

Each direct package owns its domain operations and publishes a `registration.py`.
`registry.py` discovers these registrations and combines them with system-owned operations.
Domain internals remain independently evolvable. Publisher-specific region names,
period rules, statistics and layout perimeters are interpreted by their domain.
Shared reference names may provide read-only diagnostics, not automatic source
key replacement, aggregate reconstruction or a change to literal exports.
