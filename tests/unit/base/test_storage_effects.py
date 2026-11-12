from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from threading import Barrier

from stratbox.base.filestore import LocalFileStore
from stratbox.base.ioapi.bytes import write_verified_bytes
from stratbox.data import ByteIdentity


def test_immutable_write_serializes_competing_contents(tmp_path):
    store = LocalFileStore(root=str(tmp_path))
    barrier = Barrier(2)

    def write(data):
        barrier.wait()
        return write_verified_bytes(
            "artifact.bin",
            data,
            store=store,
            expected_sha256=ByteIdentity.of(data).sha256,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(write, (b"one", b"two")))
    assert sorted(item.status for item in results) == ["failed", "stored"]
    current = store.read_bytes("artifact.bin")
    assert (
        write_verified_bytes(
            "artifact.bin",
            current,
            store=store,
            expected_sha256=ByteIdentity.of(current).sha256,
        ).status
        == "already_present"
    )


def test_read_back_mismatch_and_lost_acknowledgement_are_uncertain():
    class Store:
        def __init__(self, *, lost_ack):
            self.lost_ack = lost_ack
            self.calls = 0

        def create_if_absent(self, path, data):
            self.calls += 1
            if self.lost_ack:
                raise ConnectionError("lost acknowledgement")
            return True

        def open_read(self, path):
            return BytesIO(b"bad")

    digest = ByteIdentity.of(b"yes").sha256
    store = Store(lost_ack=False)
    assert (
        write_verified_bytes(
            "x", b"yes", store=store, expected_sha256=digest
        ).diagnostic_code
        == "effect.read_back_mismatch"
    )
    lost = Store(lost_ack=True)
    assert (
        write_verified_bytes("x", b"yes", store=lost, expected_sha256=digest).status
        == "unknown"
    )
    assert lost.calls == 1
    assert (
        write_verified_bytes(
            "x", b"yes", store=object(), expected_sha256=digest
        ).diagnostic_code
        == "provider.capability_missing"
    )
    bad = write_verified_bytes("x", b"no", store=lost, expected_sha256=digest)
    assert bad.diagnostic_code == "input.digest_mismatch"
    assert lost.calls == 1
