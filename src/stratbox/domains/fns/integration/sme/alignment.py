"""Identity aliases for all nine published SME counters; source geography is retained."""
from dataclasses import replace
from decimal import Decimal

from stratbox.shared.data.observations import MetricRef, ObservationBatch
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes

from ...tables.contracts import FieldDisposition
from ...tables.sme.projection import PROFILE as SOURCE_PROFILE
from ..contracts import FnsDataset
from ..coverage import observation_coverage

PROFILE = "fns.sme.published-counts-alignment.v1"
METRICS = {"cnt_total": "total", "cnt_ul_total": "ul_total", "cnt_ip_total": "ip_total",
    "cnt_ul_micro": "ul_micro", "cnt_ul_mini": "ul_small", "cnt_ul_normal": "ul_medium",
    "cnt_ip_micro": "ip_micro", "cnt_ip_mini": "ip_small", "cnt_ip_normal": "ip_medium"}
MAP_IDENTITY = ByteIdentity.of(canonical_manifest_bytes({"profile": PROFILE, "metrics": METRICS}))


def align(projection):
    if projection.context.series_id != "fns.sme" or projection.profile_id != SOURCE_PROFILE:
        raise ValueError("fns.sme.projection_profile_mismatch")
    observations = []
    for item in projection.batch.observations:
        if item.metric.id not in METRICS or item.metric.unit != "count" or item.period.kind != "as_of":
            raise ValueError("fns.sme.reported_metric_unreviewed")
        observations.append(replace(item, metric=MetricRef(METRICS[item.metric.id], "count", "stock", PROFILE, Decimal(1)),
            dimensions=(*item.dimensions, ("source_field", item.metric.id))))
    lineage = (*projection.batch.lineage, UsedInputReceipt("field_map", MAP_IDENTITY, "application/json",
        "reference_only", PROFILE))
    batch = ObservationBatch("fns.sme.integrated", 1, projection.batch.release_id, tuple(observations), lineage)
    dispositions = (*projection.dispositions, *(FieldDisposition(key, value, "reported_value_alias")
        for key, value in METRICS.items()))
    parent = projection.identity
    return FnsDataset(projection.context, parent, batch, PROFILE, observation_coverage(projection.coverage, observations),
        projection.qualifications, dispositions,
        canonical_manifest_bytes({"mapping_profile": PROFILE, "mapping_sha256": MAP_IDENTITY.sha256,
            "geography": "published_fns_namespaces", "time_basis": "stock_at_published_stat_date"}).decode("utf-8"),
        (parent, MAP_IDENTITY))
