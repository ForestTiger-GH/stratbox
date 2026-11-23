"""Family-typed FNS stages using the common execution and value processor.

Each publication family supplies its own extraction, interpretation, acquisition
and snapshot methods. Adding a family does not edit a central series dispatcher.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import re
from typing import Callable, Generic, TypeVar

from stratbox.core.execution import OperationFailure, run, values
from stratbox.core.formats.archives.members import ArchiveError
from stratbox.core.runtime.dependencies import MissingExtra
from stratbox.core.operations.source.validation import source_failure, use_payload
from stratbox.shared.data.calculations import compare_observations
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.representation import Representation
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.shared.evidence import AcquiredSource
from stratbox.shared.materials import MaterialArtifact
from stratbox.shared.source_publications import SourceAssetIdentity

from ..analytics.calculations import Calculation, calculation_from_snapshot, calculation_snapshot, net_changes, shares
from ..integration.contracts import FnsDataset
from ..integration.snapshots import dataset_from_snapshot, dataset_snapshot
from ..products.rendering import render as render_value
from ..products.views import PreparedView, prepare_view, view_from_snapshot, view_snapshot
from ..publications.contracts import ReleaseContext
from ..publications.legal_entities.source import SourceError
from ..tables.comparison import compare_flakes as compare_source
from ..tables.contracts import JsonFlake, SourceProjection
from ..tables.legal_entities.extraction import WorkbookBundle
from ..tables.sme.parser import FnsError
from ..tables.snapshots import projection_from_snapshot, projection_snapshot
from . import contracts as C

Flake = TypeVar("Flake")


@dataclass(frozen=True, slots=True)
class FamilyMethods(Generic[Flake]):
    """Concrete scientific methods owned by one publication family."""
    series_id: str
    flake_type: type[Flake]
    input_limit: int
    extract: Callable[..., Flake]
    project: Callable[[Flake], SourceProjection]
    validate: Callable
    readable: Callable[[Flake], Representation]
    snapshot: Callable[[Flake], DatasetSnapshot]
    restore: Callable[[DatasetSnapshot], Flake]
    align: Callable[[SourceProjection], FnsDataset]
    acquire: Callable[..., AcquiredSource]
    physical_cells: Callable[[Flake], int]

    def __post_init__(self):
        if (not self.series_id.startswith("fns.") or not isinstance(self.flake_type, type)
                or type(self.input_limit) is not int or self.input_limit <= 0
                or any(not callable(method) for method in (self.extract, self.project, self.validate,
                    self.readable, self.snapshot, self.restore, self.align, self.acquire, self.physical_cells))):
            raise ValueError("fns.family_methods_invalid")


class FamilyOperations(Generic[Flake]):
    """Independent typed stages; family semantics remain explicit methods."""
    def __init__(self, family: FamilyMethods[Flake]):
        self.family = family

    def admit(self, requirement, instance, value):
        from stratbox.core.registry.requirements import DomainAdmission
        try:
            if getattr(value, "context", None) is None:
                return DomainAdmission("conditional", ("fns.profile.typed_source_required",))
            if value.context.series_id != self.family.series_id or value.context.series_id != instance.source_id:
                return DomainAdmission("rejected", ("fns.profile.source_context_mismatch",))
            if instance.issue_id and value.context.issue_id != instance.issue_id:
                return DomainAdmission("rejected", ("fns.profile.source_context_mismatch",))
            if instance.report_date and value.context.observation_date.isoformat() != instance.report_date:
                return DomainAdmission("rejected", ("fns.profile.observation_date_mismatch",))
            if instance.layout_edition:
                return DomainAdmission("conditional", ("fns.profile.layout_edition_evidence_required",))
            batch = getattr(value, "batch", None)
            if instance.perimeter:
                if batch is None:
                    return DomainAdmission("conditional", ("fns.profile.perimeter_evidence_required",))
                if {item.perimeter for item in batch.observations} != {instance.perimeter}:
                    return DomainAdmission("rejected", ("fns.profile.perimeter_mismatch",))
            if instance.semantic_profile_edition:
                editions = {use.coordinate.semantic_profile_edition for use in batch.source_uses} if batch is not None else set()
                if not editions:
                    return DomainAdmission("conditional", ("fns.profile.semantic_edition_evidence_required",))
                if editions != {instance.semantic_profile_edition}:
                    return DomainAdmission("rejected", ("fns.profile.semantic_edition_mismatch",))
            if type(value) is self.family.flake_type:
                report = self.family.validate(value)
                return DomainAdmission("admitted" if report.valid else "rejected",
                    tuple(dict.fromkeys(item.code for item in report.findings)))
            if isinstance(value, (SourceProjection, FnsDataset, Calculation, PreparedView)):
                values.snapshot_of(value, snapshot_factory=self._snapshot)
                return DomainAdmission("admitted", ("fns.profile.qualified_observation_scope",))
        except (TypeError, ValueError) as error:
            return DomainAdmission("rejected", (str(error),))
        return DomainAdmission("conditional", ("fns.profile.typed_source_required",))

    def _snapshot(self, value, invocation):
        if type(value) is self.family.flake_type:
            return self.family.snapshot(value)
        if type(value) is SourceProjection:
            return projection_snapshot(value)
        if type(value) is Calculation:
            return calculation_snapshot(value)
        if type(value) is PreparedView:
            return view_snapshot(value)
        if type(value) is FnsDataset:
            return dataset_snapshot(value)
        return None

    def _use(self, value, invocation, role):
        if value.context.series_id != self.family.series_id:
            raise OperationFailure("fns.source_family_mismatch")
        if type(value) is self.family.flake_type:
            cells, lineage = self.family.physical_cells(value), value.lineage
        else:
            cells, lineage = len(value.batch.observations), value.batch.lineage
        invocation.budget.charge("cells", cells)
        values.use_value(value, invocation, role, snapshot_factory=self._snapshot, charge_cells=False)
        for receipt in lineage:
            invocation.use(receipt)

    def _flake(self, value, invocation, role="input_flake"):
        if type(value) is not self.family.flake_type:
            raise ValueError("fns.flake_type_mismatch")
        self._use(value, invocation, role)
        return value

    def _dataset(self, value, invocation, role="input_dataset", *, allow_calculation=False):
        if type(value) not in ({FnsDataset, Calculation} if allow_calculation else {FnsDataset}):
            raise ValueError("fns.integrated_dataset_required")
        self._use(value, invocation, role)
        return value

    def _source(self, payload, release: ReleaseContext, invocation, rar_reader):
        if release.series_id != self.family.series_id:
            raise OperationFailure("fns.source_family_mismatch")
        use_payload(payload, invocation, role="source_asset", limit=self.family.input_limit)
        flake = self.family.extract(payload, release, invocation=invocation, rar_reader=rar_reader)
        for receipt in flake.lineage:
            invocation.use(receipt)
        return flake

    def _processed(self, payload, release, format, invocation, rar_reader):
        flake = self._source(payload, release, invocation, rar_reader)
        invocation.stage("project")
        projected = self.family.project(flake)
        invocation.stage("align")
        dataset = self.family.align(projected)
        for receipt in dataset.batch.lineage:
            invocation.use(receipt)
        invocation.stage("view")
        view = prepare_view(dataset)
        invocation.stage("render")
        representation = render_value(view, format=format, budget=invocation.budget)
        return C.ProcessedRelease(flake, projected, dataset, view, representation, original=payload)

    def _read(self, request, invocation, reader):
        values.use_value(request.snapshot, invocation, "retained_snapshot", include_lineage=True)
        result = reader(request.snapshot)
        if result.context.series_id != self.family.series_id:
            raise OperationFailure("fns.source_family_mismatch")
        return result

    def extract(self, req: C.ExtractRequest, inv, *, rar_reader=None, **_):
        return self._source(req.payload, req.release, inv, rar_reader)

    def readable(self, req: C.FlakeRequest, inv, **_):
        return self.family.readable(self._flake(req.flake, inv))

    def validate(self, req: C.FlakeRequest, inv, **_):
        return self.family.validate(self._flake(req.flake, inv))

    def project(self, req: C.FlakeRequest, inv, **_):
        return self.family.project(self._flake(req.flake, inv))

    def flake_snapshot(self, req: C.FlakeRequest, inv, **_):
        return self.family.snapshot(self._flake(req.flake, inv))

    def compare_flakes(self, req: C.CompareFlakesRequest, inv, **_):
        return compare_source(self._flake(req.before, inv, "before_flake"),
                              self._flake(req.after, inv, "after_flake"))

    def align(self, req: C.ProjectionRequest, inv, **_):
        self._use(req.projection, inv, "input_projection")
        result = self.family.align(req.projection)
        for receipt in result.batch.lineage:
            inv.use(receipt)
        return result

    def projection_snapshot(self, req: C.ProjectionRequest, inv, **_):
        self._use(req.projection, inv, "input_projection")
        return projection_snapshot(req.projection)

    def compare_datasets(self, req: C.CompareDatasetsRequest, inv, **_):
        before = self._dataset(req.before, inv, "before_dataset")
        after = self._dataset(req.after, inv, "after_dataset")
        return compare_observations(before.batch, after.batch)

    def calculate_changes(self, req: C.ChangesRequest, inv, **_):
        before = self._dataset(req.before, inv, "before_dataset")
        after = self._dataset(req.after, inv, "after_dataset")
        return net_changes(before, after, metric_ids=req.metric_ids)

    def calculate_shares(self, req: C.SharesRequest, inv, **_):
        return shares(self._dataset(req.dataset, inv), numerator_metric=req.numerator_metric,
            denominator_metric=req.denominator_metric, numerator_dimensions=req.numerator_dimensions,
            denominator_dimensions=req.denominator_dimensions)

    def dataset_snapshot(self, req: C.DatasetRequest, inv, **_):
        return dataset_snapshot(self._dataset(req.dataset, inv))

    def view(self, req: C.ViewRequest, inv, **_):
        return prepare_view(self._dataset(req.dataset, inv, allow_calculation=True),
            metric_ids=req.metric_ids, subject_ids=req.subject_ids, period_kinds=req.period_kinds, dimensions=req.dimensions)

    def calculation_snapshot(self, req: C.CalculationRequest, inv, **_):
        self._use(req.calculation, inv, "input_calculation")
        return calculation_snapshot(req.calculation)

    def view_snapshot(self, req: C.ViewValueRequest, inv, **_):
        self._use(req.view, inv, "input_view")
        return view_snapshot(req.view)

    def render(self, req: C.RenderRequest, inv, **_):
        self._use(req.view, inv, "input_view")
        return render_value(req.view, format=req.format, budget=inv.budget)

    def _artifact(self, value, representation, inv, role):
        return MaterialArtifact(DataContract(self.family.series_id + "." + role, 1,
            DataRole.READABLE if role == "readable" else DataRole.PRODUCTS), representation,
            tuple(inv.used_inputs), self.family.series_id,
            SourceAssetIdentity(self.family.series_id, value.context.issue_id, value.context.asset_id))

    def readable_artifact(self, req: C.FlakeRequest, inv, **_):
        value = self._flake(req.flake, inv)
        return self._artifact(value, self.family.readable(value), inv, "readable")

    def render_artifact(self, req: C.RenderRequest, inv, **_):
        self._use(req.view, inv, "input_view")
        return self._artifact(req.view, render_value(req.view, format=req.format, budget=inv.budget), inv, "rendered_view")

    def read_flake_snapshot(self, req: C.SnapshotRequest, inv, **_):
        return self._read(req, inv, self.family.restore)

    def read_projection_snapshot(self, req: C.SnapshotRequest, inv, **_):
        return self._read(req, inv, projection_from_snapshot)

    def read_dataset_snapshot(self, req: C.SnapshotRequest, inv, **_):
        return self._read(req, inv, dataset_from_snapshot)

    def read_calculation_snapshot(self, req: C.SnapshotRequest, inv, **_):
        return self._read(req, inv, calculation_from_snapshot)

    def read_view_snapshot(self, req: C.SnapshotRequest, inv, **_):
        return self._read(req, inv, view_from_snapshot)

    def process(self, req: C.ProcessRequest, inv, *, rar_reader=None, **_):
        return self._processed(req.payload, req.release, req.format, inv, rar_reader)

    def capture_full(self, req: C.CaptureFullRequest, inv, *, transport=None, rar_reader=None):
        acquired = self.family.acquire(req, invocation=inv, transport=transport)
        release = replace(req.release, captured_at=acquired.receipt.observed_at_utc)
        return replace(self._processed(acquired.payload, release, req.format, inv, rar_reader), acquisition=acquired.receipt)

    def _recorded(self, value, req, definition, invocation):
        def snapshot_for(item):
            return values.snapshot_of(item, invocation, snapshot_factory=self._snapshot)
        if isinstance(value, C.ProcessedRelease):
            snapshots = [(name, snapshot_for(getattr(value, name))) for name in ("flake", "projection", "dataset", "view")]
            identity = value.representation.identity
        elif isinstance(value, (MaterialArtifact, Representation)):
            snapshots = []
            identity = value.representation.identity if isinstance(value, MaterialArtifact) else value.identity
        else:
            snapshot = snapshot_for(value)
            snapshots = [("value", snapshot)] if snapshot is not None else []
            identity = snapshot.identity if snapshot is not None else values.value_identity(value)
        parameters = {"series_id": self.family.series_id,
                      **{name: values.plain(getattr(req, name)) for name in definition.processing.parameters}}
        resources = {name: snapshot.identity.sha256 for name, snapshot in snapshots}
        if isinstance(value, C.ProcessedRelease):
            resources["original"] = value.original.identity.sha256
        computation = invocation.record(identity, parameters=parameters, resources=resources)
        for name, snapshot in snapshots:
            values.account_snapshot(snapshot, invocation, table_prefix=name + ":",
                manifest_key=name + ":manifest" if snapshot.identity != identity else None, charge_cells=False)
        invocation.account_output(identity)
        if isinstance(value, C.ProcessedRelease):
            invocation.account_output(value.original.identity, key="original_payload")
        if isinstance(value, MaterialArtifact):
            value = replace(value, computation=computation)
            invocation.account_output(value.identity, key="artifact_descriptor")
        return value

    def invoke(self, definition, stage, request, *, context=None, transport=None, rar_reader=None):
        def work(req, invocation):
            invocation.stage(stage.__name__)
            try:
                value = stage(req, invocation, transport=transport, rar_reader=rar_reader)
                return self._recorded(value, req, definition, invocation)
            except MissingExtra:
                raise OperationFailure("provider.capability_missing") from None
            except (FnsError, SourceError, ArchiveError, ValueError) as error:
                code = str(error).split(":", 1)[0]
                if re.fullmatch(r"(?:fns|source|workbook|observations|view|dataset)\.[a-z0-9_.]{1,100}", code):
                    raise OperationFailure(code) from None
                raise source_failure(error) from None
        return run(definition, request, work, context=context,
            providers={"http": transport} if "http" in definition.required_capabilities else {})
