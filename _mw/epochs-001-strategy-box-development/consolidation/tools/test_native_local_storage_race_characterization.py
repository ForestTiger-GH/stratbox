#!/usr/bin/env python3
"""POSIX-local storage failure characterization for proposed Artifact/FRG ports.

This test uses *actual temporary filesystem bytes and syscalls* on Linux CI;
it neither executes the installed Windows backend nor grants production
staging, approval, atomic CAS, crash durability or remote storage semantics.

Experiments intentionally exploit vulnerable stat/resolve/open/replace
sequences under controlled adversarial mutation inside one temp directory.
"""
from __future__ import annotations

import errno
import hashlib
import json
import os
import tempfile
from pathlib import Path


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def characterize() -> dict:
    cases = {}

    with tempfile.TemporaryDirectory(prefix="stratbox-file-race-") as td:
        base = Path(td)
        root = base / "workspace"
        other = base / "outside"
        root.mkdir()
        other.mkdir()

        # TOCTOU: a root-containment check of a string is not a capability.
        candidate = root / "input.bin"
        candidate.write_bytes(b"safe-contained-bytes")
        outside = other / "private.bin"
        outside.write_bytes(b"private-outside-workspace")
        assert candidate.resolve().is_relative_to(root.resolve())
        candidate.unlink()
        candidate.symlink_to(outside)
        assert candidate.read_bytes() == b"private-outside-workspace"
        cases["preopen_path_containment_can_be_invalidated"] = True

        # POSIX single-final-component O_NOFOLLOW refuses this exact symlink
        # without resolving arbitrary parent directory components.
        directory_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            try:
                os.open("input.bin", os.O_RDONLY | os.O_NOFOLLOW,
                        dir_fd=directory_fd)
            except OSError as exc:
                assert exc.errno == errno.ELOOP, exc
            else:
                raise AssertionError("O_NOFOLLOW unexpectedly opened outside bytes")
        finally:
            os.close(directory_fd)
        cases["single_final_component_nofollow_refusal"] = True

        # A write to an already-open inode can change the bytes while inode,
        # pathname, size and an earlier file descriptor remain identical.
        staging = root / "staging.bin"
        staging.write_bytes(b"AAAA")
        fd = os.open(staging, os.O_RDWR)
        try:
            old = os.fstat(fd)
            initial_digest = sha(os.pread(fd, 4, 0))
            assert initial_digest == sha(b"AAAA")
            writer = os.open(staging, os.O_WRONLY)
            try:
                assert os.pwrite(writer, b"BBBB", 0) == 4
            finally:
                os.close(writer)
            changed = os.fstat(fd)
            assert (old.st_ino, old.st_dev, old.st_size) == (
                changed.st_ino, changed.st_dev, changed.st_size)
            assert sha(os.pread(fd, 4, 0)) != initial_digest
        finally:
            os.close(fd)
        cases["open_fd_and_inode_do_not_ensure_immutable_bytes"] = True

        # Digest-before-validator and path-based finalize are three separate
        # observations unless a *real* backend generations/bytes fence exists.
        seal_candidate = root / "two-reads.bin"
        seal_candidate.write_bytes(b"1111")
        first_digest = sha(seal_candidate.read_bytes())
        seal_candidate.write_bytes(b"2222")
        second_digest = sha(seal_candidate.read_bytes())
        assert first_digest != second_digest
        cases["unfenced_repeated_staging_reads_disagree"] = True

        # A caller's target-generation precheck and os.replace() are not one
        # compare-and-swap, even when the staging generation itself is safe.
        target = root / "published.xlsx"
        staged = root / "intended.xlsx"
        target.write_bytes(b"old-report")
        staged.write_bytes(b"new-report")
        prechecked = sha(target.read_bytes())
        target.write_bytes(b"other-writer-report")
        assert sha(target.read_bytes()) != prechecked
        os.replace(staged, target)
        assert target.read_bytes() == b"new-report"
        assert not staged.exists()
        cases["plain_replace_clobbers_a_changed_target"] = True

        # On this local POSIX backend, hard-link create-only finalization is
        # genuinely no-clobber *for a destination pathname*. It is NOT an
        # immutable content seal nor a durable/recoverable catalog transaction.
        create_only_staging = root / "create-only-staging.bin"
        create_only_target = root / "create-only-output.bin"
        create_only_staging.write_bytes(b"staged-new-report")
        create_only_target.write_bytes(b"concurrent-winner")
        try:
            os.link(create_only_staging, create_only_target)
        except FileExistsError:
            pass
        else:
            raise AssertionError("create-only publication overwrote a winner")
        assert create_only_target.read_bytes() == b"concurrent-winner"
        cases["posix_link_create_only_rejects_collision"] = True

        # Same primitive can create a new name if none existed, within a
        # controlled local test. It provides no crash fsync or Windows proof.
        fresh_target = root / "fresh-output.bin"
        os.link(create_only_staging, fresh_target)
        assert fresh_target.read_bytes() == b"staged-new-report"
        cases["posix_link_create_only_adds_fresh_name"] = True

        # A source re-observation with the same bytes but later clock is not
        # itself a source-generation change; content still needs independent
        generation/byte verification.
        v = sha(create_only_staging.read_bytes())
        assert v == sha(fresh_target.read_bytes())
        cases["same_bytes_different_observation_time_remain_equal"] = True

    assert len(cases) == 8
    return {
        "status": "BOUND_TO_POSIX_NATIVE_LOCAL_TEMPORARY_FILES",
        "cases": cases,
        "passed": len(cases),
        "scope": "Linux CI ordinary local FS, real OS syscalls, injected races",
        "not_proved": [
            "Windows NTFS, SMB, remote object storage or AppDock installed runtime",
            "cross-process producer identity, reliable lock leases, authenticated approval",
            "power-loss durability, fsync guarantees, database-catalog atomicity",
            "universal safe relative-path traversal or mutation under untrusted OS principal",
            "production Strategy Box artifact or FRG cleanup implementability",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(characterize(), indent=2, ensure_ascii=False))
