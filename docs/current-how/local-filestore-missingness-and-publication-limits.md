# Local storage and publication guarantees

`LocalFileStore(root)` confines explicit paths to its configured root. Create-only writes establish immutable objects, while compare-and-set writes require the expected current content token. Both return concrete receipts checked by the effect boundary.

A missing disk input is a missing input; acquisition occurs only in an explicitly prepared acquisition route. Immutable member references are verified before a release manifest is published. Compare-and-set of a pointer alone cannot preserve mutable member bytes.

The local provider documents filesystem-specific guarantees. Distributed durability, cross-process ownership and recipient delivery require corresponding host providers and evidence.
