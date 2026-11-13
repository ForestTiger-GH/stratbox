# Core operation boundaries

Stratbox 0.11 combines reusable technical commands with independently callable
domain operations. A consumer binds providers and composes operations for
its own publication, analysis or archive workflow.

| Owner | Responsibilities |
| --- | --- |
| `base.net` | Typed HTTP request, response, failures, admission, streaming limits and bounded retries. |
| `base.filestore`, `base.ioapi` | File and directory commands, bounded reads, verified writes, archive and format primitives. |
| `data` | Payloads, byte identities, used-input and effect evidence, representations, table snapshots and canonical computation manifests. |
| `execution` | Operation definition, context, validation, stage events, original acquisition and replay, cancellation and outcomes. |
| `catalog` | Discovery of the owner definitions and explicit codecs for selected read-only operations. |
| Domain modules | Official source parameters, interpretation, period semantics, calculations, comparisons and presentation profiles. |
| Consumer | Selection and repetition of dates, scheduling, paths, permissions, publication, durable history and delivery state. |

Providers are parameters to the operations that use them. `local_providers()`
constructs independent local adapters. An offline operation can run with
just its typed inputs. The package roots import with the standard library.
Analytical and format dependencies are selected by the operations that use
them.

A composition such as `capture` has one invocation. The operation uses the
same parsing method as `parse`, and its result identifies the source bytes.
Consumers can instead archive the original immediately, parse later, or
request only a representation.

| Identifier | Owned by |
| --- | --- |
| Package version | Installed distribution |
| Contract version | Public request, value and result contract |
| Method version | Domain rule, calculation or representation |
| Invocation ID | One library operation |
| Run, step and attempt | Calling application |
| Release version | Input bytes, source method and output manifest |
| Effect key | One authorized destination transition |

[Implemented API and evidence limits](../current-how/universal-business-core.md)
