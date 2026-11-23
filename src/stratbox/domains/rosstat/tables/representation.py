"""Human-readable source-flake tables, separate from physical workbook evidence."""
import csv
from io import StringIO
from stratbox.shared.data.representation import Representation
from .contracts import RosstatSourceFlake


def readable_flake(value: RosstatSourceFlake) -> Representation:
    stream=StringIO(newline="")
    writer=csv.writer(stream)
    writer.writerow(("indicator_id","label","measure","frequency","period_start","period_end","display_date",
        "value","status","unit","scale","unit_literal","raw_token","footnotes","source_locator","source_sha256"))
    for row in value.values:
        writer.writerow((row.indicator_id,row.label,row.measure,row.frequency,row.period_start.isoformat(),
            row.period_end.isoformat(),row.display_date.isoformat(),str(row.value) if row.value is not None else "",
            row.value_status,row.unit or "",str(row.scale),row.unit_literal,row.raw_token or "",
            " | ".join(row.footnotes),row.source_locator,value.source_identity.sha256))
    return Representation("rosstat.source_flake.csv",1,"text/csv",stream.getvalue().encode("utf-8-sig"),"utf-8-sig")
