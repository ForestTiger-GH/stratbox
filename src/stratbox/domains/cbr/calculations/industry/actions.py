"""Published industry components form explicit same-period LPK and APK formulas."""
from collections import defaultdict
from decimal import Decimal, localcontext
from stratbox.shared.data.values import Assessment, DerivedDataset, SourceDataset

AGRICULTURE = "agriculture_hunting_services"
FORESTRY_AGRICULTURE = "agriculture_hunting_forestry"
FOOD = "manufacturing_food_beverages_tobacco"
MACHINERY = "manufacturing_machinery_agriculture_forestry"
WOOD = "manufacturing_wood_products"
REQUIRED = frozenset({AGRICULTURE, FORESTRY_AGRICULTURE, FOOD, MACHINERY, WOOD})


def calculate(inputs, settings, context):
    dataset = inputs["dataset"]
    if not isinstance(dataset, SourceDataset) or dataset.source_id != settings.series_id:
        raise ValueError("cbr.apk_dataset_source_mismatch")
    grouped = defaultdict(dict)
    templates = {}
    for row in dataset.rows:
        context.checkpoint()
        metric = row.get("metric")
        if metric in {"apk", "lpk"}:
            raise ValueError("cbr.apk_already_calculated")
        if metric not in REQUIRED:
            continue
        key = (row.get("subject_namespace"), row.get("subject"), str(row.get("period")),
            row.get("period_kind"), row.get("measure_kind"), row.get("frequency"), row.get("perimeter"),
            row.get("unit"), row.get("scale"), row.get("dimensions", ()))
        if metric in grouped[key]:
            raise ValueError("cbr.apk_duplicate_operand")
        grouped[key][metric] = row
        templates[key] = row
    if not grouped:
        raise ValueError("cbr.apk_required_industries_missing")
    output, findings = [], set()
    for key, operands in grouped.items():
        if set(operands) != REQUIRED:
            raise ValueError("cbr.apk_required_industries_missing")
        complete = all(row.get("value") is not None for row in operands.values())
        numbers = {name: Decimal(str(row["value"])) for name, row in operands.items()} if complete else {}
        if complete:
            if not all(value.is_finite() for value in numbers.values()):
                raise ValueError("cbr.apk_finite_operands_required")
            span = max(value.adjusted() for value in numbers.values()) - min(value.as_tuple().exponent for value in numbers.values()) + 4
            if span > 100000:
                raise ValueError("cbr.apk_precision_limit")
            with localcontext() as arithmetic:
                arithmetic.prec = max(28, span)
                lpk = numbers[WOOD] + numbers[FORESTRY_AGRICULTURE] - numbers[AGRICULTURE]
                apk = numbers[AGRICULTURE] + numbers[FOOD] + numbers[MACHINERY] + lpk
        else:
            lpk = apk = None
        if not complete:
            findings.add("cbr.apk_missing_operand_values")
        evidence = tuple(str(operands[name]["evidence_ref"]) for name in sorted(operands))
        for metric, value in (("lpk", lpk), ("apk", apk)):
            row = dict(templates[key])
            row.update(metric=metric, value=value, value_status="derived" if value is not None else "missing",
                metric_label="АПК" if metric == "apk" else "ЛПК", metric_order=27 if metric == "apk" else 28,
                raw_token=None, evidence_ref="cbr.industry_formula:" + metric,
                operands=evidence)
            output.append(row)
    assessment = Assessment("partial" if findings else "complete", tuple(sorted(findings)))
    result = DerivedDataset(dataset.source_id, tuple(output), {"calculation": "industry_components"},
        dataset.issue_id, (*dataset.lineage, dataset.identity), assessment, source_uses=dataset.source_uses)
    return {"dataset": result}
