"""Temporary live-byte accounting follows actual conditional file truncation."""
import pytest

from stratbox.core.storage.staged_values import StagedValueStore


@pytest.mark.parametrize("invalid", [-1, 1.5, "1", True])
def test_invalid_truncate_does_not_change_the_stage_or_its_quota(tmp_path, invalid):
    store = StagedValueStore(directory=tmp_path, max_bytes=8)
    try:
        with store.builder("writer") as writer:
            writer.write(b"four")
            with pytest.raises(ValueError, match="stage.truncate_size_invalid"):
                writer.truncate(invalid)
            assert store.status()["live_bytes"] == 4
            writer.seek(0)
            assert writer.read(8) == b"four"
        assert store.status()["live_bytes"] == store.status()["objects"] == 0
    finally:
        store.close()


@pytest.mark.parametrize("target,mutated,expected", [(8, False, 4), (8, True, 8), (2, True, 2)])
def test_failed_truncate_observes_actual_size_including_mutation_before_error(tmp_path, target, mutated, expected):
    store = StagedValueStore(directory=tmp_path, max_bytes=12)
    try:
        with store.builder("writer") as writer:
            writer.write(b"four")
            underlying = writer._file

            class TruncateFault:
                def truncate(self, size):
                    if mutated:
                        underlying.truncate(size)
                    raise OSError("Truncation acknowledgement unavailable")

                def __getattr__(self, name):
                    return getattr(underlying, name)

            writer._file = TruncateFault()
            with pytest.raises(OSError, match="acknowledgement"):
                writer.truncate(target)
            assert store.status()["live_bytes"] == expected
            assert writer.seek(0, 2) == expected
        assert store.status()["objects"] == store.status()["live_bytes"] == 0
    finally:
        store.close()


def test_uncommitted_shrink_cannot_lend_capacity_to_another_writer(tmp_path):
    store = StagedValueStore(directory=tmp_path, max_bytes=8)
    try:
        with store.builder("first") as writer:
            writer.write(b"four")
            underlying = writer._file

            class TruncateFault:
                def truncate(self, size):
                    with store.builder("second") as other:
                        with pytest.raises(ValueError, match="stage.byte_limit"):
                            other.write(b"fives")
                    raise OSError("Shrink failed before mutation")

                def __getattr__(self, name):
                    return getattr(underlying, name)

            writer._file = TruncateFault()
            with pytest.raises(OSError, match="Shrink failed"):
                writer.truncate(2)
            assert store.status()["live_bytes"] == 4
            assert store.status()["objects"] == 1
        assert store.status()["objects"] == 0
    finally:
        store.close()


def test_extension_quota_rejection_precedes_file_mutation(tmp_path):
    store = StagedValueStore(directory=tmp_path, max_bytes=6)
    try:
        with store.builder("writer") as writer:
            writer.write(b"four")
            with pytest.raises(ValueError, match="stage.byte_limit"):
                writer.truncate(8)
            assert store.status()["live_bytes"] == 4
            writer.seek(0)
            assert writer.read(8) == b"four"
    finally:
        store.close()
