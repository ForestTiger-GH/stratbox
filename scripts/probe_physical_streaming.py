"""Measure one bounded physical-byte SDK route using isolated temporary files.

Run with an installed checkout, for example:
    python scripts/probe_physical_streaming.py --size-mib 128

The optional --root is an existing parent directory for an owned temporary child.
The probe never reads, overwrites, or removes caller files in that parent.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack, contextmanager
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
import time

from stratbox.core.execution.service import ExecutionSettings
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.sdk import StrategyBox
from stratbox.shared.identity import ByteIdentity


CHUNK_BYTES = 1024 * 1024
RETAINED_RAM_BYTES = 2 * CHUNK_BYTES


def _peak_rss_bytes():
    try:
        import resource
    except ImportError:
        return None
    amount = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(amount if sys.platform == "darwin" else amount * 1024)


class _BoundedFile:
    def __init__(self, stream, metrics):
        self.stream, self.metrics = stream, metrics

    def read(self, size=-1):
        if size < 0:
            position = self.stream.tell()
            size = self.stream.seek(0, 2) - position
            self.stream.seek(position)
        if not 0 <= size <= CHUNK_BYTES:
            raise AssertionError(f"Unbounded provider read: {size}")
        self.metrics["max_provider_read_request"] = max(self.metrics["max_provider_read_request"], size)
        result = self.stream.read(size)
        self.metrics["provider_bytes_read"] += len(result)
        return result

    def write(self, data):
        if len(data) > CHUNK_BYTES:
            raise AssertionError(f"Unbounded provider write: {len(data)}")
        self.metrics["max_provider_write_chunk"] = max(self.metrics["max_provider_write_chunk"], len(data))
        amount = self.stream.write(data)
        self.metrics["provider_bytes_written"] += amount
        return amount

    def __getattr__(self, name):
        return getattr(self.stream, name)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stream.close()


class _StreamingOnlyStore(LocalFileStore):
    def __init__(self, root, metrics):
        super().__init__(root)
        self.metrics = metrics

    def open_read(self, path):
        return _BoundedFile(super().open_read(path), self.metrics)

    def read_bytes(self, path):
        raise AssertionError("A whole-file read API was used")

    def create_immutable(self, path, data):
        raise AssertionError("A whole-file write API was used")

    @contextmanager
    def stage_content(self, directory):
        with super().stage_content(directory) as stage:
            class Bounded:
                stream = _BoundedFile(stage.stream, self.metrics)

                def location(self, identity):
                    return stage.location(identity)

                def commit(self, identity, **kwargs):
                    return stage.commit(identity, **kwargs)

            yield Bounded()


def probe(size_mib, root=None):
    """Return observed results; throughput and RSS are environment-specific."""
    source_bytes = size_mib * CHUNK_BYTES
    metrics = {"max_provider_read_request": 0, "max_provider_write_chunk": 0,
               "provider_bytes_read": 0, "provider_bytes_written": 0}
    stages = []
    with tempfile.TemporaryDirectory(prefix="stratbox-stream-probe-", dir=root) as directory:
        path = Path(directory) / "source.bin"
        block = bytes(range(256)) * (CHUNK_BYTES // 256)
        digest = sha256()
        with path.open("wb") as stream:
            for _ in range(size_mib):
                stream.write(block)
                digest.update(block)
        del block
        identity = ByteIdentity(digest.hexdigest(), source_bytes)
        store = _StreamingOnlyStore(Path(directory), metrics)
        with StrategyBox(providers={"filestore": store},
                         settings=ExecutionSettings(max_retained_bytes=RETAINED_RAM_BYTES,
                             staging_directory=directory)) as box, ExitStack() as results:
            baseline = _peak_rss_bytes()
            started = time.perf_counter()

            def invoke(command, *, inputs, parameters=None, output=None):
                stamp = time.perf_counter()
                result = results.enter_context(box.invoke(command, inputs=inputs, parameters=parameters or {}))
                stages.append({"command": command, "seconds": round(time.perf_counter() - stamp, 4),
                               "outcome": result.outcome})
                if result.outcome != "succeeded":
                    raise AssertionError((command, result.outcome, result.diagnostics))
                return result.output(output) if output else result

            source_result = invoke("command.material.read", inputs={"location": {"path": path.name, "identity": identity}},
                                   parameters={"placement": "staged"})
            source = source_result.output("material")
            # Only this probe's generated fixture is removed. The sealed stage
            # is now the owner used by the rest of the measured route.
            path.unlink()
            archive = invoke("command.archive.pack", inputs={"members": (source,)},
                             parameters={"placement": "staged", "compression": "stored", "names": (path.name,)},
                             output="material")
            source_result.close()
            committed = invoke("command.artifact.commit", inputs={"material": archive, "destination": "objects"})
            reference = committed.output("reference")
            invoke("command.release.assemble", inputs={"members": (reference,)}, output="manifest")
            assessment = invoke("command.artifact.reconcile", inputs={"effect": committed.output("receipt")}, output="assessment")
            if not assessment.complete:
                raise AssertionError("Exact retained-byte reconciliation remained incomplete")
            peak = _peak_rss_bytes()
            return {"source_bytes": source_bytes, "archive_bytes": reference.identity.size,
                    "service_retained_ram_limit_bytes": RETAINED_RAM_BYTES,
                    "peak_rss_before_bytes": baseline, "peak_rss_after_bytes": peak,
                    "peak_rss_delta_bytes": peak - baseline if peak is not None and baseline is not None else None,
                    "elapsed_seconds": round(time.perf_counter() - started, 4),
                    "receipt_status": committed.output("receipt").status,
                    "reconciliation_complete": assessment.complete, "stages": stages, **metrics}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size-mib", type=int, default=128, help="Generated input size in MiB (default: 128)")
    parser.add_argument("--root", type=Path, help="Existing directory containing the isolated temporary child")
    options = parser.parse_args()
    if options.size_mib < 1:
        parser.error("--size-mib must be positive")
    if options.root is not None and not options.root.is_dir():
        parser.error("--root must name an existing directory")
    print(json.dumps(probe(options.size_mib, options.root), indent=2))


if __name__ == "__main__":
    main()
