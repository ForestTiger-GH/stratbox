# Frank RG archives

Archive construction belongs to the common material commands. Frank RG supplies
recognized source/issue identity and a canonical destination name. An archive
contains selected exact originals; numerical interpretation is a separate route.

1. Use `command.material.list`, `command.publication.scan` and
   `command.issue.select` to identify a bounded selection.
2. Read selected asset locators with `command.material.read`.
3. Assign each selected material an explicit archive member name derived from
   the asset's `metadata["canonical_filename"]`.
4. Call `command.archive.pack` with the `members` input.
5. Preserve its returned `material` with the common artifact storage command
   at a caller-selected destination.

`command.archive.pack` owns safe member paths, unique membership, byte
verification and transfer limits. Its output retains member identities and
lineage. Selecting all files in the delivered directory establishes completeness
of that supplied selection, rather than a complete publisher archive.

The command's current value contract returns an in-memory material. A provider
implementation that needs a staged streaming destination must expose its actual
bounded transfer and commit guarantees through the common storage contract.
The domain has no separate streaming executor.

Packaging never performs cleanup. See
[explicit maintenance](frg-cleanup-effects.md) for the distinct effectful route.
