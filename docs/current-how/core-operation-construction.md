# Core operation construction

**Scope and status.** The execution, data and provider interfaces below
describe the implemented Stratbox 0.9 library boundary. Application queues,
RPC and durable outboxes remain consumer design concerns.

```python
PARSE = OperationDefinition(
    "cbr.offices.parse", 1, "cbr-offices-html-1",
    ParseOfficesRequest, ParsedRelease,
)

def parse(request: ParseOfficesRequest, *, context=None):
    return run(PARSE, request, _parse, context=context)
```

The method receives an `Invocation`. At the consuming boundary it registers
the SHA-256, byte length and role of the actual source. It returns a
domain value or raises a typed `OperationFailure`. For partial or uncertain
results it returns `Completion` with a diagnostic. The runner supplies
identity, safe events and outcome checks.

A provider-dependent operation declares the required capability and passes
the explicitly supplied provider to `run`. An effectful operation declares
its effect types and records per-attempt outcomes. Source validators and
comparators belong next to the domain entry point. Reusable byte and format
commands belong in `base`.

[Runtime contracts](universal-business-core.md)
