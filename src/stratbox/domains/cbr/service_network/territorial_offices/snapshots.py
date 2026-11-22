"""Territorial release and unresolved-block persistence without inference."""

from datetime import date

from stratbox.core.execution import Completion, OperationFailure, run
from stratbox.shared.data.processing import DataContract
from stratbox.shared.data.snapshots import ColumnSchema, DatasetSnapshot, ScalarType, SnapshotCoverage, TableSchema, TypedTable
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity
from stratbox.domains.cbr.service_network.snapshots import (
    acquisition_from, acquisition_value, release_from_snapshot, release_snapshot,
)

from .definitions import DATASET, RESTORE, SNAPSHOT, OfficesRegCandidates
from .parser import CaptureError
from .representation import validate_csv, validate_source_details
from .operations import _observations

_PROFILE = "cbr.offices_reg.wide-csv"
_CANDIDATES = DataContract("cbr.offices_reg.candidates.snapshot", 1)
_T, _I, _D = ScalarType.TEXT, ScalarType.INTEGER, ScalarType.DATE
_META = TableSchema(DataContract("cbr.offices_reg.candidate.metadata", 1), tuple(ColumnSchema(*x) for x in (
    ("source_sha256", _T), ("source_size", _I), ("as_of", _D), ("sheet", _T, True),
    ("national_row", _I, True), ("last_row", _I, True),
    ("acquisition", _T, True),
)))
_BLOCKS = TableSchema(DataContract("cbr.offices_reg.candidate.blocks", 1), tuple(ColumnSchema(*x) for x in (
    ("ordinal", _I), ("sheet", _T), ("national_row", _I), ("territory_column", _I),
)), ("ordinal",))


def _validate_release(value):
    fragment = value.qualification is not None and value.qualification.scope == "selected_fragment"
    literal = value.qualification is not None and value.qualification.scope == "unqualified_csv"
    if validate_csv(value.representation.data, minimum_rows=1 if fragment or literal else 30) != value.row_count:
        raise ValueError("cbr.offices_reg.row_count_invalid")
    if value.batch is not None and any(item.period.kind != "as_of" or item.period.as_of != value.as_of
                                       for item in value.batch.observations):
        raise ValueError("cbr.offices_reg.period_invalid")
    if value.source_details is not None:
        selection = validate_source_details(value.source_details, value.representation.data)
        observations, excluded = _observations(value.representation.data, value.as_of,
                                               unresolved=selection["unresolved_fields"])
        if (fragment != (selection["scope"] == "selected_fragment")
                or observations != (value.batch.observations if value.batch is not None else None)
                or excluded != value.qualification.excluded_fields):
            raise ValueError("cbr.offices_reg.evidence_mismatch")
    elif value.batch is not None or not literal:
        raise ValueError("cbr.offices_reg.evidence_missing")


def _candidate_snapshot(value, dataset_id, version_id):
    if (type(value.as_of) is not date or value.as_of.day != 1 or value.as_of.year < 2019
            or not isinstance(value.blocks, tuple) or not value.blocks or len(set(value.blocks)) != len(value.blocks)
            or any(not isinstance(sheet, str) or not sheet or type(row) is not int or type(col) is not int
                   or not 1 <= row <= 1_048_576 or not 1 <= col <= 16_384 for sheet, row, col in value.blocks)):
        raise ValueError("cbr.offices_reg.candidates_invalid")
    if (not isinstance(value.inputs, tuple)
            or not any(item.identity == value.source_identity and item.role == "source_workbook" for item in value.inputs)
            or (value.acquisition is not None and value.acquisition.identity != value.source_identity)):
        raise ValueError("cbr.offices_reg.candidate_source_missing")
    if value.requested_sheet is not None and any(sheet != value.requested_sheet for sheet, _, _ in value.blocks):
        raise ValueError("cbr.offices_reg.candidate_selection_mismatch")
    if value.requested_national_row is not None and any(row != value.requested_national_row for _, row, _ in value.blocks):
        raise ValueError("cbr.offices_reg.candidate_selection_mismatch")
    if value.requested_last_row is not None and (type(value.requested_last_row) is not int or not 1 <= value.requested_last_row <= 1_048_576):
        raise ValueError("cbr.offices_reg.candidate_selection_mismatch")
    metadata = TypedTable(_META, ((value.source_identity.sha256, value.source_identity.size, value.as_of,
        value.requested_sheet, value.requested_national_row, value.requested_last_row,
        acquisition_value(value.acquisition)),))
    blocks = TypedTable(_BLOCKS, tuple((index, *block) for index, block in enumerate(value.blocks)))
    return DatasetSnapshot.build(dataset_id, version_id, _CANDIDATES,
        (("metadata", metadata), ("blocks", blocks)),
        coverage=SnapshotCoverage("partial", "Source block selection is unresolved; all discovered candidates are retained."),
        inputs=value.inputs)


def _candidates_from(snapshot):
    if (not snapshot.complete or tuple(name for name, _ in snapshot.tables) != ("metadata", "blocks")
            or snapshot.table("metadata").schema != _META or snapshot.table("blocks").schema != _BLOCKS
            or len(snapshot.table("metadata").rows) != 1):
        raise ValueError("cbr.offices_reg.candidates_invalid")
    sha, size, day, sheet, national, last, acquisition = snapshot.table("metadata").rows[0]
    blocks = snapshot.table("blocks").rows
    if any(row[0] != index for index, row in enumerate(blocks)):
        raise ValueError("cbr.offices_reg.candidates_invalid")
    value = OfficesRegCandidates(ByteIdentity(sha, size), tuple(tuple(row[1:]) for row in blocks),
        day, sheet, national, last, snapshot.manifest.inputs, acquisition_from(acquisition))
    if _candidate_snapshot(value, snapshot.manifest.dataset_id, snapshot.manifest.version_id).identity != snapshot.identity:
        raise ValueError("cbr.offices_reg.candidates_identity_mismatch")
    return value


def snapshot_release(request, *, context=None):
    def work(req, invocation):
        invocation.stage("encode_release")
        try:
            if isinstance(req.release, OfficesRegCandidates):
                value = _candidate_snapshot(req.release, req.dataset_id, req.version_id)
            else:
                value = release_snapshot(req.release, dataset=DATASET, profile=_PROFILE,
                    dataset_id=req.dataset_id, version_id=req.version_id, checkpoint=invocation.check_cancelled)
                _validate_release(req.release)
        except (ValueError, TypeError, KeyError, CaptureError):
            raise OperationFailure("cbr.offices_reg.snapshot_invalid") from None
        for receipt in req.release.inputs:
            invocation.use(receipt)
        invocation.record(value.identity)
        return value
    return run(SNAPSHOT, request, work, context=context)


def restore_release(request, *, context=None):
    def work(req, invocation):
        invocation.stage("restore_release")
        try:
            if req.manifest.contract == _CANDIDATES:
                value = _candidates_from(req)
            else:
                value = release_from_snapshot(req, dataset=DATASET, profile=_PROFILE, checkpoint=invocation.check_cancelled)
                _validate_release(value)
        except (ValueError, TypeError, KeyError, CaptureError):
            raise OperationFailure("cbr.offices_reg.snapshot_invalid") from None
        invocation.use(UsedInputReceipt("retained_snapshot", req.identity,
            "application/vnd.stratbox.dataset+json", "inline", req.manifest.dataset_id))
        for receipt in value.inputs:
            invocation.use(receipt)
        return Completion(value, "partial", "source.xlsx_national_total_ambiguous") if isinstance(value, OfficesRegCandidates) else value
    return run(RESTORE, request, work, context=context)
