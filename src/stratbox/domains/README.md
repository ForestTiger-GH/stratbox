# Business domains

Each direct package owns its domain operations and publishes a `registration.py`.
`registry.py` discovers these registrations and combines them with system-owned operations.
Domain internals remain independently evolvable.
