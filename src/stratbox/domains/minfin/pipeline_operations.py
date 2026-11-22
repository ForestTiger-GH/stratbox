"""Independent Minfin processing transitions over the existing core runner."""
from __future__ import annotations

from stratbox.core.execution import ExecutionContext, OperationFailure, run

from . import pipeline_definitions as D
from .pipeline_models import (
    BuildFlakeRequest, RenderFlakeRequest, SummaryRequest, UpdateRequest,
    NoticeRequest, NoticePreparation,
)
from .flakes import build_flake, render_flake_csv
from .summaries import prepare_notification, summarize
from .updates import assess_updates


def _wrap_error(exc: ValueError):
    code = str(exc)
    if code.startswith("minfin.") and len(code) <= 95 and all(c.isalnum() or c in "_." for c in code):
        raise OperationFailure(code) from None
    raise OperationFailure("minfin.pipeline_invalid") from None


def plan_updates(request: UpdateRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        invocation.stage("assess_publisher_markers")
        try:
            return assess_updates(req)
        except ValueError as exc:
            _wrap_error(exc)
    return run(D.PLAN_UPDATES, request, work, context=context)


def build_source_flake(request: BuildFlakeRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        invocation.stage("clean_source_table")
        try:
            return build_flake(req)
        except ValueError as exc:
            _wrap_error(exc)
    return run(D.BUILD_FLAKE, request, work, context=context)


def render_source_flake(request: RenderFlakeRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        try:
            return render_flake_csv(req)
        except ValueError as exc:
            _wrap_error(exc)
    return run(D.RENDER_FLAKE, request, work, context=context)


def calculate_headlines(request: SummaryRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        invocation.stage("calculate_source_headlines")
        try:
            return summarize(req)
        except ValueError as exc:
            _wrap_error(exc)
    return run(D.SUMMARIZE, request, work, context=context)


def prepare_notice_facts(request: NoticeRequest, *, context: ExecutionContext | None = None):
    def work(req, invocation):
        invocation.stage("qualify_notification_candidate")
        try:
            facts, reason = prepare_notification(req)
        except ValueError as exc:
            _wrap_error(exc)
        return NoticePreparation("ready" if facts is not None else "skipped", facts, reason)
    return run(D.PREPARE_NOTICE, request, work, context=context)

__all__ = ("plan_updates", "build_source_flake", "render_source_flake", "calculate_headlines", "prepare_notice_facts")