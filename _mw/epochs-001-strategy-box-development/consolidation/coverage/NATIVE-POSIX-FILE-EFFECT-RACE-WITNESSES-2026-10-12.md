# Native POSIX storage race witnesses for Artifact and FRG LCD boundaries

**Date:** 2026-10-12. **Grade:** `PRODUCER_EXECUTED_LINUX_NATIVE_NEGATIVE_CHARACTERIZATION`. This is stronger than an in-memory fake for the **specific POSIX syscalls exercised**, but weaker than actual Strategy Box storage adapter conformance. No Windows/NTFS/SMB, installed host, real authorization, power-loss testing, shared catalog or remote BlobStore was involved.

**Scientific owners:** `docs/science/artifacts/output-identity-publication-and-availability.md`, `docs/science/data-and-knowledge/frg-file-selection-cleanup-and-effects.md`. **Construction owners:** `docs/lcd/artifacts/local-output-publication-construction.md`, `docs/lcd/application/frg-cleanup-effect-plan-construction.md`. **Research grounding:** previously read `SB-SRC-0557` (artifact publication, L447–L516), `SB-SRC-0558` (host effect-time authorization) and the pinned current FRG cleanup implementation `SB-SRC-0278`; all separately distinguished preview, mutable file bytes, approved plan, pending physical effect and committed available output.

## Actual performed physical tests

`_mw/epochs-001-strategy-box-development/consolidation/tools/test_native_local_storage_race_characterization.py` creates a temporary ordinary local filesystem tree in Ubuntu GitHub Actions, injects controlled mutations and calls actual Python `os`/POSIX system operations:

| # | Controlled physical experiment | Observed proof and its limit |
| --- | --- | --- |
| NFS-01 | Check a path's resolved containment, then swap the file for a symlink before opening | A **prior** `Path.resolve().is_relative_to(root)` check passes but a later `read_bytes()` follows the symlink outside the chosen workspace. The outside file is a synthetic fixture *within* the disposable test root; no real private data touched. |
| NFS-02 | With an opened parent directory FD, open the final symlink component using `O_NOFOLLOW` | Linux refuses with `ELOOP`; positive narrow evidence for **this single final component**, not arbitrary ancestor traversal or Windows handle semantics. |
| NFS-03 | Open staging FD then alter same inode and byte count using another write FD | Same `st_dev/st_ino/st_size` yet SHA differs. Open FD/inode equality is **not** a byte immutability seal. |
| NFS-04 | Hash staged file, rewrite bytes, read again | Digests differ across two ordinary path reads. A `StagingSeal` needs backend enforcement; a Python dataclass is insufficient. |
| NFS-05 | Preinspect existing destination, inject competing writer, then `os.replace(staging,target)` | `os.replace` overwrites the changed destination without checking its prevalidated generation. It is an atomic rename in some filesystem contexts, **not** an expected-target CAS. |
| NFS-06 | Use POSIX `os.link` to create target already occupied by another writer | `FileExistsError`; existing destination remains intact: a useful limited **no-clobber/create-only** mechanism on this profile, not a generic safe overwrite. |
| NFS-07 | Link staged file to a previously unoccupied target | A fresh name is materialized with expected bytes. Does **not** prove crash durability, immutability of shared inode, auth or catalog ACID transaction. |
| NFS-08 | Compare unchanged payload bytes despite a separate later observation | Byte identity remains equal. Time-of-observation is evidence context but **not** a payload generation. |

**Exact CI:** [Actions 38221344760](https://github.com/ForestTiger-GH/stratbox/actions/runs/38221344760), `stratbox@ee40ca1794c3d3b5409df55110b92a9b43b953b6`, **SUCCESS**, eight native POSIX cases. The earlier workflow revision `1cfbaff1cb5e248c2f5bbe0c1d82adb99064b4d1` had a **Python syntax failure** in a comment, corrected before claiming native execution. This note cites only the passing run for behavior evidence. Test does not touch production files.

## Engineering significance and explicit stop

The Artifact LCD's `StagingSeal` **requires** an adapter to bind *digest/validator/finalize* to the exact same byte generation; an opened FD, inode identifier or mtime does not prove immutable bytes. Physical capability choices include copied immutable staging ownership, rigorously scoped OS permissions/handles and conditional object-store generation operations. These are alternatives requiring profile-specific testing and security/operations authority. In FRG, a source precheck cannot authorize `os.remove` after the pathname target changes; a real compare-and-delete effect must reject stale generations, including symlink/alias attacks according to the actual host storage model. `os.link` demonstrates only a create-only possibility under Linux, not an approved universal publication strategy.

**Unresolved mandatory owner decisions:** actual Windows/NTFS or SMB backend capability; replacement semantics, version retention and conflict policy; durable record/catalog after crash; resource authorization at effect, authenticated approval and allowed root; whether strict immutable output is required for a given Artifact; how large-file performance and staging lifetime are bounded. No `LCD_READY_FOR_IMPLEMENTATION`, `LOSSLESS_PASS` or independent assurance status is elevated by this native pilot.
