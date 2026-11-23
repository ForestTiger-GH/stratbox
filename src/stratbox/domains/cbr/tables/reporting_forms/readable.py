"""A faithful reading view of decoded DBF records and their physical qualifications."""
from .flakes import validate_flakes
from stratbox.shared.data.representation import Representation


def readable(value, invocation):
    validate_flakes(value)
    import json
    lines=[f"# Reporting form {value.key.code}","",f"Reporting date: {value.key.as_of.isoformat()}",
           "", "Decoded source tokens are preserved as JSON strings. Deleted-record flags remain explicit. Auxiliary or unsupported members retain their separate source originals.", ""]
    for member in value.members:
        lines.extend(("## "+member.name,"",f"Status: {member.status}; original SHA-256: {member.identity.sha256}",""))
        if member.table is None:
            lines.append("Source member has no admitted DBF reading representation.")
            if member.diagnostic:lines.append("Diagnostic: "+member.diagnostic)
            continue
        table=member.table
        lines.append("Encoding: "+table.encoding+"; profile: "+table.profile)
        lines.append("Fields: "+json.dumps([(f.name,f.field_type,f.length,f.decimals) for f in table.fields],ensure_ascii=False))
        lines.extend(("","```jsonl"))
        for row in table.records:
            invocation.check_cancelled()
            lines.append(json.dumps({"record":row.ordinal,"deleted":row.deleted,"values":row.values},ensure_ascii=False))
        lines.extend(("```",""))
    data="\n".join(lines).encode("utf-8")
    invocation.budget.charge("output_bytes",len(data))
    return Representation("cbr.forms.readable-records",1,"text/markdown",data,"utf-8")
