# Reference assets and content identities

A reference family owns one flat `_resources/manifest.json` containing `reference_id`, assets and provenance. Every asset declares a role, relative path, media type, SHA256 and byte count. Required roles are validated independently of the manifest. Paths stay within the family resource root.

`load_reference('stratbox.shared.reference.geography')` returns a verified reference. Its `snapshot_identity` hashes the actual manifest and declared resource identities. `input_receipts()` records the exact asset and `content_basis`. There are no selectable component releases or active-edition pointers.

To update a source, review the publisher material, replace the asset and update its factual manifest entry in the same repository commit. Run `python scripts/reference_assets.py --reference all`, the relevant interpretation tests and the distribution checks. Wheel and source archive inspection compares exact packaged resource bytes with the source tree.

A reference resolves only its declared meaning: a display alias does not establish bank identity; a territory label does not establish an economic perimeter; an industry hierarchy does not establish a source-specific aggregation.
