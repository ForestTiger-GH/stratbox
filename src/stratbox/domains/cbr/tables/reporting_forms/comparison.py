"""Compare source form records separately from financial-model results."""
from dataclasses import dataclass
from .contracts import FormFlakes
from .flakes import validate_flakes
from stratbox.shared.data.comparison import Comparison, ComparisonLayers
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes

@dataclass(frozen=True, slots=True)
class CompareFormFlakesRequest:
    candidate: FormFlakes
    baseline: FormFlakes | None = None
    baseline_state: str = "unavailable"


def fingerprints(value):
    structure=[];facts=[]
    for member in value.members:
        table=member.table
        structure.append((member.name,member.status,None if table is None else [(f.name,f.field_type,f.length,f.decimals) for f in table.fields]))
        if table is not None:
            facts.append((member.name,[(r.ordinal,r.deleted,r.values) for r in table.records]))
    return (ByteIdentity.of(canonical_manifest_bytes({"structure":structure})),
            ByteIdentity.of(canonical_manifest_bytes({"decoded_records":facts})))


def compare(request):
    validate_flakes(request.candidate)
    if request.baseline_state not in {"available","confirmed_absent","unavailable"}:
        raise ValueError("request.baseline_state_invalid")
    if request.baseline is None:
        return Comparison("first_seen","baseline.confirmed_absent") if request.baseline_state=="confirmed_absent" else Comparison("indeterminate","baseline.unavailable")
    if request.baseline_state != "available":
        return Comparison("indeterminate","baseline.unqualified")
    validate_flakes(request.baseline)
    old,new=request.baseline,request.candidate
    if old.key.code != new.key.code:
        return Comparison("indeterminate","comparison.form_source_incompatible")
    if old.key.as_of != new.key.as_of:
        return Comparison("new_release","comparison.form_reporting_date_changed")
    old_structure,old_facts=fingerprints(old);new_structure,new_facts=fingerprints(new)
    layers=ComparisonLayers(original="same" if old.original_identity==new.original_identity else "changed",
        structure="same" if old_structure==new_structure else "changed",
        facts="same" if old_facts==new_facts else "changed",
        method="same" if old.method_version==new.method_version else "changed")
    if not old.complete or not new.complete:
        return Comparison("indeterminate","comparison.form_member_coverage_incomplete",layers=layers)
    if layers.method=="changed" or layers.structure=="changed":
        return Comparison("indeterminate","comparison.form_schema_or_method_changed",layers=layers)
    return Comparison("unchanged" if layers.facts=="same" else "revised","comparison.form_decoded_records",layers=layers)
