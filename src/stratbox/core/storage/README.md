# Retained materials and datasets

Storage separates exact byte retention from semantic dataset ingestion.
[Filestore providers](filestore/) implement file access and conditional mutation;
[dataset providers](datasets/) ingest and query typed observations.

The standard artifact commands retain encoded materials under immutable content
identities. Dataset commands accept actual datasets. Publication pointers,
maintenance and uncertain write acknowledgements use explicit effectful actions
through the execution service.

Bounded byte and staging primitives support these operations. Domain methods
prepare data or presentation content; storage providers own the external write.

See [storage and publication limits](../../../../docs/current-how/local-filestore-missingness-and-publication-limits.md)
and [dataset retention](../../../../docs/current-how/logical-dataset-snapshots.md).
