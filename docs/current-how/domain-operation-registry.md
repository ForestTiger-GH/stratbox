# Domain operation registration and machine dispatch

Stratbox separates source-specific business implementations from the neutral
operation execution catalog. An exact `_registration.py` file establishes an
operation owner. Publication families, processing layers and operation modules
describe different responsibilities. CBR registers its whole operation surface
under the single root owner `cbr`.

## 1. Discover and resolve operations

```python
from stratbox.domains.registry import domain_catalog, operation_catalog

business = domain_catalog()                  # all installed source-domain operations
catalog = operation_catalog()                # domain operations and neutral core
references = catalog.list_refs()
descriptions = catalog.describe()             # definitions and schemas, no handlers
definition = catalog.get("frg.plan_cleanup", 1)
definition, handler, codec = catalog.resolve("frg.plan_cleanup", 1)
```

The domain catalog rejects missing intermediate `__init__.py` files for
manifest-bearing directories. The catalog and registration inventory are views
of the same validated owner snapshot, so a malformed hierarchy never silently
drops a manifest. A logical operation ID belongs to exactly one owner across
all of its declared contract versions. Its discovery algorithm is shared with the
static layout check and the distribution verifier. The source, wheel and
sdist manifest/data inventories are compared without a fixed owner count.
All manifest bytes and packaged non-code data assets are checked by size and SHA-256,
including future asset formats without per-file allowlists.
The domain catalog traverses installed Python packages under `stratbox.domains`
in deterministic order using `importlib.resources.files`. It discovers only
exact files named `_registration.py` and never searches arbitrary underscore
modules or external directories. Grouping and implementation-only packages
need no manifest. A broken existing manifest raises `RegistryError`.

Each declaration is an `OperationRegistration` with a dotted `owner_id`
relative to `stratbox.domains`. Its `OperationRef` entries reference an
`OperationDefinition`, its callable handler and optional machine contract/codec by
fully qualified Python module and symbol name.

The registry validates all module references against the **nearest registered
owner**. The discovery mechanism permits nested owners when a domain explicitly
declares that boundary; a nested implementation package alone creates no owner.
It rejects ambiguous
ownership, mismatched owner IDs and duplicate (operation ID, contract version)
pairs. Executable definitions, handlers and codecs are still resolved lazily by
`OperationCatalog`. Creating a catalog performs no source HTTP requests,
file capture, scheduling or destination effects.

## 2. Register a publisher or extend an existing owner

For a new publisher owner, create normal Python packages with `__init__.py`,
for example `stratbox.domains.example_publisher` and its `operations` package.
Add `_registration.py` **only** to the package owning operations:

```python
from stratbox.core.execution.catalog import OperationRef, OperationRegistration

REGISTRATION = OperationRegistration(
    owner_id="example_publisher",
    operations=(
        OperationRef(
            "example_publisher.parse", 1,
            "stratbox.domains.example_publisher.operations.definitions:PARSE",
            "stratbox.domains.example_publisher.operations.handlers:parse",
        ),
    ),
)
```

Typed operation definitions stay in lightweight `definitions.py` modules.
Executable methods import these definitions into their handler modules. A business
source catalog separately describes publications and processing profiles; it is
distinct from the operation manifest. Cross-domain discovery requires no central
publisher or operation allowlist. Each owner can explicitly compose its functional
segments and maintain its own business registries. Grouping packages remain lightweight.
Public owner package exports are lazily loaded so metadata listing does not
require optional spreadsheet or solver engines.

For an existing CBR segment, keep the root owner `cbr`. Add operation definitions
and handlers under `stratbox.domains.cbr.operations.<segment>`, export their
`OperationRef` entries from the segment's `registration.py`, and include that
segment in the root `_registration.py` composition. Keep its lifecycle declarations
alongside its operation references. Creating a new CBR family or source requires
the relevant publication, acquisition, layout and semantic bindings; it does not
require a child `_registration.py`.

CBR separates `publications`, `tables`, `integration`, `analytics`, `products`
and `operations`. Corporate debt and issuance have separate contracts and
operations under `operations.corporate_lending.debt` and
`operations.corporate_lending.issuance`; both belong to root `cbr`. Source parsing
helpers live in the table layer, shared semantic interpretation in integration,
calculations in analytics, and prepared views/rendering in products. Reporting
forms, service-network statistics, project finance and generic statistical
workbooks follow the same functional boundaries.

Registered domain owners are `cbr`, `minfin`, `frank_rg`, `rosstat` and `fns`.
Their business catalogs can subdivide sources without multiplying operation
owners. Use CBR's `describe_source` and `describe_family` operations for
source-scoped coverage; the root owner's aggregate stages describe its combined
surface. The shared `catalog.source_catalog()` interface covers all five
publishers with the same source/profile/operation binding shape. See the
[CBR route guide](cbr-data-pipeline.md) and
[independent publisher routes](independent-domain-data-routes.md).

## 3. Restricted read-only machine calls

```python
from stratbox.domains.registry import operation_catalog
from stratbox.core.execution.machine import invoke_read_only, wire_schemas

catalog = operation_catalog()
schema, response_schema = wire_schemas("cbr.offices.parse", 1, catalog=catalog)
```

Machine read-only admission remains limited to `cbr.offices.parse` v1,
`cbr.offices.compare` v2 and `frg.plan_cleanup` v1. Their codecs live with
their respective owner; immutable schemas live separately in `machine_contracts.py`.
Machine admission never grants authorization for
network, storage, deletion or publication side effects.

Hosts that already hold validated typed requests can additionally use
`invoke_reference` with a host-owned `TypedValueResolver`. This interface applies
the actual registered definition and explicit effect grants, reserves result
capacity before execution, and returns typed result/value handles plus a bounded
preview. It supplies no arbitrary object deserializer or destination authority.
See [machine access](independent-domain-data-routes.md#7-machine-access).

Logical operation IDs and versions are independent of Python module paths.
The new module topology is canonical; no historical import aliases are
provided.

[Processing roles, bounded catalog discovery and qualified stage connections](processing-operation-catalog.md)
