#!/usr/bin/env python3
"""Behaviorally exercise exact *documented* LCD Python candidate fragments.

This Work-only test executes selected named AST nodes extracted from Markdown
with synthetic objects. It does NOT test any installed or product source.
Selection is allowlisted; never import full markdown or evaluate unrelated code.
It is a producer-authored executable design-probe, NOT independent assurance.
"""
from __future__ import annotations

import ast
import enum
import json
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[4]
LCD = ROOT / "docs/lcd"


def extract_python_chunks(path: Path) -> list[tuple[int, ast.Module]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    found: list[tuple[int, ast.Module]] = []
    block: list[str] = []
    start = 0
    for number, line in enumerate(lines, 1):
        if line.strip() == "~~~python":
            assert start == 0, f"nested Python fence at {path}:{number}"
            start = number
            block = []
        elif start and line.strip() == "~~~":
            found.append((start, ast.parse("\n".join(block))))
            start = 0
        elif start:
            block.append(line)
    assert start == 0, f"unclosed Python fence at {path}"
    return found


def compile_definition(relative: str, name: str, scope: dict) -> None:
    """Load only named top-level class/function/enum from a documented fence."""
    path = LCD / relative
    matches = []
    for start, module in extract_python_chunks(path):
        for node in module.body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
                matches.append((start, node))
    assert len(matches) == 1, (relative, name, len(matches))
    start, definition = matches[0]
    future = ast.ImportFrom(
        module="__future__", names=[ast.alias(name="annotations")], level=0)
    new_module = ast.fix_missing_locations(
        ast.Module(body=[future, definition], type_ignores=[]))
    exec(compile(new_module, f"{relative}:{start}", "exec"), scope, scope)


def probe_local_run() -> dict:
    d = {
        "Enum": enum.Enum, "Lock": threading.Lock, "uuid4": uuid.uuid4,
        "LocalCaseSnapshot": SimpleNamespace,
    }
    ref = "application/local-scenario-execution-construction.md"
    for name in ("CaseOutcome", "EffectCertainty", "AdmissionError",
                 "BusyLocalExecutor", "DispatchDefinitelyNotStarted",
                 "DispatchStatusUnknown", "LocalScenarioService",
                 "aggregate_outcome"):
        compile_definition(ref, name, d)

    def step(step_id: str, ok: bool, certainty: str):
        return SimpleNamespace(step_id=step_id, ok=ok,
                               effect_certainty=d["EffectCertainty"](certainty))

    plan = SimpleNamespace(
        steps=[SimpleNamespace(step_id="s1", required=True),
               SimpleNamespace(step_id="s2", required=False)]
    )
    agg = d["aggregate_outcome"]
    result = d["CaseOutcome"]
    assert agg(plan, (step("s1", True, "confirmed"),
                      step("s2", True, "confirmed"))) is result.SUCCESS
    assert agg(plan, (step("s1", False, "no_effect_asserted"),
                      step("s2", True, "confirmed"))) is result.FAILED
    assert agg(plan, (step("s1", True, "confirmed"),
                      step("s2", False, "no_effect_asserted"))) is result.WARNING
    assert agg(plan, (step("s1", False, "unknown"),)) is result.OUTCOME_UNKNOWN
    assert agg(plan, (step("s1", True, "confirmed"),)) is result.WARNING

    d["build_local_plan"] = lambda scenario, request, case_id, operation_registry: (
        SimpleNamespace(case_id=case_id, scenario_id=scenario.id))
    scenarios = SimpleNamespace(get=lambda name: SimpleNamespace(id=name))
    inv = SimpleNamespace(scenario_id="s", params={}, author_id="a")
    executor = SimpleNamespace(execute=lambda plan:
        SimpleNamespace(case_id=plan.case_id, scenario_id=plan.scenario_id,
                        outcome=result.SUCCESS))
    class Dispatcher:
        def __init__(self):
            self.last_callback = None
            self.mode = "ok"
        def start(self, callback):
            self.last_callback = callback
            if self.mode == "no-start":
                self.last_callback = None
                raise d["DispatchDefinitelyNotStarted"]()
            if self.mode == "ack-lost":
                raise RuntimeError("scheduled but acknowledgment lost")
    class Sink:
        def __init__(self):
            self.snapshots = []
            self.fail = False
        def update(self, outcome):
            self.snapshots.append(outcome)
            if self.fail:
                raise RuntimeError("projection failure")

    dis, sink = Dispatcher(), Sink()
    service = d["LocalScenarioService"](
        scenarios=scenarios, operations=SimpleNamespace(), executor=executor,
        dispatcher=dis, projections=sink)
    first = service.submit(inv)
    assert service._active_case_id == first
    try:
        service.submit(inv)
    except d["BusyLocalExecutor"]:
        pass
    else:
        raise AssertionError("second concurrent submit must be rejected")
    dis.last_callback()
    assert service._active_case_id is None

    dis.mode = "no-start"
    try:
        service.submit(inv)
    except d["AdmissionError"]:
        pass
    else:
        raise AssertionError("proven scheduling rejection was not reported")
    assert service._active_case_id is None

    dis.mode = "ack-lost"
    try:
        service.submit(inv)
    except d["DispatchStatusUnknown"] as exc:
        reserved = service._active_case_id
        assert reserved and str(exc) == reserved
    else:
        raise AssertionError("ambiguous scheduling ACK was not identified")
    try:
        service.submit(inv)
    except d["BusyLocalExecutor"]:
        pass
    else:
        raise AssertionError("ack-lost window admitted duplicate run")
    sink.fail = True
    dis.last_callback()
    assert service._active_case_id is None
    assert sink.snapshots[-1].outcome is result.SUCCESS
    # Concurrent Python submissions target the documented Lock, not native Qt.
    from concurrent.futures import ThreadPoolExecutor
    barrier = threading.Barrier(8)
    racing_dispatcher = Dispatcher()
    racing_dispatcher.mode = "ok"
    racing_service = d["LocalScenarioService"](
        scenarios=scenarios, operations=SimpleNamespace(), executor=executor,
        dispatcher=racing_dispatcher, projections=Sink())
    def racing_submit(_index):
        barrier.wait()
        try:
            return ("admitted", racing_service.submit(inv))
        except d["BusyLocalExecutor"]:
            return ("busy", None)
    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(racing_submit, range(8)))
    assert sum(status == "admitted" for status, _ in outcomes) == 1
    assert sum(status == "busy" for status, _ in outcomes) == 7
    assert racing_service._active_case_id is not None
    racing_dispatcher.last_callback()
    assert racing_service._active_case_id is None

    return {"result_algebra": 5, "single_flight_and_faults": 6,
            "synthetic_thread_race_submissions": 8,
            "evidence": "executed isolated doc-defined classes/functions with fakes"}


def probe_host_admission() -> dict:
    import hashlib
    from types import MappingProxyType
    ref = "hosting/host-authority-and-client-contract-construction.md"
    d = {"Enum": enum.Enum, "dataclass": dataclass}
    for name in ("AdmissionKind", "AdmissionReceipt", "Submission", "HostAdmission"):
        compile_definition(ref, name, d)
    kind, receipt = d["AdmissionKind"], d["AdmissionReceipt"]
    host = SimpleNamespace(host_id="host-1")
    actor = SimpleNamespace(principal_ref="p1", scope_ref="workspace-A")
    submission = d["Submission"]
    def request(key="intent", period="2026-07", client_claim="FORGED-SAME-DIGEST"):
        return submission(key, "bank.report", "revision-1",
                          {"period": period}, client_claim)

    class Canonicalizer:
        def __init__(self):
            self.calls = 0
            self.mutate_intent_key = False
        def seal(self, actor, untrusted):
            self.calls += 1
            if (not untrusted.intention_key or
                    set(untrusted.parameters) != {"period"} or
                    not isinstance(untrusted.parameters["period"], str)):
                raise ValueError("schema rejected")
            frozen = MappingProxyType(dict(untrusted.parameters))
            canonical = json.dumps(
                {"principal": actor.principal_ref, "scope": actor.scope_ref,
                 "scenario": untrusted.scenario_id,
                 "definition": untrusted.definition_revision,
                 "params": dict(frozen)},
                sort_keys=True, ensure_ascii=False, separators=(",", ":"))
            digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            key = ("forged-other-key" if self.mutate_intent_key
                   else untrusted.intention_key)
            return submission(key, untrusted.scenario_id,
                              untrusted.definition_revision, frozen, digest)

    class Policy:
        allow = True
        fault = False
        seen_digest = None
        def can_submit(self, actor, req):
            if self.fault:
                raise RuntimeError("policy service unavailable")
            self.seen_digest = req.payload_digest
            return self.allow

    class Ledger:
        def __init__(self):
            self.calls = 0
            self.seen = {}
            self.lose_ack_after_commit = False
            self.bad_mode = None
        def admit_atomically(self, actor, request, host):
            self.calls += 1
            if self.bad_mode == "null":
                return None
            if self.bad_mode == "wrong_key":
                return receipt(kind.ACCEPTED, "other-key", "run-stolen", host.host_id)
            if self.bad_mode == "wrong_host":
                return receipt(kind.ACCEPTED, request.intention_key,
                               "run-stolen", "other-host")
            if self.bad_mode == "accepted_no_run":
                return receipt(kind.ACCEPTED, request.intention_key, None, host.host_id)
            if self.bad_mode == "rejected_with_run":
                return receipt(kind.REJECTED, request.intention_key, "run-stolen", host.host_id)
            if self.bad_mode == "wrong_enum":
                return receipt("accepted", request.intention_key, "run-stolen", host.host_id)
            old = self.seen.get(request.intention_key)
            if old:
                digest, run = old
                return receipt(kind.REPLAY if digest == request.payload_digest
                               else kind.REJECTED, request.intention_key,
                               run if digest == request.payload_digest else None,
                               host.host_id)
            run = "run-1"
            self.seen[request.intention_key] = (request.payload_digest, run)
            if self.lose_ack_after_commit:
                raise TimeoutError("ledger committed Run, lost ACK")
            return receipt(kind.ACCEPTED, request.intention_key, run, host.host_id)

    class Scheduler:
        fail = True
        calls = 0
        def schedule(self, run_ref):
            self.calls += 1
            if self.fail:
                raise RuntimeError("lost ACK")

    policy, ledger, scheduler, canonicalizer = (
        Policy(), Ledger(), Scheduler(), Canonicalizer())
    svc = d["HostAdmission"](host, policy, ledger, scheduler, canonicalizer)
    req = request()
    first = svc.submit(actor, req)
    assert first.kind is kind.OUTCOME_UNKNOWN and first.run_ref == "run-1"
    assert policy.seen_digest != req.payload_digest
    assert ledger.seen["intent"][0] == policy.seen_digest
    replay = svc.submit(actor, req)
    assert replay.kind is kind.REPLAY and replay.run_ref == "run-1"
    assert scheduler.calls == 1
    # A client can assert one digest for two different payloads; the trusted
    # canonicalizer must make the ledger reject the second under the same key.
    conflict = svc.submit(actor, request(period="2026-08"))
    assert conflict.kind is kind.REJECTED
    scoped_actor = SimpleNamespace(principal_ref="p1", scope_ref="workspace-B")
    cross_scope_conflict = svc.submit(scoped_actor, req)
    assert cross_scope_conflict.kind is kind.REJECTED
    policy.allow = False
    denied = svc.submit(actor, request(key="different"))
    assert denied.kind is kind.REJECTED
    policy.allow = True
    policy.fault = True
    unknown = svc.submit(actor, request(key="different"))
    assert unknown.kind is kind.OUTCOME_UNKNOWN and unknown.run_ref is None
    policy.fault = False

    calls_before_invalid = ledger.calls
    invalid_schema = submission("invalid-schema", "bank.report", "revision-1",
                                {"handler": "unregistered"}, "FORGED")
    assert svc.submit(actor, invalid_schema).kind is kind.REJECTED
    canonicalizer.mutate_intent_key = True
    assert svc.submit(actor, request(key="modified-key")).kind is kind.REJECTED
    canonicalizer.mutate_intent_key = False
    assert ledger.calls == calls_before_invalid

    ledger.lose_ack_after_commit = True
    second = request(key="intent-lost-ledger-ack")
    scheduled_before_ledger_ack_loss = scheduler.calls
    uncertain = svc.submit(actor, second)
    assert uncertain.kind is kind.OUTCOME_UNKNOWN and uncertain.run_ref is None
    qualified_hash = canonicalizer.seal(actor, second).payload_digest
    assert ledger.seen[second.intention_key] == (qualified_hash, "run-1")
    ledger.lose_ack_after_commit = False
    found = svc.submit(actor, second)
    assert found.kind is kind.REPLAY and found.run_ref == "run-1"
    # Liveness hole remains until persistent outbox/recovery exists.
    assert scheduler.calls == scheduled_before_ledger_ack_loss
    before = scheduler.calls
    for mode in ("null", "wrong_key", "wrong_host", "accepted_no_run",
                 "rejected_with_run", "wrong_enum"):
        ledger.bad_mode = mode
        result = svc.submit(actor, request(key="intent-malformed"))
        assert result.kind is kind.OUTCOME_UNKNOWN
        assert scheduler.calls == before
    ledger.bad_mode = None
    # Reuse this Host packet's existing probe group (do not inflate the
    # unique LCD document count) to qualify client-facing Artifact metadata.
    for name in ("ArtifactAvailability", "ArtifactIdentity",
                 "InternalArtifactRecord", "ArtifactResult", "ScopedReads"):
        compile_definition(ref, name, d)
    availability = d["ArtifactAvailability"]
    record_type = d["InternalArtifactRecord"]
    class ReadPolicy:
        permitted = True
        fail = False
        def can_fetch(self, actor, ref):
            if self.fail:
                raise RuntimeError("auth provider unreachable")
            return self.permitted
    class ArtifactRepo:
        fail = False
        current = record_type(availability.VERIFIED_AVAILABLE,
                              "sha256-safe", "application/vnd.report",
                              "/private/host/secret.xls")
        def resolve_verified(self, ref):
            if self.fail:
                raise IOError("synthetic backend temporarily unreachable")
            return self.current
    read_policy, repository = ReadPolicy(), ArtifactRepo()
    scoped = d["ScopedReads"](read_policy, ledger, repository,
                               SimpleNamespace(read_authorized=lambda *_: None))
    art = d["ArtifactIdentity"]("artifact-A", "rev-A")
    verified = scoped.fetch(actor, art)
    assert verified.availability is availability.VERIFIED_AVAILABLE
    assert verified.content_digest == "sha256-safe"
    assert not hasattr(verified, "host_handle")
    assert "/private/host" not in str(verified)
    read_policy.permitted = False
    denied = scoped.fetch(actor, art)
    assert denied.availability is availability.DENIED
    assert denied.content_digest is None and denied.media_type is None
    read_policy.permitted = True
    read_policy.fail = True
    assert scoped.fetch(actor, art).availability is availability.DENIED
    read_policy.fail = False
    repository.fail = True
    assert scoped.fetch(actor, art).availability is availability.BACKEND_UNAVAILABLE
    repository.fail = False
    repository.current = record_type(
        availability.VERIFIED_AVAILABLE, None, "application/vnd.report", "handle")
    assert scoped.fetch(actor, art).availability is availability.OUTCOME_UNKNOWN
    repository.current = record_type(
        availability.VERIFIED_AVAILABLE, "sha256-safe", "application/vnd.report", None)
    assert scoped.fetch(actor, art).availability is availability.OUTCOME_UNKNOWN
    repository.current = record_type(
        availability.MISSING_CONFIRMED, None, None, "/internal-only")
    missing = scoped.fetch(actor, art)
    assert missing.availability is availability.MISSING_CONFIRMED
    assert missing.content_digest is None
    repository.current = record_type(
        availability.CHANGED, "sha256-changed", "application/vnd.report", "/internal")
    changed = scoped.fetch(actor, art)
    assert changed.availability is availability.CHANGED
    assert changed.content_digest is None
    repository.current = None
    assert scoped.fetch(actor, art).availability is availability.OUTCOME_UNKNOWN
    repository.current = record_type(
        "verified_available", "sha256-safe", "application/vnd.report", "/internal")
    assert scoped.fetch(actor, art).availability is availability.OUTCOME_UNKNOWN
    return {"admission_duplicate_conflict_denial": 17,
            "client_forged_digest_ignored": True,
            "canonical_request_scope_bound": True,
            "client_safe_artifact_projection_cases": 10,
            "ledger_commit_without_dispatch_liveness_gap": "DEMONSTRATED_NOT_RESOLVED",
            "evidence": "literal HostAdmission and ScopedReads on fake ports; admission ACK gap strands a Run without an outbox, no real host/session/stream storage"}


def probe_authorized_host_feed() -> dict:
    """Execute candidate ScopedReads with a fake typed policy and safe feed."""
    ref = "hosting/host-authority-and-client-contract-construction.md"
    d = {"Enum": enum.Enum, "dataclass": dataclass}
    for name in ("RunPhase", "RunOutcome", "RunSnapshot",
                 "Observation", "ObservationPage", "ScopedReads"):
        compile_definition(ref, name, d)
    snapshot = d["RunSnapshot"]("run-A", 4, d["RunPhase"].RUNNING, None, False)
    observation = d["Observation"](
        "run-A", "visible-opaque-id", 4, "SOURCE_UNAVAILABLE", "Source unavailable")
    page_type = d["ObservationPage"]

    class Policy:
        permission, fail = True, False
        def can_read_run(self, actor, run_ref):
            if self.fail:
                raise IOError("policy down")
            return self.permission

    class Ledger:
        raw_reads = 0
        current = snapshot
        def get(self, run_ref):
            return self.current
        def read_after(self, *args):
            self.raw_reads += 1
            raise AssertionError("must not use raw ledger events")

    class Feed:
        mode = "valid"
        calls = 0
        def read_authorized(self, actor, run_ref, cursor):
            self.calls += 1
            if self.mode == "denied":
                raise PermissionError("hidden")
            if self.mode == "unavailable":
                raise IOError("backend unavailable")
            if self.mode == "wrong-run":
                return page_type("run-B", "acl-v4", None, (observation,))
            if self.mode == "raw-cursor":
                return page_type("run-A", "acl-v4", 35, (observation,))
            if self.mode == "untyped-event":
                return page_type("run-A", "acl-v4", None, ("secret",))
            if self.mode == "invalid-resync":
                return page_type("run-A", "acl-v4", None, (observation,), True)
            if self.mode == "resync":
                return page_type("run-A", "acl-v5", None, (), True)
            return page_type(run_ref, "acl-v4", "opaque-bound-cursor", (observation,))

    policy, ledger, feed = Policy(), Ledger(), Feed()
    reads = d["ScopedReads"](policy, ledger, SimpleNamespace(), feed)
    actor = SimpleNamespace(principal_ref="p", scope_ref="node-A")
    assert reads.read_run(actor, "run-A") == snapshot
    assert reads.observe(actor, "run-A", None).observations == (observation,)
    assert reads.observe(actor, "run-A", "opaque-bound-cursor").next_cursor
    for not_true in (False, "false", 1, None):
        policy.permission = not_true
        before = feed.calls
        try:
            reads.observe(actor, "run-A", None)
        except PermissionError:
            pass
        else:
            raise AssertionError("non-True permission granted")
        assert feed.calls == before
    from dataclasses import replace
    for bad_snapshot in (
        replace(snapshot, run_ref="private-other-run"),
        replace(snapshot, revision=-1),
        replace(snapshot, revision="4"),
        replace(snapshot, phase="running"),
        replace(snapshot, stale=1),
    ):
        ledger.current = bad_snapshot
        try:
            reads.read_run(actor, "run-A")
        except RuntimeError as exc:
            assert str(exc) == "RUN_SNAPSHOT_CONTRACT_INVALID"
        else:
            raise AssertionError("untyped or foreign Run snapshot accepted")
    ledger.current = snapshot
    assert not hasattr(reads.read_run(actor, "run-A"), "last_sequence")
    policy.permission, policy.fail = True, True
    try:
        reads.read_run(actor, "run-A")
    except PermissionError as exc:
        assert str(exc) == "RUN_ACCESS_UNCONFIRMED"
    else:
        raise AssertionError("policy outage did not deny")
    policy.fail = False
    for cursor in (35, "", True, {}):
        try:
            reads.observe(actor, "run-A", cursor)
        except ValueError:
            pass
        else:
            raise AssertionError("unscoped cursor accepted")
    for mode in ("wrong-run", "raw-cursor", "untyped-event", "invalid-resync"):
        feed.mode = mode
        try:
            reads.observe(actor, "run-A", None)
        except RuntimeError as exc:
            assert str(exc) == "AUTHORIZED_FEED_CONTRACT_INVALID"
        else:
            raise AssertionError("malformed projection accepted")
    feed.mode = "denied"
    try:
        reads.observe(actor, "run-A", None)
    except PermissionError:
        pass
    else:
        raise AssertionError("feed denied but leaked")
    feed.mode = "unavailable"
    try:
        reads.observe(actor, "run-A", None)
    except RuntimeError as exc:
        assert str(exc) == "AUTHORIZED_FEED_UNAVAILABLE"
    else:
        raise AssertionError("storage outage caused empty success")
    feed.mode = "resync"
    assert reads.observe(actor, "run-A", None).resync_required
    assert ledger.raw_reads == 0
    return {"authorized_feed_adverse_groups": 22,
            "raw_ledger_reads": ledger.raw_reads,
            "evidence": "literal ScopedReads/ObservationPage, synthetic feed; no native authenticated cursor or actual shared-node policy"}


def probe_problem_receipt() -> dict:
    ref = "observability/execution-evidence-and-problem-boundary-construction.md"
    d = {"Enum": enum.Enum, "dataclass": dataclass}
    for name in ("Audience", "RegistrationKind", "ProblemRegistration",
                 "OptionalProblemBridge"):
        compile_definition(ref, name, d)
    kind, receipt = d["RegistrationKind"], d["ProblemRegistration"]
    finding = SimpleNamespace(audience=d["Audience"].USER_SAFE)
    class Recorder:
        mode = "raise"
        def record(self, finding, key):
            if self.mode == "raise":
                raise RuntimeError("ack lost")
            if self.mode == "no-ref":
                return receipt(kind.ACKNOWLEDGED, key, None, "SOURCE_REPLY")
            return receipt(kind.ACKNOWLEDGED, key, "genuine-ref", "ACK")
    rec = Recorder()
    bridge = d["OptionalProblemBridge"](port=rec)
    lost = bridge.record(finding, "actual-intention-1")
    assert lost.kind is kind.OUTCOME_UNKNOWN
    assert lost.confirmed_external_ref is None
    assert lost.correlation_key == "actual-intention-1"
    rec.mode = "no-ref"
    no_ref = bridge.record(finding, "actual-intention-2")
    assert no_ref.kind is kind.OUTCOME_UNKNOWN
    rec.mode = "ack"
    confirmed = bridge.record(finding, "actual-intention-3")
    assert confirmed.kind is kind.ACKNOWLEDGED
    assert confirmed.confirmed_external_ref == "genuine-ref"
    missing = d["OptionalProblemBridge"](port=None).record(finding, "key")
    assert missing.kind is kind.UNAVAILABLE
    return {"unknown_and_confirmed_refs": 4,
            "evidence": "executed candidate Problem bridge against deterministic fake recorder"}


def probe_artifact_publication() -> dict:
    """Run a bounded subset of the exact documented publisher on in-memory bytes."""
    import hashlib
    from io import BytesIO

    ref = "artifacts/local-output-publication-construction.md"
    d = {"Enum": enum.Enum, "dataclass": dataclass, "hashlib": hashlib}
    for name in ("PublicationPhase", "ScopedLocator", "PublicationIntent",
                 "StagingSeal", "ByteReceipt", "PublicationReceipt",
                 "LocalOutputPublisher"):
        compile_definition(ref, name, d)
    phase = d["PublicationPhase"]
    receipt_type = d["ByteReceipt"]
    locator = d["ScopedLocator"]("workspace", "output/report.xlsx")
    intent = d["PublicationIntent"]("artifact", "generation-1", "run", "step",
                                   "actor", locator, "xlsx")
    class FakeWriter:
        def __init__(self):
            self.staging = {}
            self.current_generation = 1
            self.sealed_read_calls = 0
            self.final_bytes = None
            self.raise_after_commit = False
            self.corrupt_final = False
            self.mutate_after_first_sealed_read = False

        def create_unique_staging(self, intent):
            owner = self
            class CapturedStream(BytesIO):
                def close(self):
                    if not self.closed:
                        owner.staging["staging-1"] = self.getvalue()
                    super().close()
            return "staging-1", CapturedStream()

        def external_replace_staging(self):
            self.staging["staging-1"] = b"new attacker-controlled staging"
            self.current_generation += 1

        def seal_closed_staging(self, staging_ref):
            data = self.staging[staging_ref]
            return d["StagingSeal"](staging_ref, str(self.current_generation),
                                    len(data), hashlib.sha256(data).hexdigest())

        def _require_current_seal(self, seal):
            data = self.staging[seal.staging_ref]
            if (seal.generation != str(self.current_generation)
                    or len(data) != seal.byte_count
                    or hashlib.sha256(data).hexdigest() != seal.sha256):
                raise RuntimeError("sealed generation has changed")
            return data

        def read_sealed_staging(self, seal):
            data = self._require_current_seal(seal)
            self.sealed_read_calls += 1
            # A violation after a trusted first read is detected at the
            # NEXT read or conditional-finalize, never promoted to success.
            if self.mutate_after_first_sealed_read and self.sealed_read_calls == 1:
                self.external_replace_staging()
            return BytesIO(data)

        def finalize(self, intent, seal, receipt):
            data = self._require_current_seal(seal)
            assert receipt.sha256 == seal.sha256
            self.final_bytes = data
            if self.corrupt_final:
                self.final_bytes = self.final_bytes + b"externally changed"
            if self.raise_after_commit:
                raise RuntimeError("ack lost after effect")
            return "committed-object-ref"

        def inspect_final(self, intent):
            if self.final_bytes is None:
                return None
            data = self.final_bytes
            return receipt_type(len(data), hashlib.sha256(data).hexdigest(),
                                "synthetic-clock", "synthetic-domain")

    class FakeAuth:
        allow = True
        def may_write(self, actor_ref, locator):
            return self.allow

    class FakeCatalog:
        def __init__(self):
            self.pending = []
            self.committed = []
            self.fail_commit = False
            self.after_pending = None
        def record_pending(self, intent, receipt):
            self.pending.append((intent, receipt))
            if self.after_pending:
                self.after_pending()
        def record_committed(self, intent, receipt, final_ref):
            if self.fail_commit:
                raise RuntimeError("catalog record failed after bytes")
            self.committed.append((intent, receipt, final_ref))

    class FakeDomain:
        def validate(self, stream, expected_format):
            return "format-and-domain-valid" if stream.read().startswith(b"ok") else None

    def fixture():
        writer, catalog, auth, domain = (
            FakeWriter(), FakeCatalog(), FakeAuth(), FakeDomain())
        publisher = d["LocalOutputPublisher"](writer, catalog, auth, domain)
        return writer, catalog, auth, publisher

    def write_valid(stream):
        stream.write(b"ok synthetic workbook data")

    writer, catalog, auth, pub = fixture()
    result = pub.publish(intent, write_valid)
    assert result.phase is phase.COMMITTED
    assert len(catalog.committed) == 1
    assert result.byte_receipt.sha256 == hashlib.sha256(writer.final_bytes).hexdigest()

    writer, catalog, auth, pub = fixture()
    def interrupted(stream):
        stream.write(b"partial")
        raise RuntimeError("producer crashed")
    result = pub.publish(intent, interrupted)
    assert result.phase is phase.FAILED
    assert writer.final_bytes is None and not catalog.committed

    writer, catalog, auth, pub = fixture()
    writer.raise_after_commit = True
    result = pub.publish(intent, write_valid)
    assert result.phase is phase.OUTCOME_UNKNOWN and writer.final_bytes is not None
    assert catalog.pending and not catalog.committed

    writer, catalog, auth, pub = fixture()
    catalog.fail_commit = True
    result = pub.publish(intent, write_valid)
    assert result.phase is phase.OUTCOME_UNKNOWN and writer.final_bytes is not None

    writer, catalog, auth, pub = fixture()
    result = pub.publish(intent, lambda stream: stream.write(b"not a workbook"))
    assert result.phase is phase.QUARANTINED
    assert writer.final_bytes is None and not catalog.committed

    writer, catalog, auth, pub = fixture()
    catalog.after_pending = lambda: setattr(auth, "allow", False)
    result = pub.publish(intent, write_valid)
    assert result.phase is phase.FAILED and result.failure_code == "PERMISSION_CHANGED"
    assert writer.final_bytes is None

    writer, catalog, auth, pub = fixture()
    writer.corrupt_final = True
    result = pub.publish(intent, write_valid)
    assert result.phase is phase.OUTCOME_UNKNOWN and not catalog.committed

    writer, catalog, auth, pub = fixture()
    writer.mutate_after_first_sealed_read = True
    result = pub.publish(intent, write_valid)
    assert result.phase is not phase.COMMITTED
    assert writer.final_bytes is None and not catalog.committed

    writer, catalog, auth, pub = fixture()
    catalog.after_pending = writer.external_replace_staging
    result = pub.publish(intent, write_valid)
    assert result.phase is phase.OUTCOME_UNKNOWN
    assert writer.final_bytes is None and not catalog.committed

    return {"publication_effect_and_failure_cases": 9,
            "evidence": "executed documented publisher with in-memory bytes, no OS storage"}


def probe_trigger_occurrence() -> dict:
    """Exercise only the documented conditional automation trigger algorithm."""
    ref = "automation/trigger-occurrence-and-scheduling-construction.md"
    d = {"Enum": enum.Enum, "dataclass": dataclass}
    for name in ("TriggerKind", "EvaluationOutcome", "OccurrenceDisposition",
                 "TriggerEvaluation", "OccurrenceDecision",
                 "TriggerOccurrenceService", "source_change_evaluation"):
        compile_definition(ref, name, d)
    evaluation_kind = d["EvaluationOutcome"]
    disposition = d["OccurrenceDisposition"]
    rule = SimpleNamespace(automation_id="auto-1", rule_revision="rev-1",
                           enabled=True,
                           trigger=SimpleNamespace(kind=d["TriggerKind"].SOURCE_VERSION_CHANGE))
    evidence = SimpleNamespace(before_source_revision="v1",
                               after_source_revision="v2")
    evaluation = d["TriggerEvaluation"]("auto-1", "rev-1",
                                       evaluation_kind.OBSERVED, evidence)
    identity = SimpleNamespace(automation_id="auto-1", rule_revision="rev-1",
                               trigger_fingerprint="source-v1-v2")

    class Ledger:
        def __init__(self):
            self.claimed = set()
            self.attached = {}
            self.no_run = {}
            self.claim_fail_after_write = False
        def key(self, identity):
            return (identity.automation_id, identity.rule_revision,
                    identity.trigger_fingerprint)
        def claim_unique(self, identity, evidence):
            k = self.key(identity)
            if k in self.claimed:
                return False
            self.claimed.add(k)
            if self.claim_fail_after_write:
                raise RuntimeError("unique occurrence committed but ACK lost")
            return True
        def find_run_ref(self, identity):
            return self.attached.get(self.key(identity))
        def find_confirmed_no_run_reason(self, identity):
            return self.no_run.get(self.key(identity))
        def record_confirmed_no_run(self, identity, reason):
            self.no_run[self.key(identity)] = reason
        def attach_admission(self, identity, run_ref):
            self.attached[self.key(identity)] = run_ref

    class Admission:
        attempts = 0
        fail = False
        deny = False
        def request_run(self, rule, identity, evidence):
            self.attempts += 1
            if self.fail:
                raise RuntimeError("host accepted but reply lost")
            if self.deny:
                return None, "CONFIRMED_POLICY_DENIAL_NO_RUN"
            return "host-run-1", "HOST_ACCEPTED"

    ledger, admit = Ledger(), Admission()
    service = d["TriggerOccurrenceService"](ledger=ledger, admit=admit)
    first = service.handle(rule, evaluation, identity)
    assert first.disposition is disposition.ADMISSION_REQUESTED
    assert first.run_ref == "host-run-1"
    second = service.handle(rule, evaluation, identity)
    assert second.disposition is disposition.REPLAY_EXISTING
    assert second.run_ref == "host-run-1"
    assert admit.attempts == 1
    missing = d["TriggerEvaluation"]("auto-1", "rev-1",
                                     evaluation_kind.UNAVAILABLE, evidence)
    blocked = service.handle(rule, missing, None)
    assert blocked.disposition is disposition.BLOCKED
    rule.enabled = False
    disabled = service.handle(rule, evaluation, identity)
    assert disabled.disposition is disposition.SUPPRESSED
    rule.enabled = True
    wrong = SimpleNamespace(automation_id="auto-1", rule_revision="rev-old",
                            trigger_fingerprint="x")
    assert service.handle(rule, evaluation, wrong).disposition is disposition.BLOCKED

    other = SimpleNamespace(automation_id="auto-1", rule_revision="rev-1",
                            trigger_fingerprint="other-valid-event")
    admit.fail = True
    uncertain = service.handle(rule, evaluation, other)
    assert uncertain.disposition is disposition.UNKNOWN_ADMISSION
    assert ledger.key(other) in ledger.claimed
    retry = service.handle(rule, evaluation, other)
    assert retry.disposition is disposition.UNKNOWN_ADMISSION
    assert admit.attempts == 2  # never issued a second host request for the key

    # Definitive host rejection is an observable no-Run result, not a
    # permanently ambiguous occurrence or an invitation to resubmit.
    admit.fail = False
    admit.deny = True
    denied_id = SimpleNamespace(automation_id="auto-1", rule_revision="rev-1",
                                trigger_fingerprint="denied-event")
    denied = service.handle(rule, evaluation, denied_id)
    assert denied.disposition is disposition.BLOCKED
    assert denied.safe_code == "CONFIRMED_POLICY_DENIAL_NO_RUN"
    replay_denied = service.handle(rule, evaluation, denied_id)
    assert replay_denied.disposition is disposition.BLOCKED
    assert replay_denied.safe_code == denied.safe_code
    assert admit.attempts == 3  # no second host admission for denied occurrence

    # Occurrence claim ACK can fail after the ledger has written the key.
    ledger.claim_fail_after_write = True
    claim_id = SimpleNamespace(automation_id="auto-1", rule_revision="rev-1",
                               trigger_fingerprint="claim-ack-lost")
    claim_unknown = service.handle(rule, evaluation, claim_id)
    assert claim_unknown.disposition is disposition.UNKNOWN_ADMISSION
    assert ledger.key(claim_id) in ledger.claimed
    assert admit.attempts == 3
    ledger.claim_fail_after_write = False
    assert service.handle(rule, evaluation, claim_id).disposition is (
        disposition.UNKNOWN_ADMISSION)

    class SourceVerifier:
        def compare_qualified_versions(self, old, new):
            assert old == "v1" and new == "v2"
            return evaluation_kind.UNAVAILABLE
    source_result = d["source_change_evaluation"](rule, evidence, SourceVerifier())
    assert source_result.outcome is evaluation_kind.UNAVAILABLE
    return {
        "conditional_trigger_occurrence_cases": 12,
        "evidence": "real documented candidate service with fake occurrence ledger and source verifier",
    }


def probe_used_input_identity() -> dict:
    """Exercise the EXACT documentary capture/decode functions with fake bytes."""
    import hashlib
    from dataclasses import replace
    from datetime import datetime, timezone, timedelta

    ref = "data/used-input-receipt-construction.md"
    d = {"Enum": enum.Enum, "dataclass": dataclass,
         "datetime": datetime, "timedelta": timedelta,
         "sha256": hashlib.sha256, "uuid4": uuid.uuid4,
         "safe_url": lambda url: url,
         "DomainValidationIncomplete": type(
             "DomainValidationIncomplete", (ValueError,), {})}
    for name in ("AcquisitionKind", "ValidationKind", "InputEvidenceMismatch",
                 "CaptureClockInvalid", "checked_utc_observation",
                 "OriginalByteIdentity", "SourceAcquisition", "UsedInputReceipt",
                 "CapturedPayload", "DecodedPayload", "capture_downloaded_payload",
                 "decode_with_used_receipt"):
        compile_definition(ref, name, d)

    class Clock:
        def now_utc(self):
            return datetime(2026, 10, 12, 8, 30, tzinfo=timezone.utc)

    def ok(payload):
        return SimpleNamespace(ok=True, content=payload, status_code=200,
                               final_url="https://publisher.example/stat.xls")

    acquire = d["capture_downloaded_payload"]
    decode = d["decode_with_used_receipt"]
    clock = Clock()
    raw = bytearray(b"bank-source-2026")
    captured = acquire("public-source", "https://publisher.example/stat.xls",
                       lambda: ok(raw), clock)
    assert isinstance(captured, d["CapturedPayload"])
    assert captured.acquisition.kind is d["AcquisitionKind"].RECEIVED
    assert captured.content == b"bank-source-2026"
    assert captured.acquisition.actual_bytes.sha256 == hashlib.sha256(
        b"bank-source-2026").hexdigest()

    # A provider could retain/change its mutable response after capture.
    raw[0] = 0
    assert captured.content == b"bank-source-2026"

    class Decoder:
        def __init__(self):
            self.calls = 0
            self.actual_input = None
            self.format_kind = d["ValidationKind"].FORMAT_VALID
            self.format_evidence_ref = "synthetic-format-witness"
        def parse(self, payload):
            self.calls += 1
            self.actual_input = payload
            return d["DecodedPayload"](
                {"rows": 1}, self.format_kind, self.format_evidence_ref)
    class Validator:
        kind = "valid"
        def __init__(self):
            self.calls = 0
        def qualify(self, parsed, source_id):
            self.calls += 1
            return (d["ValidationKind"].DOMAIN_VALID if self.kind == "valid"
                    else d["ValidationKind"].INDETERMINATE), "evidence-ref"
    parser, validator = Decoder(), Validator()
    result, used = decode(captured, parser, validator, "bank_scope", clock,
                          registry_revision="r1", parser_revision="v1")
    assert result == {"rows": 1}
    assert parser.actual_input is captured.content
    assert used.byte_identity == captured.acquisition.actual_bytes
    assert used.format_validation is d["ValidationKind"].FORMAT_VALID
    assert used.domain_validation is d["ValidationKind"].DOMAIN_VALID

    # A forged/mismatched record MUST NOT reach decoder or validate as used.
    bad_content = replace(captured, content=b"other-version")
    parser.calls = 0
    try:
        decode(bad_content, parser, validator, "bank_scope", clock)
    except d["InputEvidenceMismatch"]:
        pass
    else:
        raise AssertionError("mismatched consumed bytes accepted")
    assert parser.calls == 0

    wrong_hash = replace(captured.acquisition, actual_bytes=d["OriginalByteIdentity"](
        "0" * 64, len(captured.content)))
    parser.calls = 0
    try:
        decode(replace(captured, acquisition=wrong_hash), parser,
               validator, "bank_scope", clock)
    except d["InputEvidenceMismatch"]:
        pass
    else:
        raise AssertionError("forged byte hash accepted")
    assert parser.calls == 0

    missing_digest = replace(captured.acquisition, actual_bytes=None)
    try:
        decode(replace(captured, acquisition=missing_digest),
               parser, validator, "bank_scope", clock)
    except d["InputEvidenceMismatch"]:
        pass
    else:
        raise AssertionError("missing byte proof accepted")

    # Format proof must precede domain validation: a parser may produce
    # something from HTML/invalid bytes without a qualified XLSX contract.
    parser.format_kind = d["ValidationKind"].NOT_CHECKED
    validator.calls = 0
    try:
        decode(captured, parser, validator, "bank_scope", clock)
    except d["DomainValidationIncomplete"]:
        pass
    else:
        raise AssertionError("parser result without format proof was promoted")
    assert validator.calls == 0
    parser.format_kind = d["ValidationKind"].FORMAT_VALID
    parser.format_evidence_ref = None
    validator.calls = 0
    try:
        decode(captured, parser, validator, "bank_scope", clock)
    except d["DomainValidationIncomplete"]:
        pass
    else:
        raise AssertionError("format-valid claim without evidence ref accepted")
    assert validator.calls == 0
    parser.format_evidence_ref = "synthetic-format-witness"

    validator.kind = "indeterminate"
    parser.calls = 0
    try:
        decode(captured, parser, validator, "bank_scope", clock)
    except d["DomainValidationIncomplete"]:
        pass
    else:
        raise AssertionError("indeterminate economic interpretation accepted")
    assert parser.calls == 1
    validator.kind = "valid"

    failed = acquire("s", "safe", lambda: (_ for _ in ()).throw(
        TimeoutError("fake transport timeout")), clock)
    assert isinstance(failed, d["SourceAcquisition"])
    assert failed.kind is d["AcquisitionKind"].FAILED
    assert failed.actual_bytes is None
    class NaiveClock:
        def now_utc(self):
            return datetime(2026, 10, 12, 8, 30)
    try:
        acquire("s", "safe", lambda: ok(b"good"), NaiveClock())
    except d["CaptureClockInvalid"]:
        pass
    else:
        raise AssertionError("naive observation was recorded as UTC")

    type_error = acquire("s", "safe", lambda: ok("not-byte-payload"), clock)
    assert type_error.kind is d["AcquisitionKind"].FAILED
    assert type_error.safe_error_code == "INVALID_PAYLOAD_TYPE"
    return {
        "used_byte_proof_and_negative_cases": 11,
        "evidence": "exact documented source capture/decode with fake immutable/mutable bytes",
    }


def probe_scoped_effect_guard() -> dict:
    """Execute exact documented security guard against denied fake policies."""
    from dataclasses import replace
    ref = "security/host-effect-authorization-construction.md"
    d = {"Enum": enum.Enum, "dataclass": dataclass}
    for name in ("EffectClass", "AuthOutcome", "DecisionPhase", "Principal",
                 "ResourceKey", "ActionRequest", "ApprovalScope",
                 "AuthDecision", "EffectGuard"):
        compile_definition(ref, name, d)
    effect, outcome = d["EffectClass"], d["AuthOutcome"]
    actor = d["Principal"]("trusted-user", "session-1", "host-1", "human", None)
    resource = d["ResourceKey"]("workspace", "object-42", "generation-7")
    request = d["ActionRequest"]("cleanup", "rev-3", effect.DELETE,
                                  resource, "plan-sha", "command-intent")
    approval = d["ApprovalScope"]("signed", "plan-sha", "target-sha",
                                   "trusted-user", "2099-01-01T00:00:00Z",
                                   "policy-42")

    class Policy:
        verdict = outcome.ALLOW
        revision = "policy-42"
        def evaluate(self, actor, request, *, phase):
            assert phase is d["DecisionPhase"].EFFECT
            return d["AuthDecision"](self.verdict, "synthetic-policy",
                                      self.revision, "generation-7", None)
    class Versions:
        revision = "generation-7"
        def current_revision(self, resource):
            return self.revision
    class Approvals:
        current = approval
        def verify_bound_scope(self, actor, request, approval_ref, digest):
            return self.current
    class Receipts:
        def __init__(self):
            self.intents = []
        def record_before_effect(self, actor, request, decision):
            self.intents.append((actor, request, decision))
            return "synthetic-durable-intent-1"
        def record_after_effect(self, intent_ref, observed_outcome):
            pass

    policy, versions, approvals, receipts = (
        Policy(), Versions(), Approvals(), Receipts())
    guard = d["EffectGuard"](policy, approvals, versions, receipts)

    def attempt(req=request, target="target-sha", approval_ref="signed"):
        return guard.authorize_before_effect(
            actor, req, approval_ref=approval_ref, target_set_digest=target)

    assert attempt() == "synthetic-durable-intent-1"
    assert len(receipts.intents) == 1
    receipts.intents.clear()

    def denied(exc_type, invocation):
        before = len(receipts.intents)
        try:
            invocation()
        except exc_type:
            pass
        else:
            raise AssertionError(f"unsafe approval passed: {exc_type}")
        assert len(receipts.intents) == before

    denied(PermissionError, lambda: attempt(
        replace(request, resource=replace(resource, revision=None))))
    denied(PermissionError, lambda: attempt(target=""))
    denied(PermissionError, lambda: attempt(approval_ref=None))
    approvals.current = replace(approval, actor_ref="other-principal")
    denied(PermissionError, attempt)
    approvals.current = replace(approval, target_set_digest="wrong-set")
    denied(PermissionError, attempt)
    approvals.current = replace(approval, request_digest="old-plan")
    denied(PermissionError, attempt)
    approvals.current = replace(approval, policy_revision="policy-old")
    denied(PermissionError, attempt)
    approvals.current = approval

    policy.verdict = outcome.DENY
    denied(PermissionError, attempt)
    policy.verdict = outcome.POLICY_UNAVAILABLE
    denied(PermissionError, attempt)
    policy.verdict = outcome.ALLOW
    versions.revision = "generation-8"
    denied(RuntimeError, attempt)
    versions.revision = "generation-7"
    policy.revision = None
    denied(PermissionError, attempt)
    return {
        "scoped_effect_auth_probes": 12,
        "evidence": "literal EffectGuard against fake object revisions, approval scopes, and policies; NO actual OS effect",
    }


def probe_safe_shared_projection() -> dict:
    """Run the actual documented projection with an independent fake schema."""
    ref = "security/host-effect-authorization-construction.md"
    d = {"Enum": enum.Enum, "dataclass": dataclass}
    for name in ("EffectClass", "AuthOutcome", "DecisionPhase", "Principal",
                 "ResourceKey", "ActionRequest", "AuthDecision",
                 "FieldVisibility", "ClassifiedField",
                 "QualifiedSharedField", "AudienceProjection"):
        compile_definition(ref, name, d)
    actor = d["Principal"]("p", "session", "host", "human", None)
    key = d["ResourceKey"]("node-shared-events", "event-7", "v2")
    vis = d["FieldVisibility"]

    class Policy:
        allow = True
        def evaluate(self, actor, request, *, phase):
            assert phase is d["DecisionPhase"].FETCH
            return d["AuthDecision"](
                d["AuthOutcome"].ALLOW if self.allow else d["AuthOutcome"].DENY,
                "synthetic", "p-1", "v2", None)

    class SafeFields:
        def __init__(self):
            self.remap = False
        def qualify_shared(self, resource, name, value):
            allowed = {"status", "safe_code", "observed_at_utc"}
            if resource.namespace != "node-shared-events" or name not in allowed:
                return None
            if type(value) is not str or len(value) > 80:
                return None
            if any(fragment in value.lower() for fragment in (
                    "token=", "bearer ", "<script", "/private/", "traceback")):
                return None
            safe_name = "unexpected-new-key" if self.remap else name
            return d["QualifiedSharedField"](safe_name, value)

    policy, safe = Policy(), SafeFields()
    projection = d["AudienceProjection"](policy, safe)
    fields = (
        d["ClassifiedField"]("status", "failed", vis.SHARED_SAFE),
        d["ClassifiedField"]("private_path", "/private/a", vis.SHARED_SAFE),
        d["ClassifiedField"]("raw_exception", "token=fake", vis.SHARED_SAFE),
        d["ClassifiedField"]("safe_code", "SOURCE_FAILED", vis.SHARED_SAFE),
        d["ClassifiedField"]("safe_code", "token=secret", vis.SHARED_SAFE),
        d["ClassifiedField"]("observed_at_utc", "2026-10-12T08:30:00Z", vis.SHARED_SAFE),
        d["ClassifiedField"]("safe_code", RuntimeError("bad"), vis.SHARED_SAFE),
        d["ClassifiedField"]("status", "private", vis.OWNER_ONLY),
        d["ClassifiedField"]("status", "<script>evil()</script>", vis.SHARED_SAFE),
    )
    result = projection.select(actor, key, fields)
    assert result["status"] == "failed"
    assert result["safe_code"] == "SOURCE_FAILED"
    assert result["observed_at_utc"] == "2026-10-12T08:30:00Z"
    assert set(result) == {"status", "safe_code", "observed_at_utc"}
    policy.allow = False
    try:
        projection.select(actor, key, fields)
    except PermissionError:
        pass
    else:
        raise AssertionError("unauthorized resource read escaped host policy")
    policy.allow = True
    safe.remap = True
    try:
        projection.select(actor, key, fields)
    except ValueError:
        pass
    else:
        raise AssertionError("untrusted field remapping silently admitted")
    return {
        "bounded_shared_projection_adverse_cases": 8,
        "evidence": "literal documented AudienceProjection against fake schema/authorization; no real serialization",
    }


def probe_curated_machine_admission() -> dict:
    """Execute documented machine gateway with a fake but effectful host port."""
    ref = "capabilities/curated-machine-operation-adapter-construction.md"
    d = {"Enum": enum.Enum, "dataclass": dataclass}
    for name in ("Availability", "DomainQuality", "AdmissionStatus",
                 "OperationDefinition", "MachineInvocation", "MachineAdmission",
                 "MachineGateway"):
        compile_definition(ref, name, d)
    status = d["AdmissionStatus"]
    definition = d["OperationDefinition"](
        "bank.report", "schema-v1", "Bank report",
        "safe-input-schema", "safe-output-schema",
        "compute", True, "machine_allowed")
    class Catalog:
        approved = True
        allow_machine = True
        def get_approved(self, operation_id, contract_revision):
            if not self.approved or operation_id != "bank.report" or contract_revision != "schema-v1":
                return None
            return definition if self.allow_machine else d["OperationDefinition"](
                "bank.report", "schema-v1", "Bank report",
                "safe-input-schema", "safe-output-schema",
                "compute", False, "hidden")
        def list_authorized(self, trusted_actor):
            return (definition,)
    class Schema:
        def validate_strict(self, schema_ref, params):
            if schema_ref != "safe-input-schema" or set(params) != {"period"}:
                raise ValueError("unregistered parameter")
            if not isinstance(params["period"], str):
                raise TypeError("period")
            return {"period": params["period"]}
    class Bindings:
        available = True
        def is_available(self, operation_id, contract_revision):
            return self.available
    class Policy:
        allow = True
        def may_invoke(self, principal, definition, params):
            return self.allow
    class Application:
        def __init__(self):
            self.calls = []
            self.mode = "accepted"
        def admit(self, actor, request, params):
            self.calls.append((actor, request.intention_key, dict(params)))
            if self.mode == "ack_lost":
                # The host may have durably admitted an invocation.
                raise TimeoutError("simulated lost admission ACK")
            if self.mode == "accepted_no_ref":
                return d["MachineAdmission"](None, status.ACCEPTED, "ACCEPTED")
            if self.mode == "denied_with_ref":
                return d["MachineAdmission"]("already-admitted-run",
                                              status.REJECTED, "REJECTED")
            if self.mode == "bad_port_type":
                return d["MachineAdmission"](None, "accepted", "BAD_TYPE")
            if self.mode == "null_payload":
                return None
            if self.mode == "no_run":
                return d["MachineAdmission"](None, status.REJECTED, "NOT_ADMITTED")
            return d["MachineAdmission"]("run-1", status.ACCEPTED, "RUN_ADMITTED")
    catalog, schema, bindings, policy, app = (
        Catalog(), Schema(), Bindings(), Policy(), Application())
    gateway = d["MachineGateway"](catalog, schema, bindings, policy, app)
    invoke = d["MachineInvocation"]("stable-intent-key", "bank.report",
                                     "schema-v1", {"period": "2026-07"})
    result = gateway.invoke("trusted-host-principal", invoke)
    assert result.accepted and result.status is status.ACCEPTED
    assert result.run_ref == "run-1" and len(app.calls) == 1
    catalog.approved = False
    assert gateway.invoke("trusted-host-principal", invoke).status is status.REJECTED
    catalog.approved = True
    catalog.allow_machine = False
    assert gateway.invoke("trusted-host-principal", invoke).status is status.REJECTED
    catalog.allow_machine = True
    altered = d["MachineInvocation"](
        "stable-intent-key", "bank.report", "schema-v1",
        {"period": "2026-07", "handler": "os.system"})
    assert gateway.invoke("trusted-host-principal", altered).safe_code == "PARAMETER_SCHEMA_INVALID"
    bindings.available = False
    assert gateway.invoke("trusted-host-principal", invoke).status is status.REJECTED
    bindings.available = True
    policy.allow = False
    assert gateway.invoke("trusted-host-principal", invoke).status is status.REJECTED
    policy.allow = True
    for mode, expected in (
        ("ack_lost", status.OUTCOME_UNKNOWN),
        ("accepted_no_ref", status.OUTCOME_UNKNOWN),
        ("denied_with_ref", status.OUTCOME_UNKNOWN),
        ("bad_port_type", status.OUTCOME_UNKNOWN),
        ("null_payload", status.OUTCOME_UNKNOWN),
        ("no_run", status.REJECTED),
    ):
        app.mode = mode
        result = gateway.invoke("trusted-host-principal", invoke)
        assert result.status is expected and not result.accepted
        assert app.calls[-1][1] == "stable-intent-key"
    return {"machine_admission_adverse_cases": 12,
            "evidence": "literal MachineGateway with fake host; no real MCP/A2A or Run store"}


def probe_neutral_provider_binding() -> dict:
    """Execute documented neutral resolver against metadata-only fake ports."""
    ref = "extensions/neutral-provider-binding-construction.md"
    d = {"Enum": enum.Enum, "dataclass": dataclass}
    for name in ("ContributionKind", "BindingStatus", "FailureKind",
                 "ProviderDescriptor", "BindingPolicy", "BindingResult",
                 "NeutralProviderResolver"):
        compile_definition(ref, name, d)
    kind, status = d["ContributionKind"], d["BindingStatus"]
    descriptor = d["ProviderDescriptor"](
        "provider-public-a", "dist-a@1", 1, 0,
        kind.FILE_BYTES, "file_bytes", "revision-1", False)
    optional = d["ProviderDescriptor"](
        "provider-codec", "dist-b@2", 1, 0,
        kind.FORMAT_CODEC, "format_codec", "revision-1", True)

    class Discovery:
        def __init__(self):
            self.items = (descriptor, optional)
        def list_metadata_only(self):
            return self.items
    class Compat:
        def validate(self, desc, major):
            return desc.api_major == major
    class Activation:
        def __init__(self):
            self.calls = 0
            self.raise_error = False
        def activate(self, desc, config):
            self.calls += 1
            if self.raise_error:
                raise ValueError("synthetic setup error")
            return object()
    class Health:
        verdict = status.READY
        def check(self, instance, scope):
            return self.verdict

    discovery, compat, activation, health = (
        Discovery(), Compat(), Activation(), Health())
    resolver = d["NeutralProviderResolver"](
        discovery, compat, activation, health)
    policy = d["BindingPolicy"](
        "workspace-A", {"file_bytes": "provider-public-a",
                        "format_codec": "provider-codec"},
        frozenset(), frozenset({"file_bytes"}))
    bind = lambda slot, major=1, configuration=None: resolver.resolve(
        policy, slot, required_major=major, configuration=configuration or {})
    assert bind("file_bytes").status is status.READY
    health.verdict = True
    assert bind("file_bytes").status is status.CONTRACT_FAILURE
    health.verdict = "ready"
    assert bind("file_bytes").status is status.CONTRACT_FAILURE
    health.verdict = status.DEGRADED
    assert bind("file_bytes").status is status.DEGRADED
    health.verdict = status.READY
    before = activation.calls
    assert bind("format_codec").status is status.CONFIGURATION_REQUIRED
    assert activation.calls == before
    assert bind("format_codec", configuration={"profile": "safe"}).status is status.READY
    assert bind("file_bytes", major=2).status is status.INCOMPATIBLE
    discovery.items = (descriptor, descriptor)
    assert bind("file_bytes").status is status.CONTRACT_FAILURE
    discovery.items = ()
    assert bind("file_bytes").status is status.UNAVAILABLE
    discovery.items = (descriptor, optional)
    activation.raise_error = True
    assert bind("file_bytes").status is status.CONTRACT_FAILURE
    activation.raise_error = False
    nochoice = d["BindingPolicy"]("workspace-A", {}, frozenset(), frozenset({"file_bytes"}))
    outcome = resolver.resolve(nochoice, "file_bytes", required_major=1,
                               configuration={})
    assert outcome.status is status.NOT_SELECTED
    assert outcome.safe_code == "REQUIRED_PROVIDER_NOT_SELECTED"
    return {"provider_resolution_adverse_cases": 11,
            "evidence": "literal neutral resolver on fake public descriptors; no provider package activated"}


def probe_frg_cleanup_effects() -> dict:
    """Execute the exact documented FRG executor with frozen synthetic witnesses.

    This does not implement the deliberately unavailable plan normalizer or
    verify OS conditional file mutation and historical domain semantics.
    """
    import hashlib
    from dataclasses import replace, asdict
    ref = "application/frg-cleanup-effect-plan-construction.md"
    d = {"Enum": enum.Enum, "dataclass": dataclass}
    class StalePlanError(RuntimeError):
        pass
    d["StalePlanError"] = StalePlanError
    d["asdict"] = asdict
    d["hashlib"] = hashlib
    d["json"] = json
    for name in ("FileAction", "EffectTruth", "FileWitness",
                 "FrozenAction", "FrozenCleanupPlan", "EffectReceipt",
                 "canonical_cleanup_digest", "source_witness_matches",
                 "CleanupExecutor"):
        compile_definition(ref, name, d)
    action, truth = d["FileAction"], d["EffectTruth"]
    source = d["FileWitness"]("data", "reports/new-source.xlsx", "gen-2",
                              "digest-new", "2026-10-12T08:00:00Z", True)
    target = d["FileWitness"]("data", "reports/target.xlsx", "gen-1",
                              "digest-old", "2026-10-12T08:00:00Z", True)
    copy = d["FrozenAction"]("copy-1", action.COPY_LATEST, source, target,
                              "financial-family", "2026-07", "digest-old", True)
    delete = d["FrozenAction"]("delete-1", action.DELETE_SOURCE, source, None,
                                "financial-family", "2026-07", None, True)
    archive = d["FrozenAction"]("archive-1", action.CREATE_ARCHIVE,
                                 source, target, "financial-family",
                                 "2026-07", None, False)
    canonical = d["canonical_cleanup_digest"]
    plan = d["FrozenCleanupPlan"](
        "plan-1", "v1", "data", (copy, delete),
        canonical((copy, delete), "data", "v1", "src-rev-2"), "src-rev-2")
    plan_with_archive = replace(
        plan, actions=(copy, delete, archive),
        sorted_target_set_digest=canonical(
            (copy, delete, archive), "data", "v1", "src-rev-2"))
    class Evidence:
        current = source
        recognized = True
        family = "financial-family"
        def derive_plan_digest(self, actions, scope_ref, revision,
                               selected_source_revision):
            # Invoke the exact documented canonical fingerprint, not a fake
            # action-ID-only implementation that masks same-ID substitutions.
            return canonical(actions, scope_ref, revision, selected_source_revision)
        def observe(self, scope_ref, path):
            return self.current
        def recognized_source(self, scope_ref, path):
            return (self.family, "2026-07") if self.recognized else None
    class Effects:
        def __init__(self):
            self.final_bytes = None
            self.staging_is_valid = True
            self.ack_lost = False
            self.deleted = False
            self.calls = []
        def prepare_copy_to_staging(self, src, dest):
            self.calls.append("staged")
            return "staging-key"
        def verify_staging(self, ref, expected):
            self.calls.append("verified_staging")
            return self.staging_is_valid
        def conditional_finalize(self, staging_ref, target, expected):
            self.calls.append("finalized")
            self.final_bytes = b"new-source"
            if self.ack_lost:
                raise TimeoutError("synthetic lost ACK")
            return replace(target, sha256=expected, file_generation="gen-3")
        def conditional_delete(self, src):
            self.calls.append("deleted")
            self.deleted = True
            if self.ack_lost:
                raise TimeoutError("synthetic lost delete ACK")
            return "deleted-file-generation"
    class Auth:
        permit = True
        def authorize(self, plan, step, approval_ref):
            if not self.permit or approval_ref != "approved-plan":
                raise PermissionError("not approved")
            return "trusted-fake-permit"
    class Receipts:
        def __init__(self):
            self.pending = []
            self.recorded = []
        def record_pending(self, plan, action, permit_ref):
            self.pending.append((plan.plan_id, action.action_id))
            return "pending-" + action.action_id
        def record_result(self, pending_ref, result):
            self.recorded.append((pending_ref, result.truth))
    def fixture():
        effects, auth, receipts, evidence = (
            Effects(), Auth(), Receipts(), Evidence())
        executor = d["CleanupExecutor"](effects, auth, receipts, evidence)
        return effects, auth, receipts, evidence, executor

    effects, auth, receipts, evidence, executor = fixture()
    result = executor.apply_one(plan, copy, "approved-plan")
    assert result.truth is truth.VERIFIED and result.observed_target_digest == "digest-new"
    assert effects.calls == ["staged", "verified_staging", "finalized"]
    assert len(receipts.pending) == len(receipts.recorded) == 1

    effects, auth, receipts, evidence, executor = fixture()
    evidence.current = replace(source, sha256="modified-after-preview")
    result = executor.apply_one(plan, copy, "approved-plan")
    assert result.truth is truth.FAILED_NO_EFFECT
    assert not effects.calls and effects.final_bytes is None

    effects, auth, receipts, evidence, executor = fixture()
    effects.staging_is_valid = False
    result = executor.apply_one(plan, copy, "approved-plan")
    assert result.truth is truth.FAILED_NO_EFFECT
    assert effects.final_bytes is None

    effects, auth, receipts, evidence, executor = fixture()
    effects.ack_lost = True
    result = executor.apply_one(plan, copy, "approved-plan")
    assert result.truth is truth.OUTCOME_UNKNOWN and result.reconciliation_ref
    assert effects.final_bytes is not None

    effects, auth, receipts, evidence, executor = fixture()
    result = executor.apply_one(plan, delete, "approved-plan")
    assert result.truth is truth.VERIFIED and effects.deleted

    effects, auth, receipts, evidence, executor = fixture()
    evidence.recognized = False
    result = executor.apply_one(plan, delete, "approved-plan")
    assert result.truth is truth.FAILED_NO_EFFECT and not effects.deleted

    effects, auth, receipts, evidence, executor = fixture()
    result = executor.apply_one(plan_with_archive, archive, "approved-plan")
    assert result.truth is truth.OUTCOME_UNKNOWN and not effects.calls

    # A handwritten FrozenAction outside a verified plan must be rejected
    # before any approval or effect-intent record.
    effects, auth, receipts, evidence, executor = fixture()
    def assert_pre_effect_rejected(p, step):
        try:
            executor.apply_one(p, step, "approved-plan")
        except PermissionError:
            pass
        else:
            raise AssertionError("unapproved plan/step reached effect")
        assert not receipts.pending and not effects.calls

    assert_pre_effect_rejected(plan, archive)
    assert_pre_effect_rejected(
        plan, replace(copy, source=replace(source, relative_path="system/secret")))
    assert_pre_effect_rejected(
        replace(plan, actions=(copy, copy, delete),
                sorted_target_set_digest="copy-1:copy-1:delete-1"), copy)
    assert_pre_effect_rejected(
        replace(plan, actions=(copy, archive), sorted_target_set_digest="copy-1:delete-1"), copy)
    cross_scope_source = replace(copy, source=replace(source, root_scope="system"))
    assert_pre_effect_rejected(
        replace(plan, actions=(cross_scope_source, delete),
                sorted_target_set_digest=canonical(
                    (cross_scope_source, delete), "data", "v1", "src-rev-2")),
        cross_scope_source)
    cross_scope_target = replace(copy, target=replace(target, root_scope="other"))
    assert_pre_effect_rejected(
        replace(plan, actions=(cross_scope_target, delete),
                sorted_target_set_digest=canonical(
                    (cross_scope_target, delete), "data", "v1", "src-rev-2")),
        cross_scope_target)
    unidentified_delete = replace(
        delete, source=replace(source, sha256=None, file_generation=None))
    assert_pre_effect_rejected(
        replace(plan, actions=(copy, unidentified_delete),
                sorted_target_set_digest=canonical(
                    (copy, unidentified_delete), "data", "v1", "src-rev-2")),
        unidentified_delete)
    assert not receipts.recorded

    # A forged *same-ID* plan cannot keep a valid approved digest when any
    # effect-bearing field, source revision, scope or plan revision changes.
    forged_target = replace(copy, target=replace(
        target, relative_path="reports/other-destination.xlsx"))
    assert canonical((forged_target, delete), "data", "v1", "src-rev-2") != (
        plan.sorted_target_set_digest)
    assert canonical((copy, delete), "data", "v2", "src-rev-2") != (
        plan.sorted_target_set_digest)
    assert canonical((copy, delete), "data", "v1", "src-rev-3") != (
        plan.sorted_target_set_digest)
    assert canonical((copy, delete), "other", "v1", "src-rev-2") != (
        plan.sorted_target_set_digest)
    try:
        canonical((copy, copy, delete), "data", "v1", "src-rev-2")
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate IDs were signed into the plan")
    # Reobservation is allowed when the *byte/generation identity* is stable
    # while the observation timestamp has legitimately advanced.
    matches = d["source_witness_matches"]
    assert matches(replace(source, observed_at_utc="2026-10-12T10:10:00Z"), source)
    assert not matches(replace(source, sha256="changed"), source)
    assert not matches(replace(source, file_generation="gen-4"), source)

    effects, auth, receipts, evidence, executor = fixture()
    evidence.current = replace(source, observed_at_utc="2026-10-12T10:10:00Z")
    result = executor.apply_one(plan, copy, "approved-plan")
    assert result.truth is truth.VERIFIED

    effects, auth, receipts, evidence, executor = fixture()
    evidence.current = replace(source, sha256="unexpected-new-version")
    result = executor.apply_one(plan, delete, "approved-plan")
    assert result.truth is truth.FAILED_NO_EFFECT and not effects.deleted

    effects, auth, receipts, evidence, executor = fixture()
    evidence.family = "different-recognized-family"
    result = executor.apply_one(plan, delete, "approved-plan")
    assert result.truth is truth.FAILED_NO_EFFECT and not effects.deleted

    effects, auth, receipts, evidence, executor = fixture()
    auth.permit = False
    try:
        executor.apply_one(plan, copy, "approved-plan")
    except PermissionError:
        pass
    else:
        raise AssertionError("unapproved FRG effect admitted")
    assert not receipts.pending and not effects.calls
    return {
        "frg_cleanup_effect_cases": 25,
        "fingerprint_uses_full_action_content": True,
        "source_observation_time_excluded_from_byte_equality": True,
        "evidence": "literal documented executor, canonical SHA256 plan fingerprint and byte-witness matcher on synthetic effects; no native FS proof",
    }


def probe_host_dispatch_recovery() -> dict:
    """Exercise exact documented outbox consumer with fault-injected fake ports.

    Durable transaction, lease expiry, native scheduler and actual effect
    safety are NOT simulated or asserted by this producer self-test.
    """
    ref = "hosting/host-authority-and-client-contract-construction.md"
    d = {"Enum": enum.Enum, "dataclass": dataclass}
    for name in ("DispatchRecoveryKind", "DispatchClaim",
                 "DispatchRecoveryReceipt", "HostDispatchRecovery"):
        compile_definition(ref, name, d)
    kind, claimtype = d["DispatchRecoveryKind"], d["DispatchClaim"]
    class Outbox:
        def __init__(self):
            self.unfinished = []
            self.epoch = 0
            self.current_claim = None
            self.fail_claim = False
            self.fail_ack = False
            self.bad_claim = None
            self.unknowns = []
            self.dispatched = set()
        def append_as_if_transactional(self, run_ref):
            self.unfinished.append((f"dispatch-{run_ref}", run_ref))
        def claim_next(self, worker_ref):
            if self.fail_claim:
                raise RuntimeError("fake ledger unreachable")
            if self.bad_claim is not None:
                return self.bad_claim
            if not self.unfinished:
                return None
            self.epoch += 1
            dispatch_ref, run_ref = self.unfinished[0]
            self.current_claim = claimtype(dispatch_ref, run_ref,
                                           worker_ref, self.epoch)
            return self.current_claim
        def mark_dispatched(self, claim):
            assert claim == self.current_claim, "stale ledger fence"
            if self.fail_ack:
                raise RuntimeError("lost final ledger ACK")
            assert claim.dispatch_ref == self.unfinished[0][0]
            self.unfinished.pop(0)
            self.dispatched.add(claim.dispatch_ref)
        def mark_uncertain(self, claim, safe_code):
            assert claim == self.current_claim, "stale claim"
            self.unknowns.append((claim.dispatch_ref, safe_code))
    class Scheduler:
        def __init__(self):
            self.reservations = set()
            self.calls = []
            self.lost_ack = False
            self.untyped_ack = False
        def schedule_once(self, claim):
            self.calls.append((claim.dispatch_ref, claim.fence_epoch))
            # Fake exact same logical Job key, even if the first ACK is lost.
            self.reservations.add(claim.dispatch_ref)
            if self.lost_ack:
                raise TimeoutError("schedule committed before ACK loss")
            if self.untyped_ack:
                return 1
            return True
    def new():
        ledger, scheduler = Outbox(), Scheduler()
        return ledger, scheduler, d["HostDispatchRecovery"](ledger, scheduler)

    ledger, scheduler, recoverer = new()
    assert recoverer.run_once("worker-A").kind is kind.NO_PENDING

    # Emulate the durable accepted-Run/outbox pair that was originally stranded
    # by a lost ledger admission response and a later REPLAY.
    ledger.append_as_if_transactional("run-1")
    scheduler.lost_ack = True
    first = recoverer.run_once("worker-A")
    assert first.kind is kind.DISPATCH_UNKNOWN and first.run_ref == "run-1"
    assert scheduler.reservations == {"dispatch-run-1"} and ledger.unfinished
    scheduler.lost_ack = False
    recovery = recoverer.run_once("worker-B")
    assert recovery.kind is kind.DISPATCH_CONFIRMED
    assert recovery.run_ref == "run-1"
    assert scheduler.reservations == {"dispatch-run-1"}
    assert len(scheduler.calls) == 2
    assert recoverer.run_once("worker-C").kind is kind.NO_PENDING

    ledger, scheduler, recoverer = new()
    ledger.append_as_if_transactional("run-2")
    ledger.fail_claim = True
    assert recoverer.run_once("worker-A").kind is kind.DISPATCH_UNKNOWN
    assert not scheduler.calls and ledger.unfinished

    ledger, scheduler, recoverer = new()
    ledger.append_as_if_transactional("run-3")
    ledger.bad_claim = claimtype("dispatch-run-3", "run-3",
                                 "other-worker", 1)
    assert recoverer.run_once("worker-A").kind is kind.MALFORMED_CLAIM
    assert not scheduler.calls

    ledger, scheduler, recoverer = new()
    ledger.append_as_if_transactional("run-4")
    ledger.bad_claim = claimtype("dispatch-run-4", "run-4",
                                 "worker-A", True)
    assert recoverer.run_once("worker-A").kind is kind.MALFORMED_CLAIM

    ledger, scheduler, recoverer = new()
    ledger.append_as_if_transactional("run-5")
    scheduler.untyped_ack = True
    assert recoverer.run_once("worker-A").kind is kind.DISPATCH_UNKNOWN
    assert ledger.unknowns and ledger.unfinished
    scheduler.untyped_ack = False
    assert recoverer.run_once("worker-B").kind is kind.DISPATCH_CONFIRMED
    assert len(scheduler.reservations) == 1

    ledger, scheduler, recoverer = new()
    ledger.append_as_if_transactional("run-6")
    ledger.fail_ack = True
    assert recoverer.run_once("worker-A").kind is kind.DISPATCH_UNKNOWN
    assert ledger.unfinished and scheduler.reservations == {"dispatch-run-6"}
    ledger.fail_ack = False
    assert recoverer.run_once("worker-B").kind is kind.DISPATCH_CONFIRMED
    assert scheduler.reservations == {"dispatch-run-6"}

    return {
        "outbox_recovery_synthetic_cases": 7,
        "ack_lost_after_accepted_run_can_recover": True,
        "reservation_key_not_run_duplicate": True,
        "evidence": "literal HostDispatchRecovery AST with synthetic transactional outbox and idempotent scheduler; zero real durability or host execution claims",
    }


def main() -> dict:
    checks = {
        "local_scenario": probe_local_run(),
        "host_admission": probe_host_admission(),
        "authorized_host_feed": probe_authorized_host_feed(),
        "host_dispatch_recovery": probe_host_dispatch_recovery(),
        "problem_receipt": probe_problem_receipt(),
        "artifact_publication": probe_artifact_publication(),
        "trigger_occurrence": probe_trigger_occurrence(),
        "used_input_identity": probe_used_input_identity(),
        "scoped_effect_guard": probe_scoped_effect_guard(),
        "safe_shared_projection": probe_safe_shared_projection(),
        "machine_admission": probe_curated_machine_admission(),
        "neutral_provider_binding": probe_neutral_provider_binding(),
        "frg_cleanup_effects": probe_frg_cleanup_effects(),
    }
    # Coverage counts *documents*, not separate fake scenarios. The Security
    # document has two independently useful scoped probes.
    packet_to_probes = {
        "application/local-scenario-execution-construction.md": ("local_scenario",),
        "hosting/host-authority-and-client-contract-construction.md": (
            "host_admission", "host_dispatch_recovery", "authorized_host_feed"),
        "artifacts/local-output-publication-construction.md": ("artifact_publication",),
        "data/used-input-receipt-construction.md": ("used_input_identity",),
        "observability/execution-evidence-and-problem-boundary-construction.md": ("problem_receipt",),
        "security/host-effect-authorization-construction.md": (
            "scoped_effect_guard", "safe_shared_projection"),
        "application/frg-cleanup-effect-plan-construction.md": ("frg_cleanup_effects",),
        "capabilities/curated-machine-operation-adapter-construction.md": ("machine_admission",),
        "extensions/neutral-provider-binding-construction.md": ("neutral_provider_binding",),
        "automation/trigger-occurrence-and-scheduling-construction.md": ("trigger_occurrence",),
    }
    assert len(packet_to_probes) == 10
    assert set(checks) == {
        key for probes in packet_to_probes.values() for key in probes}
    assert all((LCD / doc).is_file() for doc in packet_to_probes)
    return {
        "status": "DOCUMENTED_CANDIDATE_FAKE_BEHAVIOR_PASS",
        "checks": checks,
        "packet_coverage": {
            "unique_document_packets": len(packet_to_probes),
            "independent_fake_probe_functions": len(checks),
            "mapping": {doc: list(probes) for doc, probes in packet_to_probes.items()},
        },
        "scope": "ten documented LCD constructions with synthetic ports only",
        "limits": [
            "no installed or actual Strategy Box production implementation executed",
            "host persistence, thread scheduling, real network and platform unavailable",
            "unresolved Product Decisions and missing real native fault injection",
            "producer-authored fixtures; independent assurance NOT PERFORMED",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(main(), indent=2, ensure_ascii=False))
