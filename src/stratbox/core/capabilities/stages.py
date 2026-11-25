"""Independent standard stages; every effect belongs to the common executor."""
from __future__ import annotations

import base64
import csv
from dataclasses import replace
from io import StringIO
from typing import Mapping

from stratbox.core.execution.contracts import EffectReceipt, OperationFailure
from stratbox.core.storage.datasets import codec
from stratbox.shared.data import documents, observation_snapshots, views, workbooks
from stratbox.shared.data.assessment import (ValueEvidence, assessment_value, evidence_from,
    observation_coordinate, observation_scope, selected_evidence, value_evidence)
from stratbox.shared.data.observations import ObservationBatch, SubjectRef, MetricRef
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.representation import Representation
from stratbox.shared.data.snapshots import (DatasetSnapshot, ColumnSchema, ScalarType, TableSchema,
    TypedTable, manifest_value)
from stratbox.shared.data.stages import (IntegratedBatch, MaterialMember, ObservationComparison,
    ObservationDifference, QualifiedMaterial)
from stratbox.shared.evidence import SourcePayload, StoredBytesReceipt, UsedInputReceipt
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes

DEFAULT_BYTES = 32 * 1024 * 1024


def _limit(request, name="max_bytes", default=DEFAULT_BYTES):
    value = request.get(name, default)
    if type(value) is not int or not 0 < value <= 512 * 1024 * 1024:
        raise OperationFailure("stage.limit_invalid")
    return value


def _representation(data, invocation, profile, *, max_bytes=DEFAULT_BYTES, evidence=None):
    if len(data) > max_bytes:
        raise OperationFailure("stage.output_size_limit")
    result = Representation(profile, 1, "application/json", data, "utf-8", evidence)
    invocation.account_output(result.identity)
    return result


def material_preserve(request, invocation):
    from stratbox.core.capabilities.materials import store_commit
    value = request["material"]
    if isinstance(value, QualifiedMaterial):
        value = value.material
    return store_commit({**request, "material": value}, invocation)


def archive_members(request, invocation):
    from stratbox.core.formats.archives.members import ArchiveLimits, extract_members
    payload = request["material"]
    names = tuple(request.get("names", ()))
    limits = ArchiveLimits(request.get("max_members", 250), _limit(request, "max_unpacked_bytes"),
        _limit(request, "max_member_bytes"), _limit(request))
    reader = invocation.provider("archive_reader") if payload.data.startswith(b"Rar!") else None
    extracted = extract_members(payload.data, select=(lambda available: names or available),
        limits=limits, rar_reader=reader, budget=invocation.budget, checkpoint=invocation.check_cancelled)
    if names and set(extracted) != set(names):
        raise OperationFailure("archive.requested_member_missing")
    result = []
    for name, data in extracted.items():
        invocation.check_cancelled()
        member = SourcePayload(data, request.get("media_type", "application/octet-stream"), payload.source_id)
        receipt = UsedInputReceipt.for_payload(member, "archive_member", container=payload.identity, member=name)
        invocation.use(receipt)
        result.append(MaterialMember(name, member, (receipt,)))
    return tuple(result)


def archive_pack(request, invocation):
    from stratbox.core.formats.archives.members import ArchiveLimits, zip_bytes
    members = request["members"]
    if (not isinstance(members, tuple) or not members or any(not isinstance(item, MaterialMember) for item in members)
            or len({item.name for item in members}) != len(members)):
        raise OperationFailure("archive.members_invalid")
    limits = ArchiveLimits(request.get("max_members", 250), _limit(request, "max_unpacked_bytes"),
        _limit(request, "max_member_bytes"), _limit(request))
    data = zip_bytes({item.name: item.material.data for item in members}, limits=limits, budget=invocation.budget)
    for item in members:
        invocation.check_cancelled()
        invocation.use(UsedInputReceipt.for_payload(item.material, "archive_member"))
    return SourcePayload(data, "application/zip")


def collection_encode(request, invocation):
    from stratbox.shared.material_collections import encode_collection
    return _representation(encode_collection(request["collection"]), invocation, "material.collection.json",
        max_bytes=_limit(request))


def collection_decode(request, invocation):
    from stratbox.shared.material_collections import decode_collection
    value = request["material"]
    if len(value.data) > _limit(request):
        raise OperationFailure("stage.input_size_limit")
    return decode_collection(value.data)


def workbook_extract(request, invocation):
    from stratbox.core.formats.spreadsheets.extracts import extract_workbook
    payload = request["material"]
    invocation.budget.charge("input_bytes", len(payload.data))
    invocation.use(UsedInputReceipt.for_payload(payload, "source"))
    return extract_workbook(payload, series_id=request["series_id"], issue_id=request["issue_id"],
        asset_id=request.get("asset_id", "main"), budget=invocation.budget, checkpoint=invocation.check_cancelled)


def document_decode(request, invocation):
    from stratbox.core.formats.documents import extract_document
    payload = request["material"]
    invocation.budget.charge("input_bytes", len(payload.data))
    invocation.use(UsedInputReceipt.for_payload(payload, "source"))
    return extract_document(payload, series_id=request["series_id"], issue_id=request["issue_id"],
        asset_id=request.get("asset_id", "main"), budget=invocation.budget,
        checkpoint=invocation.check_cancelled, max_pages=request.get("max_pages", 10_000))


def readable(request, invocation):
    value = request["value"]
    renderer = documents.readable_document if isinstance(value, documents.DocumentExtract) else workbooks.readable_workbook
    result = renderer(value, max_bytes=_limit(request), checkpoint=invocation.check_cancelled)
    if len(result.data) > _limit(request):
        raise OperationFailure("stage.output_size_limit")
    invocation.account_output(result.identity)
    return result


_INTEGRATION_SCHEMA = TableSchema(DataContract("observations.integration.metadata", 1), (
    ColumnSchema("mapping_sha256", ScalarType.TEXT), ColumnSchema("mapping_size", ScalarType.INTEGER),
    ColumnSchema("references", ScalarType.TEXT), ColumnSchema("dataset", ScalarType.TEXT),
    ColumnSchema("release", ScalarType.TEXT)))


def _snapshot(value):
    if isinstance(value, IntegratedBatch):
        source = observation_snapshots.observation_snapshot(value.batch)
        meta = TypedTable(_INTEGRATION_SCHEMA, ((value.mapping_identity.sha256, value.mapping_identity.size,
            canonical_manifest_bytes([(key, {"sha256": identity.sha256, "size": identity.size})
                for key, identity in value.reference_editions]).decode(),
            value.batch.dataset_id, value.batch.release_id),))
        return DatasetSnapshot.build(value.batch.dataset_id, value.batch.release_id, value.contract,
            (("integration", meta), *source.tables), coverage=source.manifest.coverage,
            inputs=value.batch.lineage, parents=(source.identity,))
    for kind, convert in ((ObservationBatch, observation_snapshots.observation_snapshot),
            (views.ObservationView, views.view_snapshot), (documents.DocumentExtract, documents.document_snapshot),
            (workbooks.WorkbookExtract, workbooks.workbook_snapshot)):
        if isinstance(value, kind):
            return convert(value)
    if isinstance(value, DatasetSnapshot):
        return value
    raise OperationFailure("snapshot.value_unsupported")


def snapshot(request, invocation):
    value = request["value"]
    invocation.check_cancelled()
    from stratbox.core.operations.processing.handlers import _preflight_input
    _preflight_input(value.batch if isinstance(value, IntegratedBatch) else value, invocation)
    result = _snapshot(value)
    if result.identity.size + sum(table.identity.size for _, table in result.tables) > _limit(request):
        raise OperationFailure("snapshot.size_limit")
    for name, table in result.tables:
        invocation.check_cancelled()
        invocation.budget.charge("cells", len(table.rows) * max(1, len(table.schema.columns)))
        invocation.account_output(table.identity, key="snapshot:" + name)
    return result


def replay(request, invocation):
    value = request["snapshot"]
    kind = request["value_kind"]
    converters = {"observations": observation_snapshots.observations_from_snapshot,
        "view": views.view_from_snapshot, "document": documents.document_from_snapshot,
        "workbook": workbooks.workbook_from_snapshot}
    if kind == "integrated":
        if value.manifest.contract.role != DataRole.INTEGRATED or value.table("integration").schema != _INTEGRATION_SCHEMA:
            raise OperationFailure("integration.snapshot_invalid")
        sha, size, refs, dataset, release = value.table("integration").rows[0]
        original = DatasetSnapshot.build(dataset, release, observation_snapshots.OBSERVATION_SNAPSHOT,
            value.tables[1:], coverage=observation_snapshots._COVERAGE, inputs=value.manifest.inputs)
        result = IntegratedBatch(observation_snapshots.observations_from_snapshot(original), ByteIdentity(sha, size),
            tuple((key, ByteIdentity(**identity)) for key, identity in codec.loads(refs.encode())), value.manifest.contract)
        if _snapshot(result).identity != value.identity:
            raise OperationFailure("integration.snapshot_identity_mismatch")
        return result
    return converters[kind](value)


def snapshot_encode(request, invocation):
    value = request["snapshot"]
    if not value.complete:
        raise OperationFailure("snapshot.complete_required")
    limit = _limit(request)
    if value.identity.size + sum(table.identity.size for _, table in value.tables) > limit:
        raise OperationFailure("snapshot.size_limit")
    entries, size = [], 0
    for name, table in value.tables:
        invocation.check_cancelled()
        encoded = codec.encode_table(table)
        size += len(encoded)
        if size > limit:
            raise OperationFailure("stage.output_size_limit")
        entries.append((name, base64.b64encode(encoded).decode("ascii")))
    return _representation(canonical_manifest_bytes({"encoding": "stratbox.portable-snapshot.v1",
        "manifest": manifest_value(value.manifest), "tables": entries}), invocation, "dataset.snapshot.portable",
        max_bytes=limit)


def snapshot_decode(request, invocation):
    value = request["material"]
    limit, cells = _limit(request), request.get("max_cells", 5_000_000)
    if type(cells) is not int or cells < 0:
        raise OperationFailure("stage.cell_limit_invalid")
    decoded = codec.loads(value.data, max_bytes=limit)
    if (not isinstance(decoded, dict) or set(decoded) != {"encoding", "manifest", "tables"}
            or decoded["encoding"] != "stratbox.portable-snapshot.v1" or not isinstance(decoded["tables"], list)):
        raise OperationFailure("snapshot.encoding_invalid")
    manifest = codec.manifest_from(decoded["manifest"])
    tables = []
    for item in decoded["tables"]:
        invocation.check_cancelled()
        if not isinstance(item, list) or len(item) != 2 or not isinstance(item[0], str):
            raise OperationFailure("snapshot.encoding_invalid")
        table = codec.decode_table(base64.b64decode(item[1], validate=True), max_bytes=limit, max_cells=cells)
        count = len(table.rows) * max(1, len(table.schema.columns))
        cells -= count
        invocation.budget.charge("cells", count)
        tables.append((item[0], table))
    result = DatasetSnapshot(manifest, tuple(tables))
    if not result.complete:
        raise OperationFailure("snapshot.complete_required")
    return result


def compare(request, invocation):
    before, after = request["before"], request["after"]
    if isinstance(before, workbooks.WorkbookExtract):
        return workbooks.compare_workbooks(before, after)
    if isinstance(before, (SourcePayload, Representation)):
        return {"kind": "source_revision", "before": before.identity, "after": after.identity,
            "same_bytes": before.identity == after.identity}
    if not isinstance(before, ObservationBatch) or not isinstance(after, ObservationBatch):
        raise OperationFailure("comparison.batch_required")
    kind = request.get("kind", "revision")
    if kind not in {"revision", "period"}:
        raise OperationFailure("comparison.kind_invalid")
    def keyed(batch):
        result = {}
        for row in batch.observations:
            invocation.check_cancelled()
            key = observation_coordinate(row)
            if kind == "period":
                key = (row.subject, row.metric.id, row.dimensions, row.perimeter)
            if key in result:
                raise OperationFailure("comparison.duplicate_grain")
            result[key] = row
        return result
    old, new = keyed(before), keyed(after)
    differences = tuple(ObservationDifference(str(key), old.get(key), new.get(key))
        for key in dict.fromkeys((*old, *new)) if old.get(key) != new.get(key))
    return ObservationComparison(observation_snapshots.observation_snapshot(before).identity,
        observation_snapshots.observation_snapshot(after).identity, kind, differences,
        ("Period comparison requires one observation per subject, metric, dimensions and perimeter.",)
            if kind == "period" else ())


def plan_update(request, invocation):
    from stratbox.shared.data.updates import plan_updates
    return plan_updates(tuple(request["targets"]), tuple(request.get("retained", ())), coverage=request.get("coverage"))


def align(request, invocation):
    batch = request["observations"]
    mappings = request.get("mappings", {})
    references = tuple(request.get("references", ()))
    if not isinstance(mappings, Mapping) or set(mappings) - {"subjects", "metrics"}:
        raise OperationFailure("integration.mapping_invalid")
    subject_map, metric_map = mappings.get("subjects", {}), mappings.get("metrics", {})
    if (not isinstance(subject_map, Mapping) or not isinstance(metric_map, Mapping)
            or any(not isinstance(value, (tuple, list)) or len(value) != 2
                or any(not isinstance(part, str) or not part for part in value) for value in subject_map.values())):
        raise OperationFailure("integration.mapping_invalid")
    rows, seen = [], set()
    for row in batch.observations:
        invocation.check_cancelled()
        subject_key = row.subject.namespace + ":" + row.subject.id
        subject = subject_map.get(subject_key)
        metric = metric_map.get(row.metric.id)
        if request.get("require_mapped", False) and subject is None:
            raise OperationFailure("integration.subject_unmapped")
        target_metric, factor = row.metric, None
        if metric is not None:
            if not isinstance(metric, Mapping) or set(metric) - {*MetricRef.__dataclass_fields__, "multiplier"}:
                raise OperationFailure("integration.metric_mapping_invalid")
            target_metric = replace(row.metric, **{key: value for key, value in metric.items() if key != "multiplier"})
            factor = metric.get("multiplier")
            if target_metric.quantity_kind != row.metric.quantity_kind:
                raise OperationFailure("integration.quantity_kind_changed")
            if (target_metric.unit, target_metric.scale) != (row.metric.unit, row.metric.scale) and factor is None:
                raise OperationFailure("integration.explicit_conversion_required")
            if factor is not None:
                from decimal import Decimal
                if type(factor) not in {int, Decimal} or not Decimal(factor).is_finite() or factor == 0:
                    raise OperationFailure("integration.conversion_factor_invalid")
        value, status = row.value, row.value_status
        if factor is not None and value is not None:
            from decimal import Decimal
            if type(value) not in {int, Decimal}:
                raise OperationFailure("integration.numeric_conversion_required")
            value = value * factor
            status = "derived" if status == "reported" else status
        target = replace(row, subject=SubjectRef(*subject) if subject is not None else row.subject,
            metric=target_metric, value=value, value_status=status)
        # Alignment must never silently add or combine source aggregates.
        coordinate = observation_coordinate(target)
        if coordinate in seen:
            raise OperationFailure("integration.grain_collision")
        seen.add(coordinate)
        rows.append(target)
    if (any(not isinstance(item, tuple) or len(item) != 2 or not isinstance(item[0], str)
            or not item[0] or not isinstance(item[1], ByteIdentity) for item in references)
            or len({item[0] for item in references}) != len(references)):
        raise OperationFailure("integration.reference_editions_invalid")
    editions = tuple(sorted(references, key=lambda item: item[0]))
    evidence = value_evidence(batch)
    coverage = evidence.coverage
    if coverage is not None:
        members, observed = observation_scope(tuple(rows))
        def coordinate(value):
            subject = subject_map.get(value.subject_namespace + ":" + value.subject_id,
                (value.subject_namespace, value.subject_id))
            metric = metric_map.get(value.metric_id, {}).get("id", value.metric_id)
            return replace(value, subject_namespace=subject[0], subject_id=subject[1], metric_id=metric)
        def axis(value):
            if value.startswith("subject:"):
                key = value.removeprefix("subject:")
                return "subject:" + ":".join(subject_map[key]) if key in subject_map else value
            if value.startswith("metric:"):
                key = value.removeprefix("metric:")
                return "metric:" + metric_map.get(key, {}).get("id", key)
            return value
        coverage = replace(coverage, members=members, observed=observed,
            expected=tuple(dict.fromkeys(axis(value) for value in coverage.expected)) if coverage.expected is not None else None,
            expected_coordinates=tuple(coordinate(value) for value in coverage.expected_coordinates)
                if coverage.expected_coordinates is not None else None)
    evidence = replace(evidence, qualifications=evidence.qualifications | {"integration.aligned"},
        coverage=coverage,
        reference_fingerprints=tuple(sorted({*evidence.reference_fingerprints, *(identity.sha256 for _, identity in editions)})))
    aligned = replace(batch, observations=tuple(rows), evidence=evidence)
    return IntegratedBatch(aligned, ByteIdentity.of(canonical_manifest_bytes(mappings)), editions)


def query_observations(request, invocation):
    value = request["observations"]
    batch = value.batch if isinstance(value, IntegratedBatch) else value
    selected = tuple(row for row in batch.observations
        if (not request.get("metric_ids") or row.metric.id in request["metric_ids"])
        and (not request.get("subject_ids") or row.subject.id in request["subject_ids"])
        and (not request.get("period_kinds") or row.period.kind in request["period_kinds"]))
    result = replace(batch, observations=selected, evidence=selected_evidence(value_evidence(batch), selected))
    return replace(value, batch=result) if isinstance(value, IntegratedBatch) else result


def qualify_csv(request, invocation):
    payload = request["material"]
    if len(payload.data) > _limit(request):
        raise OperationFailure("stage.input_size_limit")
    contract = request["contract"]
    if isinstance(contract, Mapping):
        contract = DataContract(contract["schema_id"], contract.get("version", 1), DataRole(contract["role"]))
    if not isinstance(contract, DataContract) or contract.role is None:
        raise OperationFailure("csv.contract_required")
    encoding = request.get("encoding", payload.charset or "utf-8")
    stream = StringIO(payload.data.decode(encoding), newline="")
    reader = csv.reader(stream, delimiter=request.get("delimiter", ","), strict=True)
    header = next(reader, None)
    expected = tuple(request.get("columns", ()))
    if header is None or not header or len(set(header)) != len(header) or (expected and tuple(header) != expected):
        raise OperationFailure("csv.header_mismatch")
    max_rows = _limit(request, "max_rows", 1_000_000)
    count = 0
    for row in reader:
        invocation.check_cancelled()
        count += 1
        if count > max_rows or len(row) != len(header):
            raise OperationFailure("csv.record_invalid")
        invocation.budget.charge("cells", len(row))
    # Admission records a structural qualification, not an economic parser claim.
    return QualifiedMaterial(payload, contract, ValueEvidence(frozenset({"csv.structurally_valid", "role.declared"})))


def qualified_encode(request, invocation):
    value = request["value"]
    payload, contract = value.material, value.contract
    return _representation(canonical_manifest_bytes({"encoding": "stratbox.qualified-material.v1",
        "data": base64.b64encode(payload.data).decode("ascii"), "media_type": payload.media_type,
        "source_id": payload.source_id, "charset": payload.charset,
        "sha256": payload.identity.sha256,
        "expected_sha256": payload.expected_sha256,
        "contract": {"schema_id": contract.schema_id, "version": contract.version, "role": contract.role.value},
        "evidence": assessment_value(value.evidence)}), invocation, "qualified.material.portable", max_bytes=_limit(request))


def qualified_decode(request, invocation):
    value = codec.loads(request["material"].data, max_bytes=_limit(request))
    expected = {"encoding", "data", "media_type", "source_id", "charset", "sha256", "expected_sha256", "contract", "evidence"}
    if not isinstance(value, dict) or set(value) != expected or value["encoding"] != "stratbox.qualified-material.v1":
        raise OperationFailure("qualified.encoding_invalid")
    payload = SourcePayload(base64.b64decode(value["data"], validate=True), value["media_type"], value["source_id"],
        value["expected_sha256"], charset=value["charset"])
    if payload.identity.sha256 != value["sha256"]:
        raise OperationFailure("qualified.identity_mismatch")
    return QualifiedMaterial(payload, codec.contract_from(value["contract"]), evidence_from(value["evidence"]))


REFERENCE_PACKAGES = {"reference.geography.names": "stratbox.shared.reference.geography",
    "reference.banks": "stratbox.shared.reference.banks", "reference.okved2": "stratbox.shared.reference.okved2"}


def reference_editions(request, invocation):
    from stratbox.shared.reference.assets import load_reference
    selected = request.get("references", ())
    result = []
    for reference_id, edition in selected:
        invocation.check_cancelled()
        if reference_id not in REFERENCE_PACKAGES:
            raise OperationFailure("reference.identity_unsupported")
        loaded = load_reference(REFERENCE_PACKAGES[reference_id], edition_id=edition)
        for asset in loaded.edition.assets:
            if asset.required:
                receipts = []
                data = loaded.read(asset.role, inputs=receipts)
                invocation.budget.charge("input_bytes", len(data))
                for receipt in receipts:
                    invocation.use(receipt)
        result.append((loaded.edition.reference_id, loaded.snapshot_identity))
    return tuple(result)


def release_manifest(request, invocation):
    receipts = request["receipts"]
    if (not isinstance(receipts, tuple) or not receipts or any(not isinstance(item, StoredBytesReceipt)
            or item.status not in {"stored", "already_present"} or item.observed_identity != item.identity
            or item.effect_id is None for item in receipts)):
        raise OperationFailure("release.confirmed_receipts_required")
    names = tuple(request.get("members", ())) or tuple(str(index) for index in range(len(receipts)))
    if len(names) != len(receipts) or len(set(names)) != len(names):
        raise OperationFailure("release.members_invalid")
    expected = request.get("expected_members", {})
    if expected and (set(expected) != set(names) or any(
            (expected[name] != item.identity if isinstance(expected[name], ByteIdentity)
                else expected[name] != item.identity.sha256) for name, item in zip(names, receipts))):
        raise OperationFailure("release.member_identity_mismatch")
    versions = request.get("input_versions", {})
    member_versions = request.get("member_versions", {})
    if (not isinstance(versions, Mapping) or any(not isinstance(key, str) or not key
            or not isinstance(value, str) or not value for key, value in versions.items())):
        raise OperationFailure("release.version_vector_invalid")
    if versions and (set(member_versions) != set(names) or any(member_versions[name] != versions for name in names)):
        raise OperationFailure("release.member_version_mismatch")
    return _representation(canonical_manifest_bytes({"schema": "stratbox.coherent-release.v1",
        "release_id": request["release_id"], "input_versions": versions,
        "members": [{"name": name, "sha256": item.identity.sha256, "size": item.identity.size,
            "destination": item.destination, "scope": item.store_scope, "effect_id": item.effect_id}
            for name, item in zip(names, receipts)]}), invocation, "coherent.release.manifest", max_bytes=_limit(request))


def release_basis(request, invocation):
    value = codec.loads(request["manifest"].data, max_bytes=_limit(request))
    if not isinstance(value, dict) or value.get("schema") != "stratbox.coherent-release.v1":
        raise OperationFailure("release.manifest_invalid")
    return ByteIdentity.of(canonical_manifest_bytes(value["input_versions"])).sha256


def release_verify(request, invocation):
    from stratbox.core.storage.bytes import file_identity
    from stratbox.core.storage.staging import current_revision, storage_scope, store_identity
    store = invocation.provider("output_filestore")
    receipts = request["receipts"]
    for receipt in receipts:
        invocation.check_cancelled()
        if not isinstance(receipt, StoredBytesReceipt) or receipt.status not in {"stored", "already_present"}:
            raise OperationFailure("release.confirmed_receipts_required")
        if (receipt.store_id != store_identity(store) or receipt.store_scope is not None
                and receipt.store_scope != storage_scope(store, receipt.destination)):
            raise OperationFailure("release.member_store_mismatch")
        before = current_revision(store, receipt.destination)
        if receipt.observed_revision is not None and before != receipt.observed_revision:
            raise OperationFailure("release.member_revision_changed")
        actual = file_identity(receipt.destination, store=store, limit=receipt.identity.size,
            checkpoint=invocation.check_cancelled)
        if actual != receipt.identity or before != current_revision(store, receipt.destination):
            raise OperationFailure("release.member_identity_mismatch")
    return receipts


def dataset_ingest(request, invocation):
    from stratbox.core.storage.datasets.ports import DatasetWriteControls
    value = _snapshot(request["value"])
    writer = invocation.provider("dataset_writer")
    effect_id = ByteIdentity.of(canonical_manifest_bytes({"provider": writer.provider_id, "scope": writer.scope_id,
        "dataset": value.manifest.dataset_id, "version": value.manifest.version_id, "identity": value.identity.sha256})).sha256
    results = []
    def action():
        result = writer.write_snapshot(value, controls=DatasetWriteControls(invocation.budget, invocation.check_cancelled,
            invocation.context.profile == "managed", invocation.definition.operation_id))
        results.append(result)
        return EffectReceipt("dataset.write", "confirmed" if result.status in {"stored", "already_present"} else result.status,
            reference=value.manifest.dataset_id, effect_id=effect_id, identity=value.identity,
            guarantee="immutable_version", reconciliation_owner="dataset_writer")
    invocation.commit_effect("dataset.write", effect_id, action,
        resource=f"{writer.provider_id}:{writer.scope_id}:{value.manifest.dataset_id}:{value.manifest.version_id}",
        identity=value.identity)
    if results:
        if results[0].reference is None:
            raise OperationFailure(results[0].diagnostic_code or "dataset.write_unconfirmed")
        return results[0].reference
    from stratbox.shared.data.snapshots import SnapshotReference
    return SnapshotReference(writer.provider_id, writer.scope_id, value.manifest.dataset_id, value.manifest.version_id, value.identity)


def dataset_query(request, invocation):
    from stratbox.core.storage.datasets.ports import DatasetReadControls
    reader = invocation.provider("dataset_reader")
    return reader.read_snapshot(request["reference"], request.get("components"), controls=DatasetReadControls(
        budget=invocation.budget, checkpoint=invocation.check_cancelled, max_cells=request.get("max_cells", 5_000_000)))


def dataset_versions(request, invocation):
    from stratbox.core.storage.datasets.ports import DatasetReadControls
    reader = invocation.provider("dataset_catalog")
    return reader.versions(request["dataset_id"], controls=DatasetReadControls(
        budget=invocation.budget, checkpoint=invocation.check_cancelled))


def query_snapshot(request, invocation):
    from stratbox.shared.data.query import query_snapshot as query
    from stratbox.core.storage.datasets.operations import _preview_context
    value = query(request["snapshot"], request["query"], expected_identity=request.get("expected_identity"),
        checkpoint=invocation.check_cancelled)
    value = _preview_context(request["snapshot"], value)
    invocation.account_output(value.table.identity)
    return value


def material_resolve(request, invocation):
    from stratbox.core.operations.source.originals import read_material
    return read_material(request["reference"], invocation.provider("filestore"), invocation, limit=_limit(request))


def material_locate(request, invocation):
    from stratbox.core.storage.bytes import read_bounded_bytes
    from stratbox.core.storage.staging import current_revision, storage_scope, store_identity
    from stratbox.shared.evidence import MaterialReference
    store = invocation.provider("filestore")
    path = request["path"]
    before = current_revision(store, path)
    if request.get("expected_revision") is not None and request["expected_revision"] != before:
        raise OperationFailure("input.material_version_changed")
    data = read_bounded_bytes(path, store=store, limit=_limit(request), budget=invocation.budget,
        checkpoint=invocation.check_cancelled)
    if before != current_revision(store, path):
        raise OperationFailure("input.material_version_changed")
    payload = SourcePayload(data, request.get("media_type", "application/octet-stream"), request.get("source_id"),
        charset=request.get("charset"))
    if request.get("expected_identity") is not None and payload.identity != request["expected_identity"]:
        raise OperationFailure("input.identity_mismatch")
    reference = MaterialReference(path, store_identity(store), payload.identity, payload.media_type,
        payload.source_id, before, payload.charset, storage_scope(store, path))
    invocation.use(UsedInputReceipt.for_payload(payload, "material"))
    return {"material": payload, "reference": reference}


def artifact_resolve(request, invocation):
    from stratbox.core.operations.materials.operations import _read
    store = invocation.provider("filestore")
    return _read(request["reference"], _limit(request), store, store, invocation)


def artifact_parts(request, invocation):
    value = request["artifact"]
    metadata = _representation(value.descriptor, invocation, "material.descriptor", max_bytes=_limit(request))
    return {"data": value.representation, "descriptor": metadata}


def artifact_destinations(request, invocation):
    destination = request["destination"]
    descriptor = request.get("descriptor_destination") or destination + ".stratbox.json"
    if destination == descriptor:
        raise OperationFailure("material.descriptor_destination_conflict")
    return {"data": destination, "descriptor": descriptor}


def artifact_reference(request, invocation):
    from stratbox.shared.evidence import MaterialReference
    from stratbox.shared.materials import ArtifactReference
    artifact, data, descriptor = request["artifact"], request["data"], request["descriptor"]
    if (any(item.status not in {"stored", "already_present"} or item.observed_identity != item.identity
                for item in (data, descriptor)) or data.identity != artifact.representation.identity
            or descriptor.identity != artifact.identity):
        raise OperationFailure("material.confirmation_required")
    rep = artifact.representation
    return ArtifactReference(MaterialReference(data.destination, data.store_id, data.identity, rep.media_type,
        artifact.series_id, data.observed_revision, rep.encoding, data.store_scope),
        MaterialReference(descriptor.destination, descriptor.store_id, descriptor.identity, "application/json",
            artifact.series_id, descriptor.observed_revision, "utf-8", descriptor.store_scope), artifact.contract, artifact.identity)


def source_compare_versions(request, invocation):
    from stratbox.core.operations.source.version_comparison import _compare
    from stratbox.core.operations.source.version_definitions import CompareOriginalVersionsRequest
    return _compare(CompareOriginalVersionsRequest(request["candidate"], request["baseline_state"], request.get("baseline"),
        request.get("absence"), request.get("presence")))


def reconcile_material(request, invocation):
    from stratbox.core.execution.runner import Completion
    from stratbox.core.storage.bytes import file_identity
    from stratbox.core.storage.staging import current_revision, storage_scope, store_identity
    prior = request["receipt"]
    store = invocation.provider("filestore")
    if store_identity(store) != prior.store_id or prior.effect_id is None:
        raise OperationFailure("input.material_store_mismatch")
    if prior.store_scope is not None and storage_scope(store, prior.destination) != prior.store_scope:
        raise OperationFailure("input.material_store_mismatch")
    try:
        revision = current_revision(store, prior.destination)
        actual = file_identity(prior.destination, store=store, limit=prior.identity.size,
            checkpoint=invocation.check_cancelled)
        if revision != current_revision(store, prior.destination):
            actual = None
    except (OSError, ValueError):
        revision, actual = None, None
    if actual == prior.identity:
        return replace(prior, status="already_present", stage="verify", diagnostic_code=None,
            observed_identity=actual, observed_revision=revision)
    code = "effect.read_back_mismatch" if actual is not None else "effect.read_back_unavailable"
    return Completion(replace(prior, status="unknown", stage="verify", diagnostic_code=code, observed_identity=actual),
        "unknown", code)


def notification_qualify(request, invocation):
    from stratbox.core.execution.runner import Completion
    from stratbox.core.notifications.dispatch.qualification import qualify_receipt
    result = qualify_receipt(request["lookup"], request.get("receipt"))
    return Completion(result, "unknown", result.reason_code) if result.state == "unknown" else result
