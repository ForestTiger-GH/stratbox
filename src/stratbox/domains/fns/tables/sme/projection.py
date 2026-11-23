"""Reviewed published counters; RF, federal districts and subjects remain separate."""
from decimal import Decimal
from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
from stratbox.shared.data.observations import MetricRef, Observation, ObservationBatch, PeriodRef, SubjectRef
from stratbox.shared.data.snapshots import CoverageDimension, SnapshotCoverage

from ..contracts import FieldDisposition, SourceProjection, ValidationFinding, ValidationReport
from .parser import FnsError, counter, published_date

COUNTERS = ("cnt_total", "cnt_ul_total", "cnt_ip_total", "cnt_ul_micro", "cnt_ul_mini", "cnt_ul_normal",
            "cnt_ip_micro", "cnt_ip_mini", "cnt_ip_normal")
IDENTIFIERS = frozenset({"stat_date", "cnt_level", "cnt_name", "ssrf", "name"})
PROFILE = "fns.sme.published-counts.v1"


def validate(flake):
    findings = []
    observed = set()
    levels = set()
    for record in flake.records:
        item = record.values()
        ref = "json:" + str(record.ordinal)
        try:
            if published_date(item.get("stat_date")) != flake.context.observation_date:
                raise FnsError("SOURCE_DATE_MISMATCH")
            level = item.get("cnt_level")
            if type(level) is not int or level not in {0, 1, 2}:
                raise FnsError("SOURCE_LEVEL_INVALID")
            levels.add(level)
            label = item.get("cnt_name")
            if type(label) is not str or not label.strip():
                raise FnsError("SOURCE_LABEL_INVALID")
            code = item.get("ssrf") if level == 0 else label
            if type(code) is not str or not code or level == 0 and (
                    not code.isascii() or not code.isdigit() or len(code) > 3):
                raise FnsError("REGION_CODE_INVALID")
            if (level, code) in observed:
                raise FnsError("SOURCE_GEOGRAPHY_DUPLICATE")
            observed.add((level, code))
            reported = {name: int(counter(item[name])) for name in COUNTERS if name in item}
            for total, parts in (("cnt_total", ("cnt_ul_total", "cnt_ip_total")),
                ("cnt_ul_total", ("cnt_ul_micro", "cnt_ul_mini", "cnt_ul_normal")),
                ("cnt_ip_total", ("cnt_ip_micro", "cnt_ip_mini", "cnt_ip_normal"))):
                if total in reported and all(part in reported for part in parts):
                    if reported[total] != sum(reported[part] for part in parts):
                        raise FnsError("SOURCE_COUNTER_TOTAL_INCONSISTENT")
            if not reported:
                findings.append(ValidationFinding("source.counter_fields_absent", "warning", ref))
            elif set(reported) != set(COUNTERS):
                findings.append(ValidationFinding("source.counter_coverage_partial", "warning", ref))
            for name in item.keys() - IDENTIFIERS - set(COUNTERS):
                findings.append(ValidationFinding("source.unmapped_field", "warning", ref + ":" + name))
        except FnsError as error:
            findings.append(ValidationFinding("source." + str(error).lower(), "error", ref))
    if levels != {0, 1, 2}:
        findings.append(ValidationFinding("source.geographic_levels_partial", "warning", "json"))
    return ValidationReport(PROFILE, flake.identity, tuple(findings))


def project_counts(flake):
    report = validate(flake)
    if not report.valid:
        raise FnsError(next(item.code for item in report.findings if item.severity == "error"))
    observations, dispositions = [], []
    labels = {0: ("fns.ssrf", "published_subject"),
              1: ("fns.sme.federal_district", "published_federal_district"),
              2: ("fns.sme.country", "published_national")}
    for record in flake.records:
        values = record.values()
        level = values["cnt_level"]
        namespace, perimeter = labels[level]
        subject = values["ssrf"] if level == 0 else values["cnt_name"]
        for field in record.fields:
            reference = f"json:{record.ordinal}:{field.name}"
            if field.name in COUNTERS:
                observations.append(Observation(SubjectRef(namespace, subject),
                    MetricRef(field.name, "count", "stock", PROFILE, Decimal(1)),
                    PeriodRef("as_of", flake.context.observation_date),
                    (("published_label", values["cnt_name"]), ("geographic_level", str(level))),
                    perimeter, int(counter(field.value)), "reported", reference, field.raw_token))
                dispositions.append(FieldDisposition(reference, field.name, "reported_counter"))
            else:
                dispositions.append(FieldDisposition(reference, None,
                    "identity_metadata" if field.name in IDENTIFIERS else "retained_unmapped_source_field"))
    qualifications = tuple(sorted({item.code for item in report.findings}))
    fields = tuple(dict.fromkeys(item.metric.id for item in observations))
    levels = tuple(dict.fromkeys(dict(item.dimensions)["geographic_level"] for item in observations))
    coverage = SnapshotCoverage("partial" if qualifications else "complete",
        "Every present reviewed counter at every supplied geographic level. Other fields remain in the full JSON flake; absent counters are not zero.", (
            CoverageDimension("counter_fields", requested=COUNTERS, materialized=fields, validated=fields,
                output=fields, missing=tuple(field for field in COUNTERS if field not in fields)),
            CoverageDimension("geographic_levels", requested=("0", "1", "2"), materialized=levels, validated=levels,
                output=levels, missing=tuple(level for level in ("0", "1", "2") if level not in levels)),
        ))
    batch = ObservationBatch("fns.sme.reported", 1, "source-" + flake.source_identity.sha256,
                             tuple(observations), flake.lineage, (SourceUse(SourceCoordinate(flake.context.series_id,
            source_group_id="population_records", issue_id=flake.context.issue_id, asset_id=flake.context.asset_id,
            material_identity=flake.source_identity, semantic_profile_edition=PROFILE), "flake", "domain_validated"),))
    return SourceProjection(flake.context, flake.identity, batch, PROFILE, coverage,
                            qualifications, tuple(dispositions))
