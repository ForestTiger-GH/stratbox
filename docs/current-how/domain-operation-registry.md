# Domain operation registration and machine dispatch

Stratbox exposes independent domain packages as `stratbox.domains.<name>`.
Each package owns its operations, type definitions and a small immutable
`registration.py` declaration. The central registry discovers these declarations
automatically, rather than maintaining a list of domain implementations.

## Discover and resolve operations

```python
from stratbox.domains.registry import domain_catalog, operation_catalog

business = domain_catalog()
catalog = operation_catalog()
references = catalog.list_refs()  # Lightweight operation references
descriptions = catalog.describe()  # Validated contracts and capabilities
definition = catalog.get('frg.plan_cleanup', 1)
definition, handler, machine_codec = catalog.resolve('frg.plan_cleanup', 1)
```

An `OperationRef` identifies the authoritative `OperationDefinition` and its
callable handler. Resolution checks the operation ID and contract version;
duplicates, missing handlers and invalid codec declarations fail explicitly.
Domain-specific Python APIs keep their own typed requests and provider parameters.

## Add a built-in domain

Create a direct package `stratbox/domains/<domain_name>/` containing an
`__init__.py`, the domain methods and `registration.py` with exactly one
`REGISTRATION = OperationRegistration(owner_id='<domain_name>', operations=(...))`.
Each `OperationRef` names an existing definition and the corresponding callable.
The central registry discovers the package without changes to a global method list.
Domain subseries remain inside their owner until a separate semantic refactor.

Only built-in packages are discovered. Arbitrary external Python packages and
untrusted paths are outside this discovery mechanism. Registration never schedules
work, reads files, contacts network endpoints or grants execution authority.
Neutral source and notification operations are declared under `stratbox.core.operations` and `stratbox.core.notifications`.

## Restricted read-only machine calls

```python
from stratbox.domains.registry import operation_catalog
from stratbox.core.execution.machine import invoke_read_only, wire_schemas

catalog = operation_catalog()
request_schema, result_schema = wire_schemas('cbr.offices.parse', 1, catalog=catalog)
# response = invoke_read_only(raw_bytes, catalog=catalog, materials=authorized_resolver)
```

Three operations initially admit machine calls: `cbr.offices.parse` v1,
`cbr.offices.compare` v2, and `frg.plan_cleanup` v1. Their narrow codecs
belong to their domains; `stratbox.core.execution.machine` owns the
bounded JSON parser, schema construction and generic invocation protocol.
All other operations remain direct Python APIs until explicitly admitted.

The caller supplies a trusted `MaterialResolver`, the invocation context
and provider bindings. A declared codec confers no permission to access
network, storage, secrets, or destination effects. Encoded responses contain
only the codec's declared fields and bounded structured diagnostics.

Logical operation IDs and versions are independent of Python package paths.
Reorganizing an individual domain later does not change the top-level
registration system.
