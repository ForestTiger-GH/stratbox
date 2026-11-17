"""Public operations backed by trusted journal and transaction providers."""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
from random import uniform

from stratbox.system.execution import (
    Completion, EffectReceipt, ExecutionContext, OperationDefinition, OperationFailure, run,
)
from stratbox.system.observability import JournalDecodeError, RequiredJournalGate

from .delivery import (
    DeliverRequest, DeliveryResult, QualifiedHandoff, QualifyDeliveryRequest, ReconcileDeliveryRequest,
    RetryPolicy, deliver_work, qualify_receipt, reconcile_work,
)
from .preparation import PrepareRequest, PreparationReport, _load_scope, prepare_page
from .runtime import NotificationRuntime

PREPARE = OperationDefinition(
    "notifications.prepare", 3, "notification-preparation-3", PrepareRequest, PreparationReport,
    possible_effects=frozenset({"notification.state_commit"}), partial_allowed=True,
)
DELIVER = OperationDefinition(
    "notifications.deliver", 3, "notification-handoff-3", DeliverRequest, DeliveryResult,
    possible_effects=frozenset({"notification.state_commit", "notification.handoff"}),
)
QUALIFY = OperationDefinition(
    "notifications.qualify", 3, "notification-handoff-receipt-3", QualifyDeliveryRequest, QualifiedHandoff,
)
RECONCILE = OperationDefinition(
    "notifications.reconcile", 2, "notification-handoff-lookup-2", ReconcileDeliveryRequest, DeliveryResult,
    possible_effects=frozenset({"notification.state_commit"}),
)


def _coverage(first: str, second: str) -> str:
    if first == second:
        return first
    if "incomplete" in {first, second}:
        return "incomplete"
    return "indeterminate"


def _combine(prior: PreparationReport | None, page: PreparationReport) -> PreparationReport:
    if prior is None:
        return page
    reasons = Counter(dict(prior.reasons))
    reasons.update(dict(page.reasons))
    return replace(
        page, examined=prior.examined + page.examined, matched=prior.matched + page.matched,
        prepared=prior.prepared + page.prepared, duplicate=prior.duplicate + page.duplicate,
        skipped=prior.skipped + page.skipped, reasons=tuple(sorted(reasons.items())),
        storage_coverage=_coverage(prior.storage_coverage, page.storage_coverage),
        capture_coverage=_coverage(prior.capture_coverage, page.capture_coverage),
        domain_coverage=_coverage(prior.domain_coverage, page.domain_coverage),
    )


def prepare(request: PrepareRequest, *, runtime: NotificationRuntime, context: ExecutionContext | None = None):
    def work(req, invocation):
        if runtime.paused:
            raise OperationFailure("notification.processing_paused")
        invocation.stage("load_checkpoint")
        initial = _load_scope(req, runtime, invocation.context, preview=False)
        report = None
        for _ in range(req.max_pages):
            invocation.check_cancelled()
            for _ in range(3):
                current = _load_scope(req, runtime, invocation.context, preview=False)
                try:
                    initial.head.check(current.cursor)
                except JournalDecodeError as error:
                    raise OperationFailure(error.code) from None
                if current.cursor.last_offset > initial.target:
                    raise OperationFailure("notification.checkpoint_conflict")
                scope = replace(current, head=initial.head, target=initial.target)
                invocation.stage("plan_page")
                page, receipt = prepare_page(req, runtime, invocation, scope)
                if receipt is None or receipt.state != "conflict":
                    break
            if receipt is not None and receipt.state in {"confirmed", "unknown"}:
                invocation.effect(EffectReceipt(
                    "notification.state_commit", receipt.state, effect_id=receipt.command_id,
                    guarantee="atomic_state", reconciliation_owner="notification_state",
                ))
            if receipt is not None and receipt.state != "confirmed":
                code = receipt.reason_code or "notification.state_commit_failed"
                blocked = replace(page, checkpoint=scope.cursor, examined=0, matched=0, prepared=0,
                                  duplicate=0, skipped=0, reasons=(), blocked_at=scope.cursor.last_offset + 1,
                                  reason_code=code)
                value = _combine(report, blocked)
                outcome = "unknown" if receipt.state == "unknown" else "partial" if value.examined else "failed"
                return Completion(value, outcome, code)
            # A final no-op read needs no additional coverage claim.
            if report is not None and page.examined == 0 and page.reason_code is None:
                return report
            report = _combine(report, page)
            if report.reason_code is not None:
                if report.reason_code == "notification.authority_unavailable" and not report.examined:
                    return Completion(report, "unknown", report.reason_code)
                return Completion(report, "partial" if report.examined else "failed", report.reason_code)
            if report.caught_up:
                break
        return report

    return run(PREPARE, request, work, context=context)


def deliver(
    request: DeliverRequest, *, runtime: NotificationRuntime, context: ExecutionContext | None = None,
    policy: RetryPolicy = RetryPolicy(), gate: RequiredJournalGate | None = None, jitter=uniform,
):
    audit_gate = runtime.audit_gate if runtime.audit_gate is not None else gate
    return run(DELIVER, request, lambda req, invocation: deliver_work(
        req, runtime, invocation, policy=policy, gate=audit_gate, jitter=jitter,
    ), context=context)


def qualify(request: QualifyDeliveryRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        invocation.stage("qualify_receipt")
        result = qualify_receipt(req.lookup, req.receipt)
        return Completion(result, "unknown", result.reason_code) if result.state == "unknown" else result

    return run(QUALIFY, request, work, context=context)


def reconcile(
    request: ReconcileDeliveryRequest, *, runtime: NotificationRuntime, context: ExecutionContext | None = None,
    policy: RetryPolicy = RetryPolicy(), jitter=uniform,
):
    return run(RECONCILE, request, lambda req, invocation: reconcile_work(
        req, runtime, invocation, policy=policy, jitter=jitter,
    ), context=context)
