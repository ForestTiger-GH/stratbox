"""Reviewed SME table semantics over already decoded JSON evidence."""
from collections.abc import Mapping
from dataclasses import replace
from decimal import Decimal
import re

from stratbox.shared.data.values import Assessment, IntegratedDataset, JsonEvidence, SourceDataset, TableEvidenceSet
from ..common.semantics import IDENTIFIERS
from ..common.evidence import interpreted_use
from .publications import parse_day


def select_records(inputs, settings, context):
    physical = inputs["physical"]
    if not isinstance(physical, JsonEvidence):
        raise TypeError("fns.sme.json_evidence_required")
    if physical.material.source_id not in {None, settings.source_id}:
        raise ValueError("fns.sme.source_mismatch")
    if not isinstance(physical.value, (tuple, list)) or not physical.value or len(physical.value) > settings.max_records:
        raise ValueError("fns.sme.records_invalid")
    if any(not isinstance(item, Mapping) for item in physical.value):
        raise ValueError("fns.sme.record_not_object")
    metadata = {"tokens": getattr(physical, "tokens", {}), **dict(physical.material.metadata)}
    tables = TableEvidenceSet(tuple(physical.value), physical.material, settings.source_id,
        str(metadata.get("issue_id", "")), physical.assessment, metadata)
    return {"tables": tables, "coverage": physical.assessment}


def _integer(value):
    if type(value) is int and 0 <= value < 10**18:
        return value
    if isinstance(value, str) and re.fullmatch(r"0|[1-9][0-9]{0,17}", value):
        return int(value)
    raise ValueError("fns.sme.nonnegative_integer_required")


def interpret_counters(inputs, settings, context):
    tables = inputs["tables"]
    if not isinstance(tables, TableEvidenceSet) or tables.source_id != settings.source_id:
        raise ValueError("fns.sme.source_mismatch")
    issue = inputs.get("issue") or tables.issue_id or getattr(context, "parameters", {}).get("as_of")
    if isinstance(issue, Mapping):
        if issue.get("source_id", settings.source_id) != settings.source_id:
            raise ValueError("fns.sme.issue_source_mismatch")
        issue = issue.get("as_of", issue.get("issue_id"))
    elif issue is not None and hasattr(issue, "issue_id"):
        if getattr(issue, "source_id", settings.source_id) != settings.source_id:
            raise ValueError("fns.sme.issue_source_mismatch")
        issue = issue.issue_id
    expected_day = parse_day(issue) if issue else None
    rows, findings, seen, present, levels = [], [], set(), set(), set()
    tokens = tables.metadata.get("tokens", {})
    material_id = tables.material.identity.sha256 if tables.material else "unretained"
    observed_days = set()
    for ordinal, record in enumerate(tables.tables):
        context.checkpoint()
        source_day = record.get("stat_date")
        if not isinstance(source_day, str) or not re.fullmatch(r"\d{2}\.\d{2}\.20\d{2} 00:00:00", source_day):
            raise ValueError("fns.sme.source_date_format_changed")
        day = parse_day(source_day[:10])
        observed_days.add(day)
        if expected_day is not None and day != expected_day:
            raise ValueError("fns.sme.source_date_mismatch")
        level, label = record.get("cnt_level"), record.get("cnt_name")
        if type(level) is not int or level not in {0, 1, 2} or not isinstance(label, str) or not label.strip():
            raise ValueError("fns.sme.geography_invalid")
        subject = record.get("ssrf") if level == 0 else label
        if not isinstance(subject, str) or not subject or level == 0 and not re.fullmatch(r"[0-9]{1,3}", subject):
            raise ValueError("fns.sme.geography_code_invalid")
        if (level, subject) in seen:
            raise ValueError("fns.sme.duplicate_geography")
        seen.add((level, subject))
        levels.add(level)
        values = {field: _integer(record[field]) for field in settings.counters if field in record}
        for total, parts in (("cnt_total", ("cnt_ul_total", "cnt_ip_total")),
            ("cnt_ul_total", ("cnt_ul_micro", "cnt_ul_mini", "cnt_ul_normal")),
            ("cnt_ip_total", ("cnt_ip_micro", "cnt_ip_mini", "cnt_ip_normal"))):
            if total in values and all(part in values for part in parts) and values[total] != sum(values[part] for part in parts):
                raise ValueError("fns.sme.counter_total_inconsistent")
        missing = set(settings.counters) - values.keys()
        findings.extend("fns.sme.counter_missing:" + field for field in sorted(missing))
        findings.extend("fns.sme.unmapped_field:" + field for field in sorted(set(record) - IDENTIFIERS - set(settings.counters)))
        namespace, perimeter = {
            0: ("fns.ssrf", "published_subject"),
            1: ("fns.sme.federal_district", "published_federal_district"),
            2: ("fns.sme.country", "published_national"),
        }[level]
        for field, value in values.items():
            present.add(field)
            raw = tokens.get((ordinal, field))
            if raw is None:
                raw = str(record[field])
            rows.append({"metric": field, "subject": subject, "subject_namespace": namespace,
                "published_label": label, "geographic_level": level,
                "period": day.isoformat(), "period_kind": "as_of", "frequency": "monthly",
                "measure_kind": "stock", "unit": "count", "scale": Decimal(1),
                "perimeter": perimeter, "value": value, "value_status": "reported",
                "raw_token": raw, "evidence_ref": f"sha256:{material_id}#json:{ordinal}:{field}"})
    if len(observed_days) != 1:
        raise ValueError("fns.sme.mixed_observation_dates")
    if levels != {0, 1, 2}:
        findings.append("fns.sme.geographic_levels_partial")
    assessment = Assessment("partial" if findings else "complete", tuple(dict.fromkeys(findings)),
        settings.counters, tuple(field for field in settings.counters if field in present))
    day = next(iter(observed_days))
    dataset = SourceDataset(settings.source_id, tuple(rows),
        {"grain": ("subject_namespace", "subject", "metric", "period", "perimeter"),
         "period_model": "stock_at_published_stat_date", "physical_fields_retained": True},
        day.isoformat(), (tables.material.identity,) if tables.material else (), assessment,
        source_uses=interpreted_use(tables, settings.source_id, day.isoformat(),
            tuple(sorted({tuple(sorted((key, type(value).__name__) for key, value in record.items()))
                for record in tables.tables})), settings))
    return {"dataset": dataset, "assessment": assessment}


def align_observations(inputs, settings, context):
    dataset = inputs["dataset"]
    if dataset.source_id != settings.source_id:
        raise ValueError("fns.sme.source_mismatch")
    aliases = dict(settings.aliases)
    rows = []
    for row in dataset.rows:
        if row["metric"] not in aliases or row["measure_kind"] != "stock" or row["unit"] != "count":
            raise ValueError("fns.sme.unreviewed_metric")
        rows.append({**row, "metric": aliases[row["metric"]], "source_field": row["metric"]})
    value = IntegratedDataset(dataset.source_id, tuple(rows), dataset.semantics,
        dataset.issue_id, (*dataset.lineage, dataset.identity), dataset.assessment,
        source_uses=dataset.source_uses)
    return {"dataset": value, "assessment": value.assessment}


