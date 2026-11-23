"""Reading representations retain literal source material and spreadsheet cell evidence."""
from dataclasses import dataclass
from stratbox.shared.evidence import SourcePayload
from stratbox.shared.data.representation import Representation

@dataclass(frozen=True, slots=True)
class ReadableOfficesRequest:
    payload: SourcePayload
    family: str


def readable(request, invocation):
    from stratbox.core.execution import OperationFailure
    from stratbox.core.operations.source.validation import use_payload, decode_html
    use_payload(request.payload,invocation,role="source_office_material",limit=10*1024*1024)
    if request.family == "bank_offices":
        from .bank_offices.parser import CaptureError, extract_records
        from stratbox.core.operations.source.validation import source_failure
        try:
            extract_records(decode_html(request.payload))
        except (CaptureError, UnicodeError, ValueError) as error:
            raise source_failure(error) from None
        return Representation("cbr.offices.native-html",1,"text/html",request.payload.data)
    if request.family != "territorial_offices":
        raise OperationFailure("request.office_family_unknown")
    from .territorial_offices.parser import CaptureError, xlsx_rows
    from stratbox.core.operations.source.validation import source_failure
    import json
    lines=["# Published credit-institution office tables", "", "All decoded nonempty worksheet cells are listed with their source coordinates. Formula caches are preserved as read; formulas are not evaluated.", ""]
    try:
        worksheets=xlsx_rows(request.payload.data,budget=invocation.budget,checkpoint=invocation.check_cancelled)
    except (CaptureError, ValueError) as error:
        raise source_failure(error) from None
    for name, rows, formulas, _ in worksheets:
        lines.extend(("## "+name,"","| Source row | Source column | Published token |","| --- | --- | --- |"))
        for row, cells in rows:
            for column, value in cells.items():
                text=value.replace("\\","\\\\").replace("|","\\|").replace("\n","<br>")
                lines.append(f"| {row} | {column} | {text} |")
        for (row,column), evidence in sorted(formulas.items()):
            lines.append(f"\nFormula evidence at row {row}, column {column}: `{json.dumps(evidence,ensure_ascii=False,sort_keys=True)}`")
        lines.append("")
    data="\n".join(lines).encode("utf-8")
    invocation.budget.charge("output_bytes",len(data))
    return Representation("cbr.offices_reg.readable-cells",1,"text/markdown",data,"utf-8")
