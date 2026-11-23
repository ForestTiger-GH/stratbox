"""Dated identity-only mapping follows the retained reported-fields projection."""
from dataclasses import replace
from decimal import Decimal
import json

from stratbox.shared.data.observations import MetricRef, ObservationBatch
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes

from ...tables.contracts import FieldDisposition
from ...tables.legal_entities.projection import PROFILE as SOURCE_PROFILE
from ..contracts import FnsDataset
from ..coverage import observation_coverage
from .mapping import CATEGORY, KINDS, MAP_VERSION, PREFIXES, epoch, mapping

PROFILE = "fns.1yur.identity-field-alignment"
MAP_IDENTITY = ByteIdentity.of(canonical_manifest_bytes({"version": MAP_VERSION,
    "categories": CATEGORY, "kinds": KINDS, "prefixes": PREFIXES}))


def align(projection):
    if projection.context.series_id != "fns.1yur" or projection.profile_id != SOURCE_PROFILE:
        raise ValueError("fns.1yur.projection_profile_mismatch")
    observations, dispositions = [], list(projection.dispositions)
    reviewed = {}
    qualifications = list(projection.qualifications)
    for item in projection.batch.observations:
        if item.metric.unit != "count" or item.period.kind != "as_of":
            raise ValueError("fns.1yur.reported_metric_unreviewed")
        if item.metric.id not in reviewed:
            reviewed[item.metric.id] = mapping(projection.context.observation_date, item.metric.id)
            target, reason = reviewed[item.metric.id]
            dispositions.append(FieldDisposition(item.metric.id, target, reason))
        target, _ = reviewed[item.metric.id]
        if target is None:
            qualifications.append("source.unmapped_historical_fields")
            continue
        measure, kind = target[3:].split("__", 1)
        quantity = "stock" if measure in {"not_ceased", "bankruptcy_proceedings"} else "count"
        dimensions = (*item.dimensions, ("legal_kind", kind))
        if quantity == "count":
            qualifications.append("source.ceased_bankruptcy_period_basis_unresolved")
            dimensions += (("time_basis", "published_reporting_date_unspecified_accumulation"),)
        observations.append(replace(item, metric=MetricRef(measure, "count", quantity, MAP_VERSION, Decimal(1)), dimensions=dimensions))
    lineage = (*projection.batch.lineage, UsedInputReceipt("field_map", MAP_IDENTITY, "application/json", "reference_only", MAP_VERSION))
    batch = ObservationBatch("fns.1yur.integrated", 1, projection.batch.release_id, tuple(observations), lineage)
    details = json.loads(projection.details_json)
    details.update({"mapping_profile": PROFILE, "mapping_version": MAP_VERSION,
        "mapping_sha256": MAP_IDENTITY.sha256, "epoch": epoch(projection.context.observation_date),
        "mapping": [{"source_field": key, "target_field": target, "disposition": reason}
                    for key, (target, reason) in reviewed.items()]})
    parent = projection.identity
    return FnsDataset(projection.context, parent, batch, PROFILE, observation_coverage(projection.coverage, observations),
        tuple(dict.fromkeys(qualifications)), tuple(dispositions), canonical_manifest_bytes(details).decode("utf-8"),
        (parent, MAP_IDENTITY))
