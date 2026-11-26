# Factual journal streams

`JournalFact` identifies the run, logical scope, command, physical work and
outcome data of an observed transition. `MemoryJournal` retains a bounded stream;
`FileJournal` uses segmented durable storage with sequence validation.

Read facts with their stream and cursor context. A filtered selection and a
complete scanned interval carry different evidence. Notification preparation
must preserve that distinction when advancing its cursor.

The [execution service](../../execution/) publishes these facts.
[Notification state](../../notifications/) consumes them through an explicit
preparation action. See [notification consumption](../../../../../docs/current-how/notifications.md).
