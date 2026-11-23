"""Project one reviewed source table without evaluating a financial model."""
from pathlib import PurePosixPath
from types import MappingProxyType
from stratbox.core.execution import OperationFailure
from stratbox.core.runtime.dependencies import require_extra
from stratbox.core.operations.tables import record_tables
from .contracts import FormSnapshot
from .context import normalized_metadata
from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
from .flakes import validate_flakes
from .layouts.registry import LAYOUT_REGISTRY

def normalize_value(req, invocation):
    value = req.flakes
    validate_flakes(value)
    if type(req.include_deleted) is not bool:
        raise ValueError("request.deleted_policy_invalid")
    if value.key.code not in LAYOUT_REGISTRY:
        raise OperationFailure("source.form_layout_unsupported")
    if not value.complete:
        raise OperationFailure("source.form_flakes_incomplete")
    from stratbox.domains.cbr.tables.reporting_forms.layouts.schema import DirectDatasetSpec, normalize_direct_snapshot
    pd = require_extra("pandas", "dataframe")
    spec = LAYOUT_REGISTRY[value.key.code].spec
    direct = isinstance(spec, DirectDatasetSpec)
    if direct:
        required = {"REGN": spec.bank_fields, "CODE": spec.code_fields, **spec.measure_fields}
        optional, preferred = spec.optional_measure_fields, spec.prefer_stem_contains
    else:
        required, optional = spec.fields, {"SIDE": spec.side_fields} if spec.side_fields else {}
        preferred = spec.preferred_stem
    candidates = []
    for member in value.members:
        if member.table is None:
            continue
        fields = {field.name.upper(): field.name for field in member.table.fields}
        resolved = {}
        score = 20 if preferred and preferred.casefold() in PurePosixPath(member.name).stem.casefold() else 0
        for canonical, aliases in {**required, **optional}.items():
            physical = next((fields[alias] for alias in aliases if alias in fields), None)
            if physical is not None:
                resolved[canonical] = physical
                score += physical.upper() == aliases[0]
        if required.keys() <= resolved.keys():
            candidates.append((score, member, resolved))
    if not candidates:
        raise ValueError("DBF_LAYOUT_UNRECOGNIZED")
    candidates.sort(key=lambda item: item[0], reverse=True)
    if len(candidates) > 1 and candidates[0][0] == candidates[1][0]:
        raise ValueError("DBF_LAYOUT_AMBIGUOUS")
    _, member, fields = candidates[0]
    invocation.stage("normalize")
    for receipt in value.lineage:
        invocation.use(receipt)
    positions = {field.name: index for index, field in enumerate(member.table.fields)}
    columns = tuple(required) + tuple(optional)
    selected_records = tuple(record for record in member.table.records if req.include_deleted or not record.deleted)
    rows = [tuple(record.values[positions[fields[name]]] if name in fields else None for name in columns)
            for record in selected_records]
    frame = pd.DataFrame(rows, columns=columns, dtype="object")
    frame["_source_member"] = member.name
    frame["_source_record"] = [record.ordinal for record in selected_records]
    if frame.empty:
        raise OperationFailure("source.dbf_empty")
    if direct:
        frame = normalize_direct_snapshot(frame, spec)
    if frame.empty:
        raise OperationFailure("source.dbf_no_observations")
    source_uses = (SourceUse(SourceCoordinate("cbr.reporting_forms.f" + value.key.code, "cbr.reporting_forms",
        "reported_records", value.key.as_of.isoformat(), material_identity=value.original_identity,
        layout_edition=LAYOUT_REGISTRY[value.key.code].edition), "flake", "domain_validated"),)
    evidence = record_tables(invocation, (("dbf_rows", frame),),
        metadata=normalized_metadata(value.key, fields, source_uses),
        parameters={"member": member.name, "include_deleted": req.include_deleted,
                    "flake_method": value.method_version})
    return FormSnapshot(value.key, MappingProxyType(fields), frame, tuple(invocation.used_inputs), evidence, source_uses)
