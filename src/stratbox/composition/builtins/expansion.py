"""Explain and expand domain convenience calls into ordinary task instances."""
from __future__ import annotations

from dataclasses import dataclass, replace

from stratbox.composition.models import CollectSpec, CollectStep, OperationStep, PlanOutputRef, ScenarioDefinition
from stratbox.core.execution.handoff import prepare_input
from stratbox.shared.data.processing import DataContract, DataRole
from .common import network_retry, value_input


@dataclass(frozen=True, slots=True)
class CompositionDisposition:
    operation_id: str
    strategy: str
    reason: str


_EXPANDED = {
    "frg.scan": "Directory discovery, recognition and selection are independently scheduled.",
    "fns.sme.capture": "Acquisition and the qualified regional product have independent task outcomes.",
    "fns.1yur.capture": "Acquisition and the qualified regional product have independent task outcomes.",
    "fns.sme.process": "Extraction, projection, alignment, selection and rendering are separate tasks.",
    "fns.1yur.process": "Extraction, projection, alignment, selection and rendering are separate tasks.",
    "fns.sme.capture_full": "Acquisition precedes the complete independently scheduled interpretation route.",
    "fns.1yur.capture_full": "Acquisition precedes the complete independently scheduled interpretation route.",
    "cbr.forms.parse": "Physical extraction and source projection are separately reusable.",
    "cbr.forms.build_data": "Alignment, model admission and calculation have explicit data edges.",
    "cbr.sors.restore_from_originals": "Joint input preparation and numerical restoration are separate tasks.",
    "cbr.offices.capture": "Acquisition supplies its actual capture date to the parser.",
    "cbr.offices_reg.capture": "Acquisition and territorial interpretation are separate tasks.",
    "cbr.escrow.build_history": "Each source parser is scheduled separately before explicit collection and integration.",
    "cbr.industries.0104a.build_stream": "Each workbook is parsed separately before geography-aware integration.",
    "cbr.industries.0105a.build_stream": "Each workbook is parsed separately before geography-aware integration.",
    "cbr.industries.0104a.render_industries": "Each requested workbook is a separately qualified product task.",
    "cbr.industries.0105a.render_industries": "Each requested workbook is a separately qualified product task.",
    "minfin.capture": "Acquisition and interpretation have independent outputs and publication context.",
    "cbr.file_collector.collect_materials": "One scheduled member at a time carries the remaining aggregate byte allowance and exact dispositions.",
    "cbr.file_collector.collect_to_store": "Each streamed destination write is separately scheduled with cumulative admission and reconciliation.",
    "cbr.file_collector.collect_raw": "Each publisher original is separately scheduled with cumulative byte admission and explicit remainder.",
}
_INTEGRAL = {
    "cbr.file_collector.collect_stored_step": "One streamed material validates and commits its destination as one qualified transaction.",
    "source.receive_to_store": "A streamed receive validates and commits one original without materializing a second byte copy.",
    "rosstat.publications.acquire_to_store": "Envelope admission and staged streaming commit form one qualified storage transaction.",
    "frg.prepare_archive_to_store": "One streaming archive transaction owns its integrity check and storage confirmation.",
    "cbr.publications.acquire": "One physical read admits the same material envelope and publication identity before exposure.",
    "cbr.file_collector.archive_to_store": "One streaming archive transaction owns its complete member manifest and commit.",
    "fns.sme.parse": "The regional CSV is one exact source-local projection with its own evidence contract; full independent stages use the processing workflow.",
    "fns.1yur.parse": "The regional CSV is one exact source-local projection with its own evidence contract; full independent stages use the processing workflow.",
    "cbr.sors.prepare_from_originals": "Joint grid admission resolves inter-table economic identities and constraints as one numerical input boundary.",
    "cbr.sors.prepare_from_flakes": "Joint grid admission resolves inter-table economic identities and constraints as one numerical input boundary.",
    "cbr.industries.0104a.render_industry": "One workbook product owns its coordinated sheet set and derived-industry presentation rules.",
    "cbr.industries.0105a.render_industry": "One workbook product owns its coordinated sheet set and derived-industry presentation rules.",
}


def composition_dispositions():
    return tuple(CompositionDisposition(key, "graph", value) for key, value in sorted(_EXPANDED.items())) + tuple(
        CompositionDisposition(key, "integral", value) for key, value in sorted(_INTEGRAL.items()))


def request_step(step_id, operation_id, request, *, required=True):
    """Project a caller's typed request through the canonical port declarations."""
    from stratbox.operations.declarations import definition
    operation = definition(operation_id)
    inputs = {}
    for port in operation.processing.inputs:
        value = request
        for name in port.path.split(".") if port.path else ():
            value = getattr(value, name)
        if value is not None or port.required:
            inputs[port.name] = prepare_input(value, port.contract)
    parameters = {name: getattr(request, name) for name in operation.processing.parameters}
    options = {}
    if "http" in operation.required_capabilities and not operation.possible_effects:
        options["retry"] = network_retry(getattr(request, "retry", None))
    return OperationStep(step_id, operation_id, inputs, parameters, required=required, **options)


def _capture(operation_id, request):
    family = operation_id.removesuffix(".capture")
    if family.startswith("fns."):
        from .fns import fns_capture_workflow
        return fns_capture_workflow(family, request)
    acquire = request_step("acquire", family + ".acquire", request)
    parameters = ({"captured_on": PlanOutputRef("acquire", "capture_date")}
                  if family == "cbr.offices" else {"as_of": request.as_of})
    return ScenarioDefinition(operation_id, (acquire,
        OperationStep("parse", family + ".parse", {"source": PlanOutputRef("acquire", "source")}, parameters)),
        {"release": PlanOutputRef("parse", "release"), "representation": PlanOutputRef("parse", "representation")})


def _history(operation_id, request):
    from stratbox.operations.declarations import definition
    family = operation_id.rsplit(".", 1)[0]
    if not request.sources:
        raise ValueError("request.source_selection_empty")
    sources = request.sources
    if hasattr(request, "selection"):
        sources = tuple(replace(item, selection=request.selection) for item in sources)
    steps = [request_step("parse" + str(index), family + ".parse", item,
                           required=not request.continue_on_error)
             for index, item in enumerate(sources)]
    references = tuple(PlanOutputRef(step.step_id, "file") for step in steps)
    if family == "cbr.escrow":
        collection, element = "cbr.escrow.flakes", "cbr.escrow.parsed_file"
        parameters, result_port = {}, "dataset"
    else:
        collection, element = family + ".parsed_files", family + ".parsed_file"
        if family.endswith("0104a"):
            from stratbox.domains.cbr.publications.corporate_lending.issuance_editions import report_date_from_filename as day
        else:
            from stratbox.domains.cbr.publications.corporate_lending.debt_editions import report_date_from_cbr_0105a_filename as day
        selected = tuple(day(item.source_name) for item in sources)
        if len(set(selected)) != len(selected):
            raise ValueError("request.duplicate_release")
        parameters, result_port = {"expected_report_dates": selected}, "result"
    collection_contract = next(port.contract for port in definition(family + ".integrate_flakes").processing.inputs if port.name == "flakes")
    element_contract = next(port.contract for port in definition(family + ".parse").processing.outputs if port.name == "file")
    steps.append(CollectStep("collect", CollectSpec(references,
        collection_contract, element_contract,
        allow_partial=request.continue_on_error)))
    steps.append(OperationStep("integrate", family + ".integrate_flakes",
        {"flakes": PlanOutputRef("collect", "value")}, parameters))
    outputs = {"dataset" if family == "cbr.escrow" else "result": PlanOutputRef("integrate", result_port)}
    if family != "cbr.escrow":
        outputs["stream"] = PlanOutputRef("integrate", "stream")
    return ScenarioDefinition(operation_id, tuple(steps), outputs,
                              policy="continue" if request.continue_on_error else "fail_fast")


def expand_operation(operation_id, request):
    """Return a graph for declared convenience calls, otherwise ``None``.

    The normal SDK binds the typed request first. Graph results retain named
    outputs and every operation outcome instead of manufacturing a successful
    combined object when a constituent task fails.
    """
    if operation_id not in _EXPANDED:
        return None
    if operation_id in {"cbr.file_collector.collect_materials", "cbr.file_collector.collect_to_store", "cbr.file_collector.collect_raw"}:
        return _collection(operation_id, request)
    if operation_id in {"fns.sme.capture", "fns.1yur.capture", "cbr.offices.capture", "cbr.offices_reg.capture"}:
        return _capture(operation_id, request)
    if operation_id.startswith("fns."):
        from .fns import fns_workflow
        return fns_workflow(operation_id.rsplit(".", 1)[0], release=request.release,
            payload=getattr(request, "payload", None), url=getattr(request, "url", None), format=request.format)
    if operation_id == "frg.scan":
        return ScenarioDefinition(operation_id, (
            request_step("discover", "frg.discover", request),
            OperationStep("inspect", "frg.inspect", {"index": PlanOutputRef("discover", "index")}),
            OperationStep("select", "frg.select", {"inventory": PlanOutputRef("inspect", "inventory")}),
        ), {"index": PlanOutputRef("discover", "index"), "inventory": PlanOutputRef("inspect", "inventory"),
            "selections": PlanOutputRef("select", "selections")})
    if operation_id == "minfin.capture":
        from .minfin import minfin_workflow
        return minfin_workflow(request.asset.source_id, family_id=request.asset.family_id,
            format=request.asset.format, asset=request.asset,
            parameters={"max_bytes": request.max_bytes, "max_cells": request.max_cells,
                        "member": request.member, "selected_sheets": request.selected_sheets})
    if operation_id == "cbr.forms.parse":
        return ScenarioDefinition(operation_id, (
            OperationStep("extract", "cbr.forms.extract", {"source": value_input(request.payload, "material.payload")}, {"key": request.key}),
            OperationStep("normalize", "cbr.forms.normalize", {"flakes": PlanOutputRef("extract", "flakes")}),
        ), {"snapshot": PlanOutputRef("normalize", "snapshot")})
    if operation_id == "cbr.forms.build_data":
        from dataclasses import asdict
        from stratbox.shared.data.tables import table_identity
        from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
        source_version = ByteIdentity.of(canonical_manifest_bytes(tuple(
            {"key": asdict(item.key), "fields": dict(item.physical_fields),
             "tables": asdict(table_identity((("dbf_rows", item.rows),)))} for item in request.snapshots))).sha256
        return ScenarioDefinition(operation_id, (
            OperationStep("align", "cbr.forms.align", {"snapshots": value_input(request.snapshots, "cbr.forms.snapshots", "extracts")},
                {"dataset_id": "cbr.forms.model-source", "version_id": source_version, "periods": request.periods}),
            OperationStep("prepare", "cbr.forms.prepare_model_inputs", {"batch": PlanOutputRef("align", "batch")}),
            OperationStep("calculate", "cbr.forms.calculate", {"inputs": PlanOutputRef("prepare", "inputs")},
                {"banks": request.banks, "model": request.model, "selection_profile": request.selection_profile}),
        ), {"data": PlanOutputRef("calculate", "data")})
    if operation_id == "cbr.sors.restore_from_originals":
        return ScenarioDefinition(operation_id, (
            request_step("prepare", "cbr.sors.prepare_from_originals", request),
            OperationStep("restore", "cbr.sors.restore", {"bundle": PlanOutputRef("prepare", "bundle")}, {"config": request.config}),
        ), {"result": PlanOutputRef("restore", "result")})
    if operation_id.endswith((".build_stream", ".build_history")):
        return _history(operation_id, request)
    if operation_id.endswith(".render_industries"):
        family = operation_id.rsplit(".", 1)[0]
        if not request.industry_codes or len(set(request.industry_codes)) != len(request.industry_codes):
            raise ValueError("request.industry_selection_invalid")
        steps = []
        for index, code in enumerate(request.industry_codes):
            if family.endswith("0104a"):
                from stratbox.domains.cbr.operations.corporate_lending.issuance.contracts import IssuanceWorkbookRequest
                item = IssuanceWorkbookRequest(request.stream, code, True, request.include_metadata_sheet)
            else:
                from stratbox.domains.cbr.operations.corporate_lending.debt.contracts import RenderIndustryRequest
                from stratbox.domains.cbr.products.corporate_lending.debt.contracts import Cbr0105ADebtCorpIndustryWorkbookRequest
                item = RenderIndustryRequest(request.stream, Cbr0105ADebtCorpIndustryWorkbookRequest(code, True, request.include_metadata_sheet))
            steps.append(request_step("industry" + str(index), family + ".render_industry", item))
        return ScenarioDefinition(operation_id, tuple(steps),
            {code: PlanOutputRef(step.step_id, "workbook") for code, step in zip(request.industry_codes, steps)})
    raise ValueError("workflow.expansion_missing")


def _collection(operation_id, request):
    from stratbox.domains.cbr.publications.collection.contracts import CollectToStoreRequest
    stored = operation_id.endswith("collect_to_store")
    raw = operation_id.endswith("collect_raw")
    selected = request.selection.source_ids if stored else request.source_ids if raw else request.items
    if not selected or len(selected) > 10000:
        raise ValueError("cbr.collection.selection_invalid")
    keys = tuple(selected) if stored or raw else tuple(item.key for item in selected)
    if len(set(keys)) != len(keys):
        raise ValueError("cbr.collection.selection_invalid")
    if stored and (set(request.destinations) != set(keys)
                   or len({item.locator for item in request.destinations.values()}) != len(keys)):
        raise ValueError("request.archive_destinations_invalid")
    policy = request.selection if stored else request
    operation = "cbr.file_collector.collect_stored_step" if stored else "cbr.file_collector.collect_raw_step" if raw else "cbr.file_collector.collect_material_step"
    steps = []
    for index, item in enumerate(selected):
        parameters = {"max_batch_bytes": policy.max_batch_bytes,
                      "continue_on_error": policy.continue_on_error, "final": index == len(selected) - 1}
        if stored:
            parameters["request"] = CollectToStoreRequest(replace(request.selection, source_ids=(item,)),
                                                          {item: request.destinations[item]})
        elif raw:
            parameters["request"] = replace(request, source_ids=(item,))
        else:
            parameters["item"] = item
        inputs = {} if not steps else {"previous": PlanOutputRef(steps[-1].step_id, "collection")}
        steps.append(OperationStep("member" + str(index), operation, inputs, parameters,
                                   retry=network_retry(getattr(policy, "retry", None))))
    outputs = {name: PlanOutputRef(steps[-1].step_id, name) for name in
               (("collection", "files", "manifest", "archive_members") if stored or raw else
                ("collection", "manifest", "archive_members"))}
    return ScenarioDefinition(operation_id, tuple(steps), outputs)
