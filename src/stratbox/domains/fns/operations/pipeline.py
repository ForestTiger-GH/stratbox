"""Thin operation orchestration over independently usable functional owners."""
from dataclasses import replace
import re

from stratbox.core.execution import OperationFailure, run, values
from stratbox.core.formats.archives.members import ArchiveError
from stratbox.core.runtime.dependencies import MissingExtra
from stratbox.core.operations.source.validation import source_failure, use_payload
from stratbox.shared.data.calculations import compare_observations
from stratbox.shared.data.releases import ReleaseLink
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.representation import Representation
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.shared.materials import MaterialArtifact
from stratbox.shared.source_publications import SourceAssetIdentity

from ..analytics.calculations import Calculation, calculation_from_snapshot, calculation_snapshot, net_changes, shares
from ..integration.contracts import FnsDataset
from ..integration.snapshots import dataset_from_snapshot, dataset_snapshot
from ..products.rendering import render as render_value
from ..products.views import PreparedView, prepare_view, view_from_snapshot, view_snapshot
from ..publications.legal_entities.source import SourceError
from ..tables.comparison import compare_flakes as compare_source
from ..tables.contracts import JsonFlake, SourceProjection
from ..tables.legal_entities.extraction import WorkbookBundle
from ..tables.sme.parser import FnsError
from ..tables.snapshots import projection_from_snapshot, projection_snapshot
from .contracts import ProcessedRelease


def _family_modules(series_id):
    if series_id == "fns.sme":
        from ..tables.sme.extraction import extract_json
        from ..tables.sme.projection import project_counts, validate
        from ..tables.sme.readable import readable
        from ..tables.sme.snapshots import flake_from_snapshot, flake_snapshot
        from ..integration.sme.alignment import align
        return extract_json, project_counts, validate, readable, flake_snapshot, flake_from_snapshot, align
    if series_id == "fns.1yur":
        from ..tables.legal_entities.extraction import extract_bundle
        from ..tables.legal_entities.projection import project_reported, validate
        from ..tables.legal_entities.readable import readable
        from ..tables.legal_entities.snapshots import flake_from_snapshot, flake_snapshot
        from ..integration.legal_entities.alignment import align
        return extract_bundle, project_reported, validate, readable, flake_snapshot, flake_from_snapshot, align
    raise ValueError("fns.series_unknown")


def _snapshot(value, invocation):
    if isinstance(value, (JsonFlake, WorkbookBundle)):
        return _family_modules(value.context.series_id)[4](value)
    if type(value) is SourceProjection:
        return projection_snapshot(value)
    if type(value) is Calculation:
        return calculation_snapshot(value)
    if type(value) is PreparedView:
        return view_snapshot(value)
    if type(value) is FnsDataset:
        return dataset_snapshot(value)
    return None


def _use(value, invocation, role, series_id):
    if value.context.series_id != series_id:
        raise OperationFailure("fns.source_family_mismatch")
    if isinstance(value, JsonFlake):
        lineage = value.lineage
        cells = sum(len(record.fields) for record in value.records)
    elif isinstance(value, WorkbookBundle):
        lineage = value.lineage
        cells = sum(len(sheet.cells) for _, workbook in value.members for sheet in workbook.sheets)
    else:
        lineage = value.batch.lineage
        cells = len(value.batch.observations)
    invocation.budget.charge("cells", cells)
    values.use_value(value, invocation, role, snapshot_factory=_snapshot, charge_cells=False)
    for receipt in lineage:
        invocation.use(receipt)


def execute(definition, series_id, action, request, *, context=None, transport=None, rar_reader=None):
    def work(req, invocation):
        extract, project, validate, readable, flake_snapshot, read_flake, align = _family_modules(series_id)
        invocation.stage(action)

        def source(payload, release):
            if release.series_id != series_id:
                raise OperationFailure("fns.source_family_mismatch")
            use_payload(payload, invocation, role="source_json" if series_id == "fns.sme" else "source_asset",
                limit=4_000_000 if series_id == "fns.sme" else 30_000_000)
            options = {"budget": invocation.budget, "checkpoint": invocation.check_cancelled}
            if series_id == "fns.1yur":
                if payload.data.startswith(b"Rar!") and invocation.context.profile == "managed":
                    invocation.require_provider("archive_decoder", rar_reader)
                options["rar_reader"] = rar_reader
            flake = extract(payload, release, **options)
            for receipt in flake.lineage:
                invocation.use(receipt)
            return flake

        def processed(payload, release, format):
            flake = source(payload, release)
            invocation.stage("project")
            projected = project(flake)
            invocation.stage("align")
            dataset = align(projected)
            for receipt in dataset.batch.lineage:
                invocation.use(receipt)
            invocation.stage("view")
            view = prepare_view(dataset)
            invocation.stage("render")
            representation = render_value(view, format=format, budget=invocation.budget)
            return ProcessedRelease(flake, projected, dataset, view, representation, original=payload)

        try:
            if action == "extract":
                return source(req.payload, req.release)
            if action == "process":
                return processed(req.payload, req.release, req.format)
            if action == "capture_full":
                if series_id == "fns.sme":
                    from .sme.definitions import AcquireSmeRequest
                    from .sme.operations import _acquire
                    if req.url is not None:
                        raise OperationFailure("fns.sme.fixed_endpoint_required")
                    acquired = _acquire(AcquireSmeRequest(req.release.observation_date), invocation, transport)
                else:
                    from .legal_entities.operations import _acquire
                    if not req.url:
                        raise OperationFailure("request.release_link_required")
                    acquired = _acquire(ReleaseLink(req.release.observation_date, req.url), invocation, transport)
                release = replace(req.release, captured_at=acquired.receipt.observed_at_utc)
                return replace(processed(acquired.payload, release, req.format), acquisition=acquired.receipt)
            if action in {"readable", "readable_artifact", "validate", "project", "flake_snapshot"}:
                _use(req.flake, invocation, "input_flake", series_id)
                expected = JsonFlake if series_id == "fns.sme" else WorkbookBundle
                if type(req.flake) is not expected:
                    raise ValueError("fns.flake_type_mismatch")
                if action == "readable_artifact":
                    value = req.flake
                    return MaterialArtifact(DataContract(series_id + ".readable", 1, DataRole.READABLE),
                        readable(value), tuple(invocation.used_inputs), series_id,
                        SourceAssetIdentity(series_id, value.context.issue_id, value.context.asset_id))
                return {"readable": readable, "validate": validate, "project": project, "flake_snapshot": flake_snapshot}[action](req.flake)
            if action == "compare_flakes":
                _use(req.before, invocation, "before_flake", series_id)
                _use(req.after, invocation, "after_flake", series_id)
                return compare_source(req.before, req.after)
            if action in {"align", "projection_snapshot"}:
                _use(req.projection, invocation, "input_projection", series_id)
                result = align(req.projection) if action == "align" else projection_snapshot(req.projection)
                if action == "align":
                    for receipt in result.batch.lineage:
                        invocation.use(receipt)
                return result
            if action in {"compare_datasets", "calculate_changes"}:
                for name in ("before", "after"):
                    value = getattr(req, name)
                    if type(value) is not FnsDataset:
                        raise ValueError("fns.integrated_dataset_required")
                    _use(value, invocation, name + "_dataset", series_id)
                return compare_observations(req.before.batch, req.after.batch) if action == "compare_datasets" else net_changes(
                    req.before, req.after, metric_ids=req.metric_ids)
            if action in {"calculate_shares", "dataset_snapshot", "view"}:
                if type(req.dataset) not in ({FnsDataset, Calculation} if action == "view" else {FnsDataset}):
                    raise ValueError("fns.integrated_dataset_required")
                _use(req.dataset, invocation, "input_dataset", series_id)
                if action == "dataset_snapshot":
                    return dataset_snapshot(req.dataset)
                if action == "view":
                    return prepare_view(req.dataset, metric_ids=req.metric_ids, subject_ids=req.subject_ids,
                        period_kinds=req.period_kinds, dimensions=req.dimensions)
                return shares(req.dataset, numerator_metric=req.numerator_metric, denominator_metric=req.denominator_metric,
                    numerator_dimensions=req.numerator_dimensions, denominator_dimensions=req.denominator_dimensions)
            if action == "calculation_snapshot":
                _use(req.calculation, invocation, "input_calculation", series_id)
                return calculation_snapshot(req.calculation)
            if action in {"render", "render_artifact", "view_snapshot"}:
                _use(req.view, invocation, "input_view", series_id)
                if action == "render_artifact":
                    value = req.view
                    return MaterialArtifact(DataContract(series_id + ".rendered_view", 1, DataRole.PRODUCTS),
                        render_value(value, format=req.format, budget=invocation.budget),
                        tuple(invocation.used_inputs), series_id,
                        SourceAssetIdentity(series_id, value.context.issue_id, value.context.asset_id))
                return view_snapshot(req.view) if action == "view_snapshot" else render_value(
                    req.view, format=req.format, budget=invocation.budget)
            if action.startswith("read_") and action.endswith("_snapshot"):
                invocation.use(UsedInputReceipt("retained_snapshot", req.snapshot.identity,
                    "application/vnd.stratbox.dataset+json", "reference_only", series_id))
                invocation.budget.charge("cells", sum(len(table.rows) * len(table.schema.columns)
                                                     for _, table in req.snapshot.tables))
                reader = {"read_flake_snapshot": read_flake, "read_projection_snapshot": projection_from_snapshot,
                    "read_dataset_snapshot": dataset_from_snapshot, "read_calculation_snapshot": calculation_from_snapshot,
                    "read_view_snapshot": view_from_snapshot}[action]
                result = reader(req.snapshot)
                if result.context.series_id != series_id:
                    raise OperationFailure("fns.source_family_mismatch")
                for receipt in req.snapshot.manifest.inputs:
                    invocation.use(receipt)
                return result
            raise OperationFailure("fns.operation_unknown")
        except MissingExtra:
            raise OperationFailure("provider.capability_missing") from None
        except (FnsError, SourceError, ArchiveError, ValueError) as error:
            code = str(error).split(":", 1)[0]
            if re.fullmatch(r"(?:fns|source|workbook|observations|view|dataset)\.[a-z0-9_.]{1,100}", code):
                raise OperationFailure(code) from None
            raise source_failure(error) from None

    def recorded(req, invocation):
        value = work(req, invocation)
        snapshots = []

        def snapshot_for(item):
            return values.snapshot_of(item, invocation, snapshot_factory=_snapshot)

        if isinstance(value, ProcessedRelease):
            snapshots = [(name, snapshot_for(getattr(value, name))) for name in ("flake", "projection", "dataset", "view")]
            identity = value.representation.identity
        elif isinstance(value, (MaterialArtifact, Representation)):
            identity = value.representation.identity if isinstance(value, MaterialArtifact) else value.identity
        else:
            snapshot = snapshot_for(value)
            if snapshot is not None:
                snapshots = [("value", snapshot)]
                identity = snapshot.identity
            else:
                identity = values.value_identity(value)
        parameters = {"series_id": series_id}
        for name in definition.processing.parameters:
            parameter = getattr(req, name)
            parameters[name] = values.plain(parameter)
        resources = {name: snapshot.identity.sha256 for name, snapshot in snapshots}
        if isinstance(value, ProcessedRelease) and value.original is not None:
            resources["original"] = value.original.identity.sha256
        computation = invocation.record(identity, parameters=parameters, resources=resources)
        for name, snapshot in snapshots:
            values.account_snapshot(snapshot, invocation, table_prefix=name + ":",
                                    manifest_key=name + ":manifest" if snapshot.identity != identity else None,
                                    charge_cells=False)
        invocation.account_output(identity)
        if isinstance(value, ProcessedRelease) and value.original is not None:
            invocation.account_output(value.original.identity, key="original_payload")
        if isinstance(value, MaterialArtifact):
            value = replace(value, computation=computation)
            invocation.account_output(value.identity, key="artifact_descriptor")
        return value

    return run(definition, request, recorded, context=context,
        providers={"http": transport} if "http" in definition.required_capabilities else {})
