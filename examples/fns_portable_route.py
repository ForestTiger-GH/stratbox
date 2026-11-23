"""Offline FNS route with independent original, snapshot and artifact storage.

Example:
    python examples/fns_portable_route.py sme source.json 2026-11-10 ./fns-output
    python examples/fns_portable_route.py legal_entities source.zip 2026-11-01 ./fns-output

Install the appropriate spreadsheet extras for workbook input or XLSX output.
The destination can be a local directory or an already mounted network path.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path

from stratbox.core.operations.materials.definitions import ArtifactDestination, SaveArtifactRequest
from stratbox.core.operations.materials.operations import save_artifact
from stratbox.core.operations.source.original_definitions import OriginalDestination, SaveOriginalRequest
from stratbox.core.operations.source.originals import save_original
from stratbox.core.storage.datasets import FileDatasetStore
from stratbox.core.storage.datasets.definitions import ReadSnapshotRequest, WriteSnapshotRequest
from stratbox.core.storage.datasets.operations import read_snapshot, write_snapshot
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.domains.fns.operations import legal_entities, sme
from stratbox.shared.evidence import SourcePayload


def require_value(result):
    if result.outcome != "succeeded":
        raise RuntimeError(f"{result.operation_id}: {[item.code for item in result.diagnostics]}")
    return result.value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("family", choices=("sme", "legal_entities"))
    parser.add_argument("source", type=Path)
    parser.add_argument("as_of", type=date.fromisoformat)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--issue-id")
    parser.add_argument("--published-on", type=date.fromisoformat)
    parser.add_argument("--captured-at", type=datetime.fromisoformat,
                        help="Known acquisition timestamp with a timezone; omit when unavailable")
    parser.add_argument("--format", choices=("csv", "json", "jsonl", "xlsx"), default="csv")
    args = parser.parse_args(argv)
    operations = sme if args.family == "sme" else legal_entities
    series = "fns.sme" if args.family == "sme" else "fns.1yur"
    limit = 4_000_000 if args.family == "sme" else 30_000_000
    with args.source.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("The source exceeds this family's admitted byte limit")
    payload = SourcePayload(data, "application/json" if args.family == "sme" else "application/octet-stream", series)
    release = operations.ReleaseContext(series, args.issue_id or args.as_of.isoformat(), args.as_of,
        published_on=args.published_on, captured_at=args.captured_at)
    files = LocalFileStore(root=str(args.destination.resolve()))
    datasets = FileDatasetStore(files, "datasets", provider_id="example.files", scope_id="fns")

    original = require_value(save_original(SaveOriginalRequest(payload,
        OriginalDestination("originals/" + payload.identity.sha256 + ".bin")), store=files))
    processed = require_value(operations.process(operations.ProcessRequest(payload, release, args.format)))
    references = {}
    for layer, value, request_type in (
        ("flake", processed.flake, operations.FlakeRequest),
        ("projection", processed.projection, operations.ProjectionRequest),
        ("dataset", processed.dataset, operations.DatasetRequest),
        ("view", processed.view, operations.ViewValueRequest),
    ):
        snapshot = require_value(getattr(operations, layer + "_snapshot")(request_type(value)))
        saved = require_value(write_snapshot(WriteSnapshotRequest(snapshot), store=datasets))
        references[layer] = saved.reference

    # Presentation resumes from the retained view; no original is opened here.
    retained = require_value(read_snapshot(ReadSnapshotRequest(references["view"]), store=datasets))
    view = require_value(operations.read_view_snapshot(operations.SnapshotRequest(retained)))
    artifact = require_value(operations.render_artifact(operations.RenderRequest(view, args.format)))
    artifact_path = "exports/" + artifact.identity.sha256 + "." + args.format
    saved_artifact = require_value(save_artifact(SaveArtifactRequest(artifact, ArtifactDestination(artifact_path)), store=files))
    print("Original:", original.material.identity.sha256)
    for layer, reference in references.items():
        print(layer + ":", reference.dataset_id, reference.version_id, reference.identity.sha256)
    print("Artifact:", saved_artifact.artifact.identity.sha256, artifact_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
