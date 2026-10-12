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
    return {"result_algebra": 5, "single_flight_and_faults": 6,
            "evidence": "executed isolated doc-defined classes/functions with fakes"}


def probe_host_admission() -> dict:
    ref = "hosting/host-authority-and-client-contract-construction.md"
    d = {"Enum": enum.Enum, "dataclass": dataclass}
    for name in ("AdmissionKind", "AdmissionReceipt", "HostAdmission"):
        compile_definition(ref, name, d)
    kind, receipt = d["AdmissionKind"], d["AdmissionReceipt"]
    host = SimpleNamespace(host_id="host-1")
    actor = SimpleNamespace(principal_ref="p1")
    req = SimpleNamespace(intention_key="intent", payload_digest="good")
    class Policy:
        allow = True
        def can_submit(self, actor, req):
            return self.allow
    class Ledger:
        def __init__(self):
            self.calls = 0
            self.seen = {}
        def admit_atomically(self, actor, request, host):
            self.calls += 1
            old = self.seen.get(request.intention_key)
            if old:
                digest, run = old
                return receipt(kind.REPLAY if digest == request.payload_digest
                               else kind.REJECTED, request.intention_key,
                               run if digest == request.payload_digest else None,
                               host.host_id)
            run = "run-1"
            self.seen[request.intention_key] = (request.payload_digest, run)
            return receipt(kind.ACCEPTED, request.intention_key, run, host.host_id)
    class Scheduler:
        fail = True
        calls = 0
        def schedule(self, run_ref):
            self.calls += 1
            if self.fail:
                raise RuntimeError("lost ACK")

    policy, ledger, scheduler = Policy(), Ledger(), Scheduler()
    svc = d["HostAdmission"](host, policy, ledger, scheduler)
    first = svc.submit(actor, req)
    assert first.kind is kind.OUTCOME_UNKNOWN and first.run_ref == "run-1"
    replay = svc.submit(actor, req)
    assert replay.kind is kind.REPLAY and replay.run_ref == "run-1"
    assert scheduler.calls == 1
    conflict = svc.submit(actor, SimpleNamespace(intention_key="intent",
                                                  payload_digest="different"))
    assert conflict.kind is kind.REJECTED
    policy.allow = False
    denied = svc.submit(actor, SimpleNamespace(intention_key="different",
                                                payload_digest="good"))
    assert denied.kind is kind.REJECTED
    return {"admission_duplicate_conflict_denial": 4,
            "evidence": "executed candidate admission code on synthetic ledger; no durability"}


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


def main() -> dict:
    checks = {
        "local_scenario": probe_local_run(),
        "host_admission": probe_host_admission(),
        "problem_receipt": probe_problem_receipt(),
    }
    return {
        "status": "DOCUMENTED_CANDIDATE_FAKE_BEHAVIOR_PASS",
        "checks": checks,
        "scope": "three named LCD snippets executed with synthetic ports only",
        "limits": [
            "no installed or actual Strategy Box production implementation executed",
            "host persistence, thread scheduling, real network and platform unavailable",
            "unresolved Product Decisions and missing real native fault injection",
            "producer-authored fixtures; independent assurance NOT PERFORMED",
        ],
    }


if __name__ == "__main__":
    print(json.dumps(main(), indent=2, ensure_ascii=False))
