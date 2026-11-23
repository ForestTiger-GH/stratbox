"""Align reviewed source tables while keeping source constructs and identities."""
from dataclasses import asdict
from decimal import Decimal, InvalidOperation
import re
from stratbox.shared.data.observations import MetricRef, Observation, ObservationBatch, PeriodRef, SubjectRef
from stratbox.shared.identity import canonical_manifest_bytes, ByteIdentity
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
from stratbox.core.execution import OperationFailure
from stratbox.core.operations.tables import use_tables
from stratbox.domains.cbr.tables.reporting_forms.layouts.registry import LAYOUT_REGISTRY
from stratbox.domains.cbr.tables.reporting_forms.layouts.schema import DirectDatasetSpec


def align(request, invocation):
    if not request.snapshots or not request.dataset_id or not request.version_id:
        raise OperationFailure("request.form_alignment_invalid")
    periods = dict(request.periods)
    if len(periods) != len(request.periods):
        raise OperationFailure("request.form_period_duplicate")
    subjects = {(item.source_namespace, item.source_id): item for item in request.subjects}
    if len(subjects) != len(request.subjects) or any(not item.edition.strip() for item in request.subjects):
        raise OperationFailure("request.form_subject_mapping_invalid")
    identities = [(s.key.code, s.key.as_of) for s in request.snapshots]
    if len(identities) != len(set(identities)):
        raise OperationFailure("request.form_revision_selection_required")
    flow_dates = {snapshot.key.as_of for snapshot in request.snapshots if snapshot.key.code == "102"}
    if set(periods) - flow_dates:
        raise OperationFailure("request.form_flow_period_unmatched")
    invocation.stage("align")
    observations, seen = [], set()
    for snapshot in sorted(request.snapshots, key=lambda s: (s.key.code, s.key.as_of)):
        code = snapshot.key.code
        if code not in LAYOUT_REGISTRY:
            raise OperationFailure("source.form_layout_unsupported")
        spec = LAYOUT_REGISTRY[code].spec
        frame, = use_tables(invocation, (("dbf_rows", snapshot.rows),), receipt=snapshot.evidence,
            role="form_source_projection", metadata={"form": code, "as_of": snapshot.key.as_of,
                                                      "fields": dict(snapshot.physical_fields)})
        for receipt in snapshot.lineage:
            invocation.use(receipt)
        period = periods.get(snapshot.key.as_of)
        if code == "102":
            if period is None or period.kind != "interval" or period.end > snapshot.key.as_of:
                raise OperationFailure("request.form_flow_period_required")
        else:
            period = PeriodRef("as_of", snapshot.key.as_of)
        if period.kind == "capture":
            raise OperationFailure("request.form_observation_period_invalid")
        namespace = ("cbr.banking_group.registration" if snapshot.physical_fields.get("REGN", "").upper() == "REGN_GKO"
                     else "cbr.bank.registration")
        channels = tuple({**spec.measure_fields, **spec.optional_measure_fields}) if isinstance(spec, DirectDatasetSpec) else ("VALUE",)
        unit, scale, kind = ("percent", Decimal(1), "ratio") if code in {"135", "805"} else (
            "RUB", Decimal(1000), "flow" if code == "102" else "stock")
        for index, row in enumerate(frame.to_dict("records"), 1):
            invocation.check_cancelled()
            subject_id = str(row["REGN"]).strip()
            if not re.fullmatch(r"[0-9]+(?:\.0+)?", subject_id):
                raise OperationFailure("source.form_subject_invalid")
            subject_id = subject_id.split(".")[0]
            source = SubjectRef(namespace, subject_id)
            mapping = subjects.get((namespace, subject_id))
            subject = mapping.target if mapping else source
            source_code = str(row["CODE"]).strip()
            if not source_code:
                raise OperationFailure("source.form_indicator_invalid")
            for channel in channels:
                raw = row.get(channel)
                token = None if raw is None else str(raw)
                if raw is None:
                    value, status = None, "missing"
                elif not token.strip():
                    value, status = None, "blank"
                elif token.strip() in {"-", "–", "—"}:
                    value, status = None, "dash"
                else:
                    try:
                        value = Decimal(token.strip().replace(",", "."))
                    except InvalidOperation:
                        raise OperationFailure("source.form_numeric_token_invalid") from None
                    if not value.is_finite():
                        raise OperationFailure("source.form_numeric_token_invalid")
                    status = "reported"
                dimensions = [("form", code), ("reporting_date", snapshot.key.as_of.isoformat()),
                              ("source_dataset", spec.dataset), ("source_code", source_code),
                              ("measure", channel), ("source_subject_namespace", namespace), ("source_subject_id", subject_id)]
                for name in ("PLAN", "SIDE"):
                    if row.get(name) is not None:
                        dimensions.append((name.lower(), str(row[name])))
                if mapping:
                    dimensions.append(("subject_mapping_edition", mapping.edition))
                metric = MetricRef(f"cbr.forms.{code}.{spec.dataset}.{source_code}.{channel}", unit, kind,
                                   LAYOUT_REGISTRY[code].edition, scale)
                key = subject, metric, period, tuple(dimensions)
                if key in seen:
                    raise OperationFailure("source.form_duplicate_observation")
                seen.add(key)
                member = str(row.get("_source_member", "selected_table"))
                ordinal = row.get("_source_record", index)
                observations.append(Observation(subject, metric, period, tuple(dimensions),
                    "consolidated_group" if namespace.endswith("group.registration") else "credit_institution",
                    value, status, f"form:{code}/{snapshot.key.as_of.isoformat()}/{member}/record:{ordinal}/field:{snapshot.physical_fields.get(channel, channel)}", token))
    mapping_bytes = canonical_manifest_bytes({"periods": [(day, asdict(period)) for day, period in request.periods], "subjects": [asdict(item) for item in request.subjects]})
    invocation.use(UsedInputReceipt.for_payload(SourcePayload(mapping_bytes, "application/json"), "form_alignment_rules"))
    result = ObservationBatch(request.dataset_id, 1, request.version_id, tuple(observations), tuple(invocation.used_inputs))
    invocation.budget.charge("objects", len(observations))
    invocation.record(ByteIdentity.of(canonical_manifest_bytes(asdict(result))))
    return result
