"""Source-faithful CSV members and descriptors for neutral saving and packaging."""

import csv
from io import StringIO
from pathlib import PurePosixPath
from datetime import date

from stratbox.core.execution import Completion, OperationFailure, run
from stratbox.core.formats.archives.members import safe_member_name
from stratbox.core.formats.dbf_lossless import DBFField, DBFRecord, DBFTable
from stratbox.core.storage.datasets.codec import loads
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.representation import Representation, CSV
from stratbox.shared.data.snapshots import SnapshotCoverage
from stratbox.shared.material_collections import CollectionDisposition, CollectionManifest, CollectionMember
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes

from .contracts import FormFlakeExport, FormFlakes, FormKey, FormMember
from .flakes import validate_flakes
from .source_definitions import RENDER_FLAKES, READ_FLAKE_EXPORT


def render_flakes(request, *, context=None):
    def work(req, invocation):
        validate_flakes(req.flakes)
        if (type(req.include_member_originals) is not bool or type(req.prefix) is not str
                or req.prefix and (not safe_member_name(req.prefix) or "\\" in req.prefix)):
            raise OperationFailure("request.form_export_invalid")
        root = req.prefix.rstrip("/") + "/" if req.prefix else ""
        value = req.flakes
        files, members, dispositions, descriptions = [], [], [], []
        def add(name, representation, contract):
            key = f"file.{len(files)}"
            files.append((root + name, representation))
            members.append(CollectionMember(key, root + name, contract,
                representation.identity, representation.media_type))
            dispositions.append(CollectionDisposition(key, "completed"))
            return root + name
        invocation.stage("render_csv")
        for ordinal, member in enumerate(value.members):
            invocation.check_cancelled()
            name = member.name.replace("\\", "/")
            entry = {"name": member.name, "identity": {"sha256": member.identity.sha256, "size": member.identity.size},
                     "status": member.status, "diagnostic": member.diagnostic}
            if req.include_member_originals or member.status != "decoded":
                entry["original_path"] = add("source/" + name,
                    Representation("cbr.forms.member-original", 1, "application/x-dbf" if name.lower().endswith(".dbf") else "application/octet-stream", member.data),
                    DataContract("cbr.forms.member.original", 1, DataRole.ORIGINALS))
            if member.table is not None:
                table = member.table
                buffer = StringIO(newline="")
                writer = csv.writer(buffer, lineterminator="\n")
                writer.writerow(field.name for field in table.fields)
                writer.writerows(record.values for record in table.records)
                representation = Representation("cbr.forms.dbf-csv", 1, CSV, buffer.getvalue().encode("utf-8"), "utf-8")
                entry["csv_path"] = add("tables/" + str(PurePosixPath(name).with_suffix(".csv")), representation,
                    DataContract("cbr.forms.dbf.csv", 1, DataRole.EXTRACTS))
                entry["csv_identity"] = {"sha256": representation.identity.sha256, "size": representation.identity.size}
                entry["dbf"] = {"profile": table.profile, "version": table.version,
                    "header_date_bytes": table.header_date.hex(), "header_length": table.header_length,
                    "record_length": table.record_length, "language_driver": table.language_driver,
                    "encoding": table.encoding, "encoding_basis": table.encoding_basis,
                    "eof_marker": table.eof_marker, "record_count": len(table.records),
                    "deleted_records": [record.ordinal for record in table.records if record.deleted],
                    "fields": [{"name": field.name, "type": field.field_type, "length": field.length,
                        "decimals": field.decimals, "offset": field.offset} for field in table.fields]}
            elif member.status in {"unsupported", "failed"}:
                dispositions.append(CollectionDisposition(f"decode.{ordinal}", member.status, member.diagnostic))
            descriptions.append(entry)
        descriptor = {"encoding": "cbr.forms.csv-flakes.v1", "form": value.key.code,
            "report_date": value.key.as_of, "original_identity": {
                "sha256": value.original_identity.sha256, "size": value.original_identity.size},
            "source_id": value.source_id, "media_type": value.media_type,
            "archived": value.archived, "method_version": value.method_version,
            "row_order": "physical", "field_order": "source", "deleted_records": "included",
            "numeric_policy": "source lexical token with fixed-width padding removed",
            "blank_policy": "empty text distinct from zero", "members": descriptions}
        description = Representation("cbr.forms.csv-descriptor", 1, "application/json",
            canonical_manifest_bytes(descriptor), "utf-8")
        add("form.json", description, DataContract("cbr.forms.csv.descriptor", 1, DataRole.EXTRACTS))
        manifest = CollectionManifest(f"cbr.form.{value.key.code}.{value.key.as_of.isoformat()}",
            description.identity.sha256, tuple(members), tuple(dispositions),
            SnapshotCoverage("complete" if value.complete else "partial",
                "Selected supplied release; source history and analytics model coverage are separate."), value.lineage)
        for receipt in value.lineage:
            invocation.use(receipt)
        invocation.record(manifest.identity, parameters={"prefix": req.prefix, "include_member_originals": req.include_member_originals})
        result = FormFlakeExport(tuple(files), manifest)
        return result if value.complete else Completion(result, "partial", "source.form_members_incomplete")
    return run(RENDER_FLAKES, request, work, context=context)


def read_flake_export(request, *, context=None):
    """Reconstruct exported source records; the original DBF is never parsed."""
    def work(req, invocation):
        invocation.stage("read_csv_flakes")
        try:
            if (not isinstance(req.manifest, CollectionManifest) or not isinstance(req.files, tuple)
                    or tuple((name, payload.identity, payload.media_type) for name, payload in req.files)
                    != tuple((item.name, item.identity, item.media_type) for item in req.manifest.members)):
                raise ValueError("cbr.forms.export_members_invalid")
            files = dict(req.files)
            descriptions = [item for item in req.manifest.members if item.contract ==
                DataContract("cbr.forms.csv.descriptor", 1, DataRole.EXTRACTS)]
            if len(descriptions) != 1:
                raise ValueError("cbr.forms.export_descriptor_invalid")
            descriptor = loads(files[descriptions[0].name].data)
            if descriptor["encoding"] != "cbr.forms.csv-flakes.v1":
                raise ValueError("cbr.forms.export_descriptor_invalid")
            members = []
            for entry in descriptor["members"]:
                if "original_path" not in entry:
                    raise ValueError("cbr.forms.export_original_members_required")
                original = files[entry["original_path"]]
                identity = ByteIdentity(**entry["identity"])
                if original.identity != identity:
                    raise ValueError("cbr.forms.export_member_identity_mismatch")
                table = None
                if entry["status"] == "decoded":
                    dbf = entry["dbf"]
                    csv_payload = files[entry["csv_path"]]
                    if csv_payload.identity != ByteIdentity(**entry["csv_identity"]):
                        raise ValueError("cbr.forms.export_csv_identity_mismatch")
                    fields = tuple(DBFField(field["name"], field["type"], field["length"],
                        field["decimals"], field["offset"]) for field in dbf["fields"])
                    rows = list(csv.reader(StringIO(csv_payload.data.decode("utf-8"), newline="")))
                    deleted = dbf["deleted_records"]
                    if (not rows or rows[0] != [field.name for field in fields]
                            or len(rows) - 1 != dbf["record_count"]
                            or any(len(row) != len(fields) for row in rows[1:])
                            or len(set(deleted)) != len(deleted)
                            or any(type(index) is not int or not 1 <= index < len(rows) for index in deleted)):
                        raise ValueError("cbr.forms.export_csv_structure_invalid")
                    flags = set(deleted)
                    table = DBFTable(identity, dbf["version"], bytes.fromhex(dbf["header_date_bytes"]),
                        dbf["header_length"], dbf["record_length"], dbf["language_driver"], dbf["encoding"],
                        dbf["encoding_basis"], fields,
                        tuple(DBFRecord(index, index in flags, tuple(row)) for index, row in enumerate(rows[1:], 1)),
                        dbf["eof_marker"], dbf["profile"])
                members.append(FormMember(entry["name"], original.data, identity, entry["status"], table, entry["diagnostic"]))
            value = FormFlakes(FormKey(descriptor["form"], date.fromisoformat(descriptor["report_date"])),
                ByteIdentity(**descriptor["original_identity"]), descriptor["source_id"], descriptor["media_type"],
                tuple(members), req.manifest.inputs, descriptor["archived"], descriptor["method_version"])
            validate_flakes(value)
        except (ValueError, TypeError, KeyError, UnicodeError) as error:
            from .source_operations import _failure
            raise _failure(error) from None
        for receipt in value.lineage:
            invocation.use(receipt)
        return value if value.complete else Completion(value, "partial", "source.form_members_incomplete")
    return run(READ_FLAKE_EXPORT, request, work, context=context)
