"""Reporting-form interpretation consumes already decoded DBF evidence."""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from types import MappingProxyType

from stratbox.domains.cbr.common.provenance import source_use
from stratbox.domains.cbr.common.issues import issue_parameters
from stratbox.shared.data.values import Assessment, DbfEvidence, SourceDataset, TableEvidenceSet


# Physical alternatives are source facts, not another catalog of executable work.
FIELDS = MappingProxyType({
    "101": (("REGN",), ("NUM_SC",), (("VALUE", ("IITG",)),), ("PLAN", "A_P"), "balance"),
    "102": (("REGN",), ("CODE",), (("VALUE", ("SIM_ITOGO", "SIM_ITOG", "SIM_R")),), (), "pnl"),
    "123": (("REGN",), ("C1",), (("VALUE", ("C3",)),), (), "capital"),
    "134": (("REGN",), ("C1",), (("C3", ("C3",)),), (), "published_fields"),
    "135": (("REGN",), ("C1_3",), (("actual", ("C2_3",)),), (), "section3"),
    "802": (("REGN_GKO",), ("STR",), (("total", ("VSEGO",)),
        ("consolidation_plus", ("KORR_P",)), ("consolidation_minus", ("KORR_M",)),
        ("intragroup_adjustment", ("KORR_GR",))), (), "main"),
    "803": (("REGN_GKO",), ("RAZDEL", "STR"), (("KORR_P", ("KORR_P",)),
        ("KORR_M", ("KORR_M",)), ("VSEGO", ("VSEGO",))), (), "published_fields"),
    "805": (("REGN_GKO", "REGN"), ("NAME_NORM", "C1_3"), (("actual", ("FAKT_ZN", "C2_3")),), (), "normatives"),
})


def _field(names, alternatives):
    return next((name for name in alternatives if name in names), None)


def _shape(physical, settings):
    names = {item.name: item for item in physical.fields}
    subjects, codes, channels, extras, dataset = FIELDS[settings.code]
    subject = _field(names, subjects)
    code_fields = tuple(codes) if settings.code == "803" else ((_field(names, codes),) if _field(names, codes) else ())
    selected = tuple((channel, _field(names, alternatives)) for channel, alternatives in channels)
    if subject is None or not code_fields or not selected or selected[0][1] is None:
        return None
    if settings.code in {"134", "803"}:
        if any(name not in names or (names[name].field_type, names[name].length) != (kind, width)
               for name, kind, width in settings.required_fields):
            raise ValueError("cbr.form_published_geometry_mismatch")
        if any(value is None for _, value in selected):
            raise ValueError("cbr.form_published_field_missing")
    return subject, code_fields, tuple((key, value) for key, value in selected if value is not None), extras, dataset


def extract(inputs, settings, context):
    physical = inputs["physical"]
    values = (physical,) if isinstance(physical, DbfEvidence) else tuple(physical) if isinstance(physical, (tuple, list)) else ()
    if not values or any(not isinstance(item, DbfEvidence) for item in values):
        raise ValueError("cbr.form_dbf_evidence_required")
    issue_ids, retained_uses = set(), []
    for item in values:
        material = item.material
        issue = str(material.metadata.get("issue_id") or context.parameters.get("issue_id", ""))
        if issue:
            issue_ids.add(issue)
        if material.source_id == "cbr.reporting_forms.publications":
            from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
            expected_asset = "form-0409" + settings.code
            container = material.metadata.get("container_asset_id", material.metadata.get("asset_id"))
            parent = material.metadata.get("parent")
            expected_identity = (next((identity for identity in material.lineage
                if getattr(identity, "sha256", None) == parent), None) if parent else material.identity)
            verify = getattr(context, "verify_source_use", None)
            uses = tuple(getattr(material, "source_uses", ()))
            matched = tuple(use for use in uses if use.coordinate.source_id == material.source_id
                and use.coordinate.issue_id == issue and use.coordinate.asset_id == expected_asset
                and use.coordinate.material_identity == expected_identity)
            if (container != expected_asset or not issue or expected_identity is None or not matched
                    or verify is None or not all(verify(use) for use in matched)):
                raise ValueError("cbr.form_feed_relation_unqualified")
            retained_uses.extend(matched)
            retained_uses.append(SourceUse(SourceCoordinate(source_id=settings.series_id,
                family_id=material.source_id, issue_id=issue,
                asset_id=str(material.metadata.get("member", expected_asset)), material_identity=material.identity),
                "source_dbf", "domain_validated", "sha256:" + material.identity.sha256))
        elif material.source_id not in {None, settings.series_id}:
            raise ValueError("cbr.form_source_mismatch")
    if len(issue_ids) > 1 or issue_ids and context.parameters.get("issue_id") not in {None, "", next(iter(issue_ids))}:
        raise ValueError("cbr.form_issue_conflict")
    admitted = tuple(item for item in values if _shape(item, settings) is not None)
    if not admitted:
        raise ValueError("cbr.form_fields_unsupported")
    metadata = {"form": settings.code, "all_members": tuple(item.material.identity for item in values),
        "source_uses": tuple(dict.fromkeys(retained_uses))}
    tables = TableEvidenceSet(admitted, admitted[0].material, settings.series_id,
        next(iter(issue_ids), str(context.parameters.get("issue_id", ""))), Assessment(), metadata)
    return {"tables": tables, "coverage": tables.assessment}


def _number(token):
    if token is None or not str(token).strip():
        return None, "blank"
    text = str(token).strip()
    if text in {"-", "—", "–"}:
        return None, "dash"
    if text in {"...", "…", "н/д"}:
        return None, "missing"
    try:
        value = Decimal(text.replace(" ", "").replace(",", "."))
    except InvalidOperation:
        return None, "unparsed"
    return (value, "reported") if value.is_finite() else (None, "unparsed")


def _period(settings, parameters, issue):
    supplied = parameters.get("period")
    if supplied is not None:
        if isinstance(supplied, tuple) and len(supplied) == 2:
            start, end = (date.fromisoformat(str(value)) for value in supplied)
            if start > end:
                raise ValueError("cbr.form_period_invalid")
            return (start.isoformat(), end.isoformat()), "interval"
        if hasattr(supplied, "kind"):
            if supplied.kind == "interval":
                return (supplied.start.isoformat(), supplied.end.isoformat()), "interval"
            return supplied.as_of.isoformat(), "as_of"
        return date.fromisoformat(str(supplied)).isoformat(), "as_of"
    if settings.require_measurement:
        raise ValueError("cbr.form_published_measurement_required")
    if settings.code == "102":
        raise ValueError("cbr.form_flow_period_required")
    observed = date.fromisoformat(issue)
    return observed.isoformat(), "as_of"


def interpret(inputs, settings, context):
    tables = inputs["tables"]
    if not isinstance(tables, TableEvidenceSet) or tables.source_id != settings.series_id:
        raise ValueError("cbr.form_tables_required")
    parameters = issue_parameters(inputs, context, tables.issue_id)
    issue = str(parameters.get("issue_id") or tables.issue_id)
    period, period_kind = _period(settings, parameters, issue)
    if settings.code == "102" and (period_kind != "interval" or period[1] >= issue):
        raise ValueError("cbr.form_flow_period_invalid")
    if settings.code in {"101", "123", "135", "802", "805"} and (period_kind != "as_of" or str(period) != issue):
        raise ValueError("cbr.form_stock_date_mismatch")
    if settings.require_measurement and ("unit" not in parameters or "scale" not in parameters):
        raise ValueError("cbr.form_published_measurement_required")
    unit, scale = parameters.get("unit", settings.unit), Decimal(str(parameters.get("scale", settings.scale)))
    if not scale.is_finite() or scale <= 0:
        raise ValueError("cbr.form_scale_invalid")
    if settings.code == "134" and (period_kind != "as_of" or str(period) != issue):
        raise ValueError("cbr.form_stock_date_mismatch")
    if settings.code == "803" and (period_kind != "interval" or issue and period[1] >= issue):
        raise ValueError("cbr.form_flow_period_required")
    rows, findings, lineage = [], set(), []
    for physical in tables.tables:
        shape = _shape(physical, settings)
        if shape is None:
            raise ValueError("cbr.form_fields_unsupported")
        subject_field, code_fields, channels, extras, dataset = shape
        names = [field.name for field in physical.fields]
        lineage.append(physical.material.identity)
        for record in physical.records:
            context.checkpoint()
            if record.deleted:
                continue
            values = dict(zip(names, record.values))
            subject = str(values[subject_field]).strip().lstrip("0") or "0"
            if not subject.isdecimal() or subject == "0":
                findings.add("cbr.form_subject_unparsed")
                continue
            codes = tuple(str(values[name]).strip() for name in code_fields)
            if not all(codes):
                continue
            code = ":".join(codes)
            if settings.code in {"135", "805"}:
                code = code.upper().replace("Н", "H").replace(" ", "")
                if code in {"H20.2", "H20.4"}:
                    code = code.replace(".", "_")
            for channel, field in channels:
                value, status = _number(values[field])
                if status == "unparsed":
                    findings.add("cbr.form_numeric_token_unparsed")
                namespace = "cbr.banking_group.registration" if subject_field == "REGN_GKO" else "cbr.bank.registration"
                quantity = "ratio" if settings.code in {"135", "805"} else "flow" if settings.code in {"102", "803"} else "stock"
                row = {"subject_namespace": namespace, "subject": subject,
                    "metric": f"cbr.forms.{settings.code}.{dataset}.{code}.{channel}",
                    "unit": "percent" if quantity == "ratio" else unit,
                    "scale": Decimal(1) if quantity == "ratio" else scale,
                    "measure_kind": quantity, "period": period, "period_kind": period_kind,
                    "perimeter": "consolidated_group" if subject_field == "REGN_GKO" else "credit_institution",
                    "value": value, "value_status": status, "raw_token": values[field],
                    "form": settings.code, "source_dataset": dataset, "source_code": code,
                    "measure": channel, "reporting_date": issue,
                    "evidence_ref": f"sha256:{physical.material.identity.sha256}#record={record.ordinal}&field={field}",
                    "dimensions": tuple((key, str(values[key])) for key in extras if key in values)}
                rows.append(row)
    if not rows:
        raise ValueError("cbr.form_no_observations")
    assessment = Assessment("partial" if findings else "complete", tuple(sorted(findings)),
        qualifications=frozenset({"published_fields_only"}) if settings.code in {"134", "803"} else frozenset())
    uses = (*tuple(tables.metadata.get("source_uses", ())),
        *(source_use(settings.series_id, issue, identity, role="source_dbf") for identity in lineage))
    dataset = SourceDataset(settings.series_id, tuple(rows), {"form": settings.code}, issue,
        tuple(lineage), assessment, source_uses=tuple(dict.fromkeys(uses)))
    return {"dataset": dataset, "assessment": assessment}
