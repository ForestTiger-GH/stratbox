"""Measure a finite local profile with deterministic offline source revisions.

Run an installed checkout, for example:
    python scripts/probe_persistent_profile.py --cycles 120

The probe creates and removes only an owned temporary child of --root (or the
system temporary directory). It uses no live endpoints. Measurements qualify
this physical acquisition/retention/recovery workload in the reported runtime;
they do not establish scientific interpretation or power-loss guarantees.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
import sqlite3
import sys
import tempfile
import time

from stratbox import __version__
from stratbox.core.network.contracts import HttpResponse, HttpStreamResponse
from stratbox.core.observability.journal.stream import FileJournal
from stratbox.core.recovery import restore_recovery_package, validate_recovery_package
from stratbox.core.storage.readable import scan_identity
from stratbox.sdk import LocalProfile, PersistentLimits
from stratbox.shared.data.materials import RetainedRepresentation
from stratbox.shared.data.values import ByteIdentity, RequestSpec


SOURCE = "probe.rolling"
PAGE_LIMIT = 32
MAX_PAGES = 16


class OfflinePublisher:
    """A deterministic conditional HTTP adapter with bounded writes."""
    def __init__(self, payload_bytes):
        self.payload_bytes = payload_bytes
        self.cycle = self.revision = 0
        self.counts = {"200": 0, "304": 0}
        self.bytes_sent = 0

    @property
    def body(self):
        block = sha256(f"fixture-revision-{self.revision}".encode()).digest()
        return (block * ((self.payload_bytes + len(block) - 1) // len(block)))[:self.payload_bytes]

    def exchange_into(self, request, sink, *, cancelled):
        body = self.body
        etag = '"' + sha256(body).hexdigest() + '"'
        headers = {str(key).lower(): value for key, value in request.headers.items()}
        status = 304 if headers.get("if-none-match") == etag else 200
        outgoing = b"" if status == 304 else body
        for offset in range(0, len(outgoing), 65536):
            if cancelled():
                raise RuntimeError("probe.cancelled")
            sink.write(outgoing[offset:offset + 65536])
        self.counts[str(status)] += 1
        self.bytes_sent += len(outgoing)
        response = HttpResponse(status, b"", {"etag": etag, "content-type": "application/octet-stream"},
            datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=self.cycle),
            "https://fixture.example/", target_sha256=sha256(request.url.encode()).hexdigest(), wire_size=len(outgoing))
        return HttpStreamResponse(response, ByteIdentity.of(outgoing))

    def exchange(self, *args, **kwargs):
        raise AssertionError("The persistent probe requires the streaming HTTP entrance")


def _retained(reference, evidence):
    return RetainedRepresentation(reference, evidence.representation_identity,
        {key: value for key, value in evidence.headers.items() if key in {"etag", "last-modified"}},
        evidence.observed_at, request_identity=evidence.request_identity, evidence=evidence)


def _tree_bytes(root):
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file()) if root.exists() else 0


def probe(cycles=120, *, root=None, payload_bytes=4096):
    if type(cycles) is not int or not 4 <= cycles <= 10000:
        raise ValueError("probe.cycles_must_be_between_4_and_10000")
    if type(payload_bytes) is not int or not 1 <= payload_bytes <= 4 * 1024**2:
        raise ValueError("probe.payload_must_be_between_1_byte_and_4_MiB")
    started = time.perf_counter()
    publisher = OfflinePublisher(payload_bytes)
    split = cycles // 2
    maxima = {"hot_records": 0, "hot_bytes": 0, "archive_records": 0, "archive_bytes": 0,
        "state_physical_bytes": 0, "profile_directory_bytes": 0, "artifact_directory_bytes": 0,
        "effect_hot_receipts": 0, "effect_archived_receipts": 0}
    counts = {"maintenance_calls": 0, "retired_current": 0, "archived_records": 0,
        "discarded_records": 0, "archived_effect_receipts": 0, "cursor_checks": 0,
        "journal_prune_requests": 0, "restarts": 0}
    checks = {"all_commands_succeeded": True, "latest_observation_and_output_preserved": True,
        "page_limits_respected": True, "projection_cursors_exact": True,
        "recovery_package_verified": False, "restored_projection_equal": False,
        "restored_limits_equal": False, "restored_receipt_confirmed": False,
        "artifact_bytes_verified": False, "original_writer_closed": False,
        "prior_effect_namespace_fenced": False}
    limits = PersistentLimits(min_free_bytes=0, projection_reserve_records=8,
        projection_reserve_bytes=1024**2,
        source_state={"max_records": 128, "max_bytes": 16 * 1024**2,
            "max_record_bytes": 1024**2, "max_archive_records": 512, "max_archive_bytes": 64 * 1024**2},
        effects={"max_hot_receipts": 32, "max_hot_bytes": 8 * 1024**2, "max_receipt_bytes": 128 * 1024},
        journal={"segment_size": 32})
    phase_seconds = {}
    with tempfile.TemporaryDirectory(prefix="stratbox-profile-probe-", dir=root) as directory:
        temporary = Path(directory)
        live, artifacts, package = temporary / "live", temporary / "artifacts", temporary / "recovery"
        retained = latest_reference = latest_state = None
        stream_id = None

        def sample(profile):
            usage = profile.usage()
            state = usage["source_state"]
            for name in ("hot_records", "hot_bytes", "archive_records", "archive_bytes"):
                maxima[name] = max(maxima[name], state[name])
            maxima["state_physical_bytes"] = max(maxima["state_physical_bytes"], sum(state["physical_bytes"].values()))
            maxima["profile_directory_bytes"] = max(maxima["profile_directory_bytes"], _tree_bytes(live))
            maxima["artifact_directory_bytes"] = max(maxima["artifact_directory_bytes"], _tree_bytes(artifacts))
            maxima["effect_hot_receipts"] = max(maxima["effect_hot_receipts"], usage["effects"]["hot_receipts"])
            metadata = profile.providers["effect_state"].recovery_metadata()
            maxima["effect_archived_receipts"] = max(maxima["effect_archived_receipts"], metadata["archived_count"])
            return usage

        def maintain(profile, *, disposition, retired=(), prune=False):
            tail = profile.journal.checkpoint().tail
            result = profile.maintain(disposition=disposition, through=tail,
                max_pages=MAX_PAGES, page_limit=PAGE_LIMIT,
                retire_current_accepted_ids=retired, retire_persistent=True,
                prune_through=tail if prune else None)
            counts["maintenance_calls"] += 1
            counts["journal_prune_requests"] += int(prune)
            counts["archived_effect_receipts"] += result["effect_receipts_archived"]
            for report in result["projection"]:
                work = report.retired_current + report.records + report.authority + report.retention_links
                if work > PAGE_LIMIT:
                    raise AssertionError("A source-state maintenance page exceeded its work bound")
                counts["retired_current"] += report.retired_current
                counts["archived_records" if disposition == "archive" else "discarded_records"] += report.records
            if result["projection"][-1].has_more:
                raise AssertionError("The declared finite fixture exceeded its maintenance-page envelope")
            checkpoint = profile.providers["source_state"].checkpoint(profile.journal.stream_id)
            journal = profile.journal.checkpoint()
            if checkpoint.applied_through != journal.tail or journal.consumers["source-state"] != journal.tail:
                raise AssertionError("Source projection and protected journal consumer disagree at the cut")
            counts["cursor_checks"] += 1
            return result

        for phase, bounds in (("unchanged", (0, split)), ("changing", (split, cycles))):
            phase_started = time.perf_counter()
            with LocalProfile(live, artifact_root=artifacts, limits=limits, providers={"http": publisher}) as profile:
                if stream_id is not None:
                    counts["restarts"] += 1
                    if profile.journal.stream_id != stream_id:
                        raise AssertionError("A cold profile reopen changed its journal stream")
                stream_id = profile.journal.stream_id
                for cycle in range(*bounds):
                    publisher.cycle = cycle
                    publisher.revision = 0 if cycle < split else cycle - split + 1
                    request = RequestSpec("https://fixture.example/rolling.bin", source_id=SOURCE,
                        observation_id=f"poll-{cycle}", max_bytes=payload_bytes)
                    inputs = {"request": request, "destination": "originals"}
                    if retained is not None:
                        inputs["retained"] = retained
                    with profile.box.invoke("command.material.receive", inputs=inputs) as result:
                        if result.outcome != "succeeded":
                            raise AssertionError((cycle, result.outcome, result.diagnostics))
                        latest_reference, evidence = result.output("reference"), result.output("evidence")
                        retained = _retained(latest_reference, evidence)
                    profile.box.advance_source_state(max_pages=MAX_PAGES, page_limit=PAGE_LIMIT)
                    state = profile.providers["source_state"].read((SOURCE,), stream_id=stream_id)
                    outputs = tuple(value for value in state.outputs if value.stage == "raw")
                    if not outputs:
                        raise AssertionError("The accepted receive did not create a current raw entrance")
                    wanted = max(outputs, key=lambda value: value.sequence).accepted_value_id
                    obsolete = tuple(value.accepted_value_id for value in outputs if value.accepted_value_id != wanted)
                    sample(profile)
                    maintain(profile, disposition="discard" if (cycle + 1) % 5 == 0 else "archive",
                        retired=obsolete, prune=(cycle + 1) % 10 == 0)
                    latest_state = profile.providers["source_state"].read((SOURCE,), stream_id=stream_id)
                    if (not latest_state.complete or len(latest_state.outputs) != 1
                            or latest_state.outputs[0].accepted_value_id != wanted
                            or len(latest_state.observations) != 1
                            or latest_state.observations[0].observation_id != f"poll-{cycle}"):
                        raise AssertionError("Maintenance changed the selected current source/output")
                    sample(profile)
                if phase == "changing":
                    maintain(profile, disposition="discard", prune=True)
                    latest_state = profile.providers["source_state"].read((SOURCE,), stream_id=stream_id)
                    history = profile.providers["source_state"].read((SOURCE,), stream_id=stream_id, view="history")
                    if history.complete or not history.history_retained_after:
                        raise AssertionError("Explicit history retirement was reported as full historical coverage")
                    final_usage = sample(profile)
                    final_cursors = {"tail": final_usage["journal"].tail,
                        "retained_after": final_usage["journal"].retained_after,
                        "applied_through": latest_state.checkpoint.applied_through,
                        "history_retained_after": latest_state.history_retained_after}
                    if not final_cursors["retained_after"]:
                        raise AssertionError("The probe did not exercise acknowledged journal pruning")
                    providers = {role: profile.providers[role] for role in ("filestore", "datasets")}
                    backup_started = time.perf_counter()
                    manifest = profile.export_recovery(package)
                    verified = validate_recovery_package(package)
                    if verified["package_id"] != manifest["package_id"]:
                        raise AssertionError("Recovery package verification changed its identity")
                    checks["recovery_package_verified"] = True
                    phase_seconds["export_and_verify"] = time.perf_counter() - backup_started
            phase_seconds[phase] = time.perf_counter() - phase_started

        restore_started = time.perf_counter()
        restored = restore_recovery_package(package, temporary / "restored", providers=providers)
        try:
            restored_state = restored["providers"]["source_state"]
            snapshot = restored_state.read((SOURCE,), stream_id=stream_id)
            checks["restored_projection_equal"] = snapshot == latest_state
            checks["restored_limits_equal"] = restored_state.recovery_metadata()["limits"] == dict(limits.source_state)
            effects = restored["providers"]["effect_state"]
            checks["restored_receipt_confirmed"] = effects.get(latest_reference.effect_id).status == "confirmed"
            checks["prior_effect_namespace_fenced"] = effects.recovery_metadata()["namespace_state"] == "closed"
            with providers["filestore"].open_read(latest_reference.location) as stream:
                checks["artifact_bytes_verified"] = scan_identity(stream) == latest_reference.identity
            with FileJournal(live / "journal") as prior:
                try:
                    prior.append(kind="probe.forbidden_old_writer", run_id="closed-owner")
                except RuntimeError as error:
                    checks["original_writer_closed"] = "writer_namespace_closed" in str(error)
                else:
                    raise AssertionError("The previous journal writer remained authorized after restore")
        finally:
            restored["providers"]["source_state"].close()
            restored["journal"].close()
        phase_seconds["restore_and_verify"] = time.perf_counter() - restore_started
        if not all(checks.values()):
            raise AssertionError({key: value for key, value in checks.items() if not value})
        if publisher.counts["200"] != cycles - split + 1 or publisher.counts["304"] != split - 1:
            raise AssertionError("Conditional retrieval did not follow the fixture's known revisions")
        return {"environment": {"core_version": __version__, "python": platform.python_version(),
                "implementation": platform.python_implementation(), "platform": platform.platform(),
                "sqlite": sqlite3.sqlite_version, "scope": "local_single_coordinator_offline_physical_route"},
            "workload": {"cycles": cycles, "unchanged_cycles": split, "changing_cycles": cycles - split,
                "payload_bytes": payload_bytes, "maintenance_page_limit": PAGE_LIMIT,
                "maintenance_max_pages": MAX_PAGES, "retirement": "explicit_host_selected_accepted_ids"},
            "http": {**publisher.counts, "body_bytes_transferred": publisher.bytes_sent},
            "counts": counts, "maxima": maxima, "final_cursors": final_cursors,
            "final_state": {key: final_usage["source_state"][key] for key in
                ("hot_records", "hot_bytes", "archive_records", "archive_bytes")},
            "recovery": {"files": manifest["files"], "bytes": manifest["bytes"],
                "dependencies": manifest["dependencies"], "dependency_bytes": manifest["dependency_bytes"]},
            "seconds": {**{key: round(value, 4) for key, value in phase_seconds.items()},
                "total": round(time.perf_counter() - started, 4)}, "checks": checks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycles", type=int, default=120)
    parser.add_argument("--payload-bytes", type=int, default=4096)
    parser.add_argument("--root", type=Path, help="Existing parent for the probe's owned temporary directory")
    arguments = parser.parse_args()
    if arguments.root is not None and not arguments.root.is_dir():
        parser.error("--root must name an existing directory")
    try:
        result = probe(arguments.cycles, root=arguments.root, payload_bytes=arguments.payload_bytes)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
