# CBR file collector

Discover the fixed-file selection derived from the common CBR publication
registry, retain explicitly selected originals, and prepare a manifest-bearing
ZIP in memory or directly through a receiving file store.

`collect_materials` accepts per-item inline payloads, pinned references from
independently selected stores, or explicit HTTP routes. It returns exact original
artifacts and the shared `CollectionManifest`, including a disposition for every
selected item. Historical coverage remains independent of batch completion.

The common material and dataset operations choose storage destinations. Logical
series/issue/asset identities and member hashes remain independent of paths.

[CBR collection and replay routes](../../../../../docs/current-how/cbr-data-pipeline.md)

[Contracts and operations](../../../../../docs/current-how/universal-business-core.md)
