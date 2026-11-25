"""Human-readable source-flake tables, separate from physical workbook evidence."""
import csv
from io import StringIO
from stratbox.shared.data.representation import Representation
from .contracts import RosstatSourceFlake
from stratbox.shared.identity import canonical_manifest_bytes


def readable_flake(value: RosstatSourceFlake) -> Representation:
    stream=StringIO(newline="")
    writer=csv.writer(stream)
    writer.writerow(("indicator_id","label","measure","frequency","period_start","period_end","display_date",
        "value","status","unit","scale","unit_literal","raw_token","footnotes","source_locator","source_sha256",
        "geography_namespace","geography_id","period_kind","perimeter","dimensions","source_sheet","source_row",
        "source_column","source_kind","number_format","formula","source_year_literal","period_label_literal","section_notes"))
    for row in value.values:
        writer.writerow((row.indicator_id,row.label,row.measure,row.frequency,row.period_start.isoformat(),
            row.period_end.isoformat(),row.display_date.isoformat(),str(row.value) if row.value is not None else "",
            row.value_status,row.unit or "",str(row.scale),row.unit_literal,row.raw_token or "",
            " | ".join(row.footnotes),row.source_locator,value.source_identity.sha256,
            row.geography_namespace,row.geography_id,row.period_kind,row.perimeter,
            canonical_manifest_bytes(dict(row.dimensions)).decode("utf-8"),row.source_sheet,row.source_row,row.source_column,
            row.source_kind,row.number_format,row.formula or "",row.source_year_literal,row.period_label_literal,
            canonical_manifest_bytes(tuple(note for section in value.sections if section.indicator_id == row.indicator_id
                and section.sheet == row.source_sheet for note in section.notes)).decode("utf-8")))
    return Representation("rosstat.source_flake.csv",1,"text/csv",stream.getvalue().encode("utf-8-sig"),"utf-8-sig")
