# Single-node, multiuser execution and collaboration — source-unit extraction

**Original:** `SB-SRC-0036`, complete Research L1–L2585, blob `fb8ffe1b13f5c8718b171e6c7ad3d8a0f06948df` from pinned `stratbox@8459dc58922b7e8df853cf1d9e8131fa9e132580`. 36 provisional meaning units: `units/BASE-STUDY-0036.jsonl`. Master census source identity and blob unchanged; only `read_state=full_read`; full conservation remains `unaccounted`.

## Current implementation and product-meaning gap

The Windows application has Cases with authors, operational Events, participant projection, assignments, artifacts, logs, a background status store and five JSON history files. These are **local client-side objects** with selected projection affordances. A current node-wide execution authority, real presence across sessions, transactional multiuser event stream and centralized authorization were **not** proven by this static baseline. A UI showing incoming/outgoing cards is not proof of a network-shared timeline. The Windows coordinator's single-active-run guard is local to its own GUI process; it does not stop a second GUI process from concurrently writing the same shared output path.

The study proposes a common node as operational boundary, distinct session/participant identities, shared Cases/Jobs/automation, append-only ordered activities, per-user read cursors, scoped notifications, resource claims and authenticated/authorized commands. A separate host repository or one particular persistence technology is **not** implied by this conceptual allocation.

## High-consequence negative evidence and alternative explanations

1. A shared Data root does not make application state transactional: two independent JSON writers may diverge or overwrite, and external manual Excel changes remain outside application-lease guarantees.
2. Global `unread: bool` belongs neither in shared event truth nor in another user's preference. A per-user cursor/receipt maintains individual reading state while one source event retains stable identity.
3. Multiple sessions can belong to the same participant; one ephemeral online flag in a local model does not establish node-wide presence.
4. A path to an artifact on one Windows device is not a portable content identifier for remote/mobile consumers. Artifact metadata, byte materialization, lineage and authorization are different responsibilities.
5. A shared failure may merit a permission-filtered resource/node condition; a private validation error must not broadcast technical traceback to every user.
6. A GUI process exiting and a Job actually finishing are different observations only under a verified independent Job authority. Worker death may leave effects `OUTCOME_UNKNOWN`.
7. SQLite WAL on local node storage is a conditional implementation alternative. Hosting a WAL database directly on a network-shared Data root is not an established multi-node collaboration guarantee.
8. No separate full-featured chat/messenger, distributed cluster scheduler, client-side shared-state copying, or independent background-only execution engine is justified without an actual consumer need.

## Authority and target status

The proposed NodeActivityEvent/NodeCommand/Job/ArtifactRef fields and nine-stage development sequence are illustrative Research; Product Decisions on deployment, ACL, retention, concurrency, mobile scope and operating profile remain necessary. Actual AppDock capabilities must be revalidated through direct versioned external contracts. The study's `125` numbered concerns/testing conditions are **candidate tests**, not performed testing or adopted policy.

**Assurance:** fully read source and its 36 provisional source-unit uses; independent semantic conservation and primary evidence checks for all unit roles remain open, as do external contract assurance, public-security review and Research Amputation.

**Next authorized work:** scoped cross-theme synthesis for the already-read execution/automation/commands/multiuser Research cohort, with one-to-many source lineages and incompatible assumptions expressly preserved before any maintained Science/Target revision.
