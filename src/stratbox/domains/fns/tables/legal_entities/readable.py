"""Readable workbook evidence includes member inventory and every retained cell."""
from stratbox.shared.data.representation import Representation
from stratbox.shared.data.workbooks import readable_workbook
from stratbox.shared.identity import canonical_manifest_bytes


def readable(flake):
    lines = [canonical_manifest_bytes({"kind": "member_inventory", "name": item.name,
        "sha256": item.identity.sha256, "size": item.identity.size,
        "disposition": item.disposition, "reason": item.reason}) for item in flake.inventory]
    for name, workbook in flake.members:
        lines.append(canonical_manifest_bytes({"kind": "member", "name": name}))
        lines.append(readable_workbook(workbook).data.rstrip(b"\n"))
    return Representation("fns.1yur.readable.jsonl", 1, "application/x-ndjson", b"\n".join(lines) + b"\n", "utf-8")
