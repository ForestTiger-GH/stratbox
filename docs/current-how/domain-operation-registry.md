# Domain operation registration and machine dispatch

Stratbox separates source-specific business implementations from the neutral
operation execution catalog. Source packages group publication families, while
an exact `_registration.py` file establishes an operation owner at any depth.

## 1. Discover and resolve operations

```python
from stratbox.domains.registry import domain_catalog, operation_catalog

business = domain_catalog()                  # 68 source-domain operations
catalog = operation_catalog()                # domain operations and neutral core
references = catalog.list_refs()
descriptions = catalog.describe()             # resolves executable contracts
definition = catalog.get("frg.plan_cleanup", 1)
definition, handler, codec = catalog.resolve("frg.plan_cleanup", 1)
```

The domain catalog traverses installed Python packages under `stratbox.domains`
in deterministic order using `importlib.resources.files`. It discovers only
exact files named `_registration.py` and never searches arbitrary underscore
modules or external directories. Grouping and implementation-only packages
need no manifest. A broken existing manifest raises `RegistryError`.

Each declaration is an `OperationRegistration` with a dotted `owner_id`
relative to `stratbox.domains`. Its `OperationRef` entries reference an
`OperationDefinition`, its callable handler and an optional machine codec by
fully qualified Python module and symbol name.

The registry validates all module references against the **nearest registered
owner**, including parent/child publication series. It rejects ambiguous
ownership, mismatched owner IDs and duplicate (operation ID, contract version)
pairs. Executable definitions, handlers and codecs are still resolved lazily by
`OperationCatalog`. Creating a catalog performs no source HTTP requests,
file capture, scheduling or destination effects.

## 2. Add a source or publication family

Create normal Python packages with `__init__.py` under a publisher namespace,
for example `stratbox.domains.cbr.new_family.series_a`. Add
`_registration.py` **only** to the exact package owning operations:

```python
from stratbox.core.execution.catalog import OperationRef, OperationRegistration

REGISTRATION = OperationRegistration(
    owner_id="cbr.new_family.series_a",
    operations=(
        OperationRef(
            "cbr.series_a.parse", 1,
            "stratbox.domains.cbr.new_family.series_a.operations:PARSE",
            "stratbox.domains.cbr.new_family.series_a.operations:parse",
        ),
    ),
)
```

Executable methods stay in `operations.py` or `api.py`. A business source
registry may separately use `registry.py` for publication definitions; that
file is **not** the operation manifest. No global list of publishers, families,
or operations is maintained. Parent grouping packages should remain lightweight.
Public owner package exports are lazily loaded so metadata listing does not
require optional spreadsheet or solver engines.

The current owners include `cbr`, `fns` and `frank_rg` publisher branches.
The industry parent owns nine `01_05_A` operations; the nested
`industries.issuance_0104` owns eight `01_04_A` operations. All 68 original
logical operation IDs and contract versions remain unchanged by this relocation.

## 3. Restricted read-only machine calls

```python
from stratbox.domains.registry import operation_catalog
from stratbox.core.execution.machine import invoke_read_only, wire_schemas

catalog = operation_catalog()
schema, response_schema = wire_schemas("cbr.offices.parse", 1, catalog=catalog)
```

Machine read-only admission remains limited to `cbr.offices.parse` v1,
`cbr.offices.compare` v2 and `frg.plan_cleanup` v1. Their codecs live with
their respective owner. Machine admission never grants authorization for
network, storage, deletion or publication side effects.

Logical operation IDs and versions are independent of Python module paths.
The new module topology is canonical; no historical import aliases are
provided.
