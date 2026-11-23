# Shared semantic owners

The `stratbox.shared` package defines reusable identities, evidence, statistical data contracts, reference data and calendar semantics. It has no execution, network transport, filesystem effects, user interface or domain-specific source parsing.

- `identifiers.py`: bounded logical identifiers.
- `identity.py`: immutable byte identity and canonical manifest serialization.
- `evidence.py`: source materials, acquisition and effect receipts, used-input lineage.
- `data/`: observation facts, processing roles and named ports, dataset and computation versions, representations, release comparisons and table identities.
- `reference/`: deterministic, offline, integrity-checked editions and named-reference resolution for banks, OKVED2 and geography.
- `time/`: calendar period anchor generation.

The dependency direction is `identity → evidence → data`; reference components may use these contracts, while `data` does not require concrete reference packages. Consumers choose and record reference editions explicitly. See [current contracts](../../../docs/current-how/shared-semantic-contracts.md) and [ownership](../../../docs/architecture/shared-ownership.md).
