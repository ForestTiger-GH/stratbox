# Runtime providers and network transport

This guide describes the current public-neutral infrastructure in
`stratbox.core`. For the functional ownership rules see
[core operation boundaries](../architecture/core-operation-boundaries.md).

## Responsibility map

| Package | Responsibility |
| --- | --- |
| `stratbox.core.runtime.providers` | Composition and lookup of a provider bundle. |
| `stratbox.core.runtime.capabilities` | Versioned capability requirements and explicit provider bindings. |
| `stratbox.core.runtime.secrets` | Secret provider contract and local environment/prompt adapters. |
| `stratbox.core.storage.filestore` | Logical file-store ports and the local implementation. |
| `stratbox.core.storage.bytes` | Bounded reads and verified writes over a file-store port. |
| `stratbox.core.storage.staging` | Staged byte material and conditional writes. |
| `stratbox.core.network` | HTTPS request and response contracts, transport, routes and retries. |

The library does not own an application scheduler, presentation process or
host-specific authorization database. Those are supplied by the caller.

## Compose an explicit local provider bundle

```python
from stratbox.core.runtime.providers import Providers, local_providers
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.core.network import RequestsTransport
from stratbox.core.runtime.secrets import EnvSecretProvider

providers = local_providers(root="./data")
assert isinstance(providers.filestore, LocalFileStore)

# Individual operations also accept explicitly supplied adapters.
bundle = Providers(
    filestore=LocalFileStore("./data"),
    http=RequestsTransport(),
    secrets=EnvSecretProvider(prefix="STRATBOX_"),
)
```

`Providers` consists of `filestore`, `http`, `secrets` and an optional
callable `excel_styles` registry factory. No concrete host extension is
required by the public package.

`default_filestore(explicit_store)` and `default_secrets(explicit_provider)`
return their supplied argument first. With no argument, each obtains a
validated active provider bundle when one exists, or builds the designated
local adapter otherwise.

## Runtime discovery and ambiguity

`active_providers()` checks for one installed `default` entry point in the
`stratbox.runtime` group, or one matching sibling package factory under
the neutral `stratbox_*/_stratbox_runtime.py` convention. A sibling factory
is named `create_providers()` and returns a `Providers` instance.
Discovery validates the candidate count, module location, required methods
and optional style factory. Ambiguous or invalid composition fails with a
`RuntimeProviderError`; discovery results are cached for the process.

Importing `stratbox.core` by itself does not probe the environment,
create files or start network access. Provider discovery occurs through
explicit runtime access or an operation that requests a default adapter.

A managed operation uses `ExecutionContext` bindings. Each required
`ProviderBinding` is selected against a `CapabilityRequirement` with
its declared version, scope and guarantees. The bound accepting provider
must enforce its own authority, destination restrictions and effect
conditions. The core cannot infer those from Python object type.

## HTTP requests and transport

```python
from stratbox.core.network import (
    HttpRequest, HttpTransport, RequestsTransport, PeerBoundTransport,
    RoutedTransport, HttpsEndpoint, RetryPolicy, exchange,
)

transport: HttpTransport = RequestsTransport()
request = HttpRequest("https://example.org/observations.csv")
result = exchange(request, transport=transport)
```

`HttpRequest` validates method, endpoint, headers, payload limits,
redirection settings and response budgets. `exchange()` returns a
qualified response or a structured `HttpFailure`; `exchange_into()`
writes admitted response bytes to an explicit streaming sink. Retry
limits and request budgets are evaluated by the generic implementation,
rather than being hidden in domain-specific fetchers.

`PeerBoundTransport` adds numeric peer-address admission and checks the
established TLS hostname. `RoutedTransport` can separate a logical HTTPS
target from an explicitly configured HTTPS gateway; the resulting
receipt distinguishes logical and physical target qualifications. A
route must not imply upstream authenticity solely from TLS to the gateway.
A managed acquisition requires explicit transport accounting and
appropriate destination guarantees.

Built-in transport evidence uses stable semantic adapter family tokens:
`http.requests.v1`, `http.routed.v1` or `http.peer_bound.v1`.
Explicit capability provider IDs take precedence in request identity.
Custom unbound transport class names provide only a local fallback
identity; persistent proofs require an appropriate provider contract.

## File-store and byte-oriented operations

File operations consume `FileStore`, `SourceStore`, `StagedWriter`
and related abstract ports. The local implementation provides a
filesystem-backed option; other callers can bind alternative stores
without changing economic methods. Use the exact logical destination,
bounded byte read and expected revision or immutable creation mode
supported by the accepting store.

A successful write receipt is distinct from evidence that downstream
parsing or publication occurred. A write that may have taken effect but
lacks verified confirmation remains `unknown` and is reconciled using
the exact intended content identity. An immutable verified append is
never interpreted as an atomic multi-segment transaction.

Document and archive encoders live in `core.formats`; presentation
styles and spreadsheet views belong to `core.rendering`. Specialized
readers load optional dependencies only when their respective
operation is requested.

## Import boundaries and checks

The core accepts external adapters through neutral contracts. Its storage,
network and execution foundations do not import business domains,
notification consumers or specific application implementations.
The `shared` package owns canonical data semantics independently from
the executable core.

```sh
python -B scripts/check_internal_imports.py
python -B scripts/check_release_integrity.py
python -B -m pytest -q
```

This guide replaces a historically pinned description of an earlier
runtime implementation. Immutable source revisions remain available in
repository history; current Python paths and behavior are defined by the
code and maintained documentation on the active branch.
