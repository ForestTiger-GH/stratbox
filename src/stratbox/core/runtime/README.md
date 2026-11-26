# Runtime providers and optional dependencies

Runtime bindings select technical implementations by declared role and readiness.
[Provider contracts](capabilities.py) own that selection boundary;
[provider discovery](providers.py) supplies configured or local implementations.

Optional numerical and format libraries are loaded through
[dependency admission](dependencies.py) at the operation that needs them.
Applications configure providers and their environment; domain catalogs retain
only source facts and method settings.

See [the SDK](../../sdk/) for supplying providers to an execution service.
