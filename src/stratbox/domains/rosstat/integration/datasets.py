"""Explicit observation integration; reported indices retain their source basis."""
from __future__ import annotations

from dataclasses import dataclass
import json
from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
from stratbox.shared.data.observations import Observation, ObservationBatch, MetricRef, PeriodRef, SubjectRef
from stratbox.shared.data.observation_snapshots import observation_snapshot, observations_from_snapshot, OBSERVATION_SNAPSHOT
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import ColumnSchema, DatasetSnapshot, ScalarType as S, SnapshotCoverage, TableSchema, TypedTable
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from ..tables.contracts import RosstatSourceFlake

DATASET_CONTRACT=DataContract("rosstat.integrated_dataset",1,DataRole.INTEGRATED)
# Snapshot wrapper metadata is distinct from the integrated value contract.
DATASET_SNAPSHOT_CONTRACT=DataContract("rosstat.integrated_dataset.snapshot",1,DataRole.INTEGRATED)
_CONTEXT=TableSchema(DataContract("rosstat.integrated_dataset.context",1,DataRole.INTEGRATED),(
    ColumnSchema("ordinal",S.INTEGER),ColumnSchema("series_id",S.TEXT),ColumnSchema("issue_id",S.TEXT),
    ColumnSchema("asset_id",S.TEXT),ColumnSchema("flake_sha256",S.TEXT),ColumnSchema("flake_size",S.INTEGER),
    ColumnSchema("source_sha256",S.TEXT),ColumnSchema("source_size",S.INTEGER),ColumnSchema("profile_id",S.TEXT),
    ColumnSchema("profile_version",S.INTEGER),ColumnSchema("source_sections",S.TEXT),
), ("ordinal",))

@dataclass(frozen=True,slots=True)
class DatasetSource:
    series_id: str
    issue_id: str
    asset_id: str
    flake_identity: ByteIdentity
    source_identity: ByteIdentity
    profile_id: str
    profile_version: int
    source_sections: str

@dataclass(frozen=True,slots=True)
class RosstatDataset:
    batch: ObservationBatch
    sources: tuple[DatasetSource,...]
    coverage: SnapshotCoverage

    @property
    def identity(self):
        return dataset_snapshot(self).identity


def observation_key(item: Observation) -> tuple:
    dimensions=tuple((key,value) for key,value in item.dimensions if key not in {
        "source_label","unit_literal","display_date","source_footnotes","source_number_format","source_year_literal",
    })
    return (item.subject.namespace,item.subject.id,item.metric.id,item.period.kind,item.period.as_of,
        item.period.start,item.period.end,item.perimeter,dimensions)


def integrate_flakes(flakes: tuple[RosstatSourceFlake,...], *, dataset_id: str, release_id: str) -> RosstatDataset:
    if not flakes or not dataset_id or not release_id:
        raise ValueError("rosstat.integration_input_required")
    observations,sources,lineage,seen=[],[],[],set()
    for flake in flakes:
        if flake.diagnostics:
            raise ValueError("rosstat.integration_unresolved_source")
        flake_id=flake.identity
        sections=canonical_manifest_bytes({"sections":[{
            "indicator_id":s.indicator_id,"measure":s.measure,"sheet":s.sheet,"source_title":s.source_title,
            "headers":s.headers,"unit_literal":s.unit_literal,"notes":s.notes,
        } for s in flake.sections]}).decode("utf-8")
        sources.append(DatasetSource(flake.series_id,flake.issue_id,flake.asset_id,flake_id,flake.source_identity,
            flake.profile_id,flake.profile_version,sections))
        for receipt in (*flake.lineage,UsedInputReceipt("source_flake",flake_id,"application/vnd.stratbox.dataset", "inline")):
            if receipt not in lineage:
                lineage.append(receipt)
        for row in flake.values:
            if row.unit is None or row.quantity_kind is None or row.value_status == "unparsed":
                raise ValueError("rosstat.integration_semantics_unresolved")
            if row.measure.endswith("_index") and (row.quantity_kind != "index" or row.unit != "percent"):
                raise ValueError("rosstat.integration_index_semantics_invalid")
            metric=MetricRef(flake.series_id + "." + row.indicator_id + "." + row.measure,
                row.unit,row.quantity_kind,flake.profile_id + ":" + str(flake.profile_version),row.scale)
            period=PeriodRef("as_of",as_of=row.period_start) if row.period_kind == "as_of" else PeriodRef("interval",start=row.period_start,end=row.period_end)
            dimensions=tuple(sorted((*row.dimensions,("indicator_id",row.indicator_id),("measure",row.measure),
                ("frequency",row.frequency),("source_label",row.label),("unit_literal",row.unit_literal),
                ("display_date",row.display_date.isoformat()),("source_footnotes"," | ".join(row.footnotes)),
                ("source_number_format",row.number_format),("source_year_literal",row.source_year_literal))))
            value=Observation(SubjectRef(row.geography_namespace,row.geography_id),metric,period,dimensions,row.perimeter,
                row.value,row.value_status,flake.source_identity.sha256 + "#" + row.source_locator,row.raw_token)
            key=observation_key(value)
            if key in seen:
                # Source revisions need an explicit release choice. Even equal
                # duplicates cannot be averaged or silently preferred.
                raise ValueError("rosstat.integration_duplicate_observation")
            seen.add(key)
            observations.append(value)
    complete=all(flake.coverage.status == "complete" for flake in flakes)
    return RosstatDataset(ObservationBatch(dataset_id,1,release_id,tuple(observations),tuple(lineage),
        tuple(SourceUse(SourceCoordinate(flake.series_id, source_group_id="kep2_indicators" if flake.series_id == "rosstat.short_term_indicators" else None,
            issue_id=flake.issue_id, asset_id=flake.asset_id, material_identity=flake.source_identity,
            semantic_profile_edition=flake.profile_id + ":" + str(flake.profile_version)), "flakes", "domain_validated") for flake in flakes)),tuple(sources),
        SnapshotCoverage("complete" if complete else "partial","Union of explicitly supplied Rosstat source-flake scopes; no source-wide completeness inferred."))


def dataset_snapshot(value: RosstatDataset, *, dataset_id=None, version_id=None) -> DatasetSnapshot:
    original=observation_snapshot(value.batch)
    context=TypedTable(_CONTEXT,tuple((i,s.series_id,s.issue_id,s.asset_id,s.flake_identity.sha256,s.flake_identity.size,
        s.source_identity.sha256,s.source_identity.size,s.profile_id,s.profile_version,s.source_sections) for i,s in enumerate(value.sources)))
    return DatasetSnapshot.build(dataset_id or value.batch.dataset_id,version_id or value.batch.release_id,DATASET_CONTRACT,
        (*original.tables,("source_context",context)),coverage=value.coverage,inputs=value.batch.lineage,
        parents=tuple(s.flake_identity for s in value.sources))


def dataset_from_snapshot(snapshot: DatasetSnapshot) -> RosstatDataset:
    if not snapshot.complete or snapshot.manifest.contract != DATASET_CONTRACT or tuple(n for n,_ in snapshot.tables) != ("metadata","observations","source_context"):
        raise ValueError("rosstat.dataset_snapshot_invalid")
    if snapshot.table("source_context").schema != _CONTEXT:
        raise ValueError("rosstat.dataset_context_invalid")
    batch_snapshot=DatasetSnapshot.build(snapshot.manifest.dataset_id,snapshot.manifest.version_id,OBSERVATION_SNAPSHOT,
        snapshot.tables[:2],coverage=SnapshotCoverage("unknown","Exactly the supplied observation batch; source-wide coverage is not inferred."),
        inputs=snapshot.manifest.inputs)
    batch=observations_from_snapshot(batch_snapshot)
    sources=[]
    for i,row in enumerate(snapshot.table("source_context").rows):
        position,series,issue,asset,flake_hash,flake_size,source_hash,source_size,profile,version,sections=row
        if position != i:
            raise ValueError("rosstat.dataset_context_invalid")
        decoded=json.loads(sections)
        if canonical_manifest_bytes(decoded).decode("utf-8") != sections:
            raise ValueError("rosstat.dataset_context_invalid")
        sources.append(DatasetSource(series,issue,asset,ByteIdentity(flake_hash,flake_size),ByteIdentity(source_hash,source_size),profile,version,sections))
    result=RosstatDataset(batch,tuple(sources),snapshot.manifest.coverage)
    rebuilt=dataset_snapshot(result,dataset_id=snapshot.manifest.dataset_id,version_id=snapshot.manifest.version_id)
    if rebuilt.identity != snapshot.identity:
        raise ValueError("rosstat.dataset_snapshot_identity_mismatch")
    return result
