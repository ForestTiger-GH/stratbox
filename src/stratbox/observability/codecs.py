"""Strict versioned JSON, JSONL and named CSV-projection encodings."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from io import StringIO
import json
from typing import Iterable, Iterator, Mapping

from stratbox.data import ByteIdentity
from stratbox.execution.contracts import Correlation
from .contracts import JournalRecord, ObjectRef

MAX_LINE_BYTES = 2 * 1024 * 1024


class JournalDecodeError(ValueError):
    def __init__(self, code: str, *, line: int | None = None):
        self.code = code
        self.line = line
        super().__init__(f"{code}" + (f" at line {line}" if line is not None else ""))


def _value(obj):
    if isinstance(obj, Decimal):
        return {"$stratbox_decimal": str(obj)}
    if type(obj) is int and abs(obj) > 2**53 - 1:
        return {"$stratbox_integer": str(obj)}
    if isinstance(obj, (tuple, list)):
        return [_value(x) for x in obj]
    if isinstance(obj, Mapping):
        return {k: _value(v) for k, v in obj.items()}
    return obj


def _restore(obj):
    if isinstance(obj, list):
        return [_restore(x) for x in obj]
    if isinstance(obj, dict):
        if len(obj) == 1 and "$stratbox_decimal" in obj:
            try:
                dec = Decimal(obj["$stratbox_decimal"])
                if dec.is_finite():
                    return dec
            except (TypeError, ValueError, ArithmeticError):
                pass
            raise JournalDecodeError("journal.decimal_invalid")
        if len(obj) == 1 and "$stratbox_integer" in obj:
            text = obj["$stratbox_integer"]
            if not isinstance(text, str) or not text.lstrip("-").isdigit() or len(text) > 1024:
                raise JournalDecodeError("journal.integer_invalid")
            return int(text)
        return {k: _restore(v) for k, v in obj.items()}
    return obj


def _ref(obj: ObjectRef) -> dict[str, object]:
    return {"namespace": obj.namespace, "object_id": obj.object_id, "relation": obj.relation,
            "version_id": obj.version_id,
            "identity": ({"sha256": obj.identity.sha256, "size": obj.identity.size} if obj.identity else None)}


def record_to_dict(record: JournalRecord) -> dict[str, object]:
    return {
        "schema_version": record.schema_version, "record_id": record.record_id,
        "record_type": record.record_type, "kind": record.kind,
        "occurred_at_utc": record.occurred_at_utc.isoformat(),
        "observed_at_utc": record.observed_at_utc.isoformat() if record.observed_at_utc else None,
        "correlation": {key: getattr(record.correlation, key) for key in Correlation.__dataclass_fields__},
        "invocation_id": record.invocation_id, "operation_id": record.operation_id,
        "fact_id": record.fact_id, "subject": _ref(record.subject) if record.subject else None,
        "references": [_ref(x) for x in record.references],
        "cause_record_ids": list(record.cause_record_ids), "outcome": record.outcome,
        "sequence": record.sequence, "payload": _value(record.payload),
    }


def _parse_ref(obj):
    if obj is None:
        return None
    if not isinstance(obj, dict):
        raise ValueError("Invalid object reference")
    identity = obj.get("identity")
    return ObjectRef(obj["namespace"], obj["object_id"], obj.get("relation", "subject"),
                     obj.get("version_id"), ByteIdentity(**identity) if identity else None)


def record_from_dict(value: Mapping[str, object]) -> JournalRecord:
    try:
        if not isinstance(value, dict):
            raise ValueError("Expected journal object")
        if set(value) != set(record_to_dict(JournalRecord("template", "diagnostic", "diagnostic.sample",
                                         datetime.fromisoformat("2026-01-01T00:00:00+00:00"), {}))):
            raise ValueError("Journal schema keys disagree")
        corr = value["correlation"]
        return JournalRecord(
            value["record_id"], value["record_type"], value["kind"],
            datetime.fromisoformat(value["occurred_at_utc"]), _restore(value["payload"]),
            schema_version=value["schema_version"],
            observed_at_utc=datetime.fromisoformat(value["observed_at_utc"]) if value["observed_at_utc"] else None,
            correlation=Correlation(**corr), invocation_id=value["invocation_id"],
            operation_id=value["operation_id"], fact_id=value["fact_id"],
            subject=_parse_ref(value["subject"]),
            references=tuple(_parse_ref(x) for x in value["references"]),
            cause_record_ids=tuple(value["cause_record_ids"]), outcome=value["outcome"],
            sequence=value["sequence"],
        )
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        if isinstance(error, JournalDecodeError):
            raise
        raise JournalDecodeError("journal.record_invalid") from error


def encode_record(record: JournalRecord) -> bytes:
    result = json.dumps(record_to_dict(record), ensure_ascii=False, sort_keys=True, allow_nan=False,
                        separators=(",", ":")).encode("utf-8")
    if len(result) > MAX_LINE_BYTES:
        raise ValueError("Journal record exceeds the supported line limit")
    return result


def decode_record(data: bytes) -> JournalRecord:
    if len(data) > MAX_LINE_BYTES:
        raise JournalDecodeError("journal.record_too_large")
    try:
        doc = json.loads(data.decode("utf-8"), parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    except (UnicodeError, ValueError) as error:
        raise JournalDecodeError("journal.json_invalid") from error
    return record_from_dict(doc)


def encode_records(records: Iterable[JournalRecord], *, format: str = "jsonl") -> bytes:
    if format == "jsonl":
        return b"".join(encode_record(x) + b"\n" for x in records)
    if format == "json":
        return b"[" + b",".join(encode_record(x) for x in records) + b"]"
    raise ValueError("Unsupported journal format")


def iter_decode_jsonl(lines: Iterable[bytes]) -> Iterator[JournalRecord]:
    for index, line in enumerate(lines, 1):
        if not line.strip():
            raise JournalDecodeError("journal.blank_line", line=index)
        try:
            yield decode_record(line)
        except JournalDecodeError as exc:
            raise JournalDecodeError(exc.code, line=index) from exc


def decode_records(data: bytes, *, format: str = "jsonl") -> tuple[JournalRecord, ...]:
    if format == "jsonl":
        return tuple(iter_decode_jsonl(data.splitlines(keepends=True)))
    if format == "json":
        try:
            values = json.loads(data.decode("utf-8"))
            if not isinstance(values, list):
                raise ValueError("Journal JSON requires array")
            return tuple(record_from_dict(x) for x in values)
        except (UnicodeError, ValueError) as exc:
            raise JournalDecodeError("journal.json_invalid") from exc
    raise ValueError("Unsupported journal format")


def export_projection_csv(rows: Iterable[Mapping[str, object]], *, columns: tuple[str, ...]) -> bytes:
    if not columns or len(set(columns)) != len(columns):
        raise ValueError("A distinct CSV projection schema is required")
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="raise", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        if any(key not in columns for key in row):
            raise ValueError("Projection has columns outside the schema")
        writer.writerow({k: "" if row.get(k) is None else str(row[k]) for k in columns})
    return output.getvalue().encode("utf-8")
