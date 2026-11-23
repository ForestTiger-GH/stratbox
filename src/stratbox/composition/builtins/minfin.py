"""Minfin acquisition and extraction with explicit publication context."""
from __future__ import annotations

from stratbox.composition.models import OperationStep, PlanOutputRef, ScenarioDefinition
from .common import network_retry, value_input


def minfin_workflow(series_id, *, family_id, format, payload=None, asset=None, publication=None,
                    parameters=None, extract=True):
    parameters = dict(parameters or {})
    steps, outputs = [], {}
    if payload is None:
        if asset is None:
            raise ValueError("workflow.asset_required")
        if asset.source_id != series_id:
            raise ValueError("workflow.source_mismatch")
        from stratbox.domains.minfin.publications.context import context_for
        publication = context_for(asset)
        steps.append(OperationStep("acquire", "minfin.acquire", {"asset": value_input(asset, "minfin.asset")},
                                   {key: parameters[key] for key in ("max_bytes", "deadline_seconds") if key in parameters}, retry=network_retry()))
        original = PlanOutputRef("acquire", "payload")
    else:
        original = value_input(payload, "source.payload", "originals")
    if steps:
        outputs["original"] = original
    if extract:
        if format in {"pdf", "docx", "doc"}:
            if format == "doc":
                raise ValueError("minfin.document.legacy_doc_unsupported")
            if publication is None:
                raise ValueError("workflow.publication_context_required")
            steps.append(OperationStep("extract", "minfin.extract_document", {"payload": original},
                {"family_id": family_id, "publication": publication}))
            outputs["extract"] = PlanOutputRef("extract", "document")
        else:
            selected = {key: parameters[key] for key in
                        ("member", "selected_sheets", "max_cells", "csv_encoding") if key in parameters}
            steps.append(OperationStep("extract", "minfin.extract", {"original": original},
                {"family_id": family_id, "format": format, "publication": publication, **selected}))
            outputs["extract"] = PlanOutputRef("extract", "extract")
    if not steps:
        # The supplied bytes are already a usable retained input. A pure
        # zero-step graph can expose them without claiming a storage effect.
        outputs["original"] = original
    return ScenarioDefinition(series_id + ".processing", tuple(steps), outputs)
