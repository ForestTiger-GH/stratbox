# CBR publication identity and original access

Logical families are declared in the parent `REGISTRY_*.yaml` files. This owner
loads those declarations, binds official access profiles, discovers and selects
publication instances, admits originals and assesses observed updates. It also
owns named collection selections and complete source-disposition manifests.

Family subdirectories contain publication-specific discovery and release rules.
Parser, model, presentation and destination policies have independent owners.
Exact operation bindings are maintained in `operations/bindings.py`.

[CBR routes](../../../../../docs/current-how/cbr-data-pipeline.md)
