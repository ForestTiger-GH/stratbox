# Execution facts and causal observation

The execution service journals accepted outputs, scope outcomes, physical work and effects with run, scope, attempt and command identities. Physical reuse retains independent logical scopes. Observers consume factual events and may project progress; journal truth is the notification input.

`MemoryJournal` provides bounded retention with explicit exhaustion. `FileJournal` stores fsynced records in numbered segments and supports bounded cursor reads and restart. The file provider is a single-writer implementation; applications needing distributed ownership supply an appropriate journal provider.

A failed optional observer does not change a business result. Missing required journal coverage remains visible and prevents claims that depend on those facts. Byte bodies and credentials do not belong in event summaries.

Each journal has a stream identity. A persistent journal restores it after restart. Notification cursors bind to that identity and reject a fresh stream with overlapping sequence numbers. File reads bound both returned records and scanned records; missing or corrupt segments remain explicit failures.
