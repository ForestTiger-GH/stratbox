"""Strict bounded JSON/JSONL and spreadsheet-safe, schema-limited CSV projections."""
from __future__ import annotations

import csv
from datetime import datetime
from decimal import Decimal
from io import StringIO
import json
from collections.abc import Iterable, Iterator, Mapping

from stratbox.shared.data import ByteIdentity
from stratbox.core.execution.contracts import Correlation
from stratbox.core.observability.records.contracts import JournalRecord, ObjectRef

MAX_LINE_BYTES = 2 * 1024 * 1024
DEFAULT_MAX_SEGMENT_BYTES = 8 * 1024 * 1024
MAX_SEGMENT_BYTES = 128 * 1024 * 1024
DEFAULT_MAX_RECORDS = 100_000


class JournalDecodeError(ValueError):
    def __init__(self, code: str, *, line: int | None = None):
        self.code, self.line = code, line
        super().__init__(code + (f" at line {line}" if line is not None else ""))


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
            val = obj["$stratbox_decimal"]
            if type(val) is not str or len(val) > 1024:
                raise JournalDecodeError("journal.decimal_invalid")
            try:
                dec = Decimal(val)
                if dec.is_finite():
                    return dec
            except (ArithmeticError, ValueError):
                pass
            raise JournalDecodeError("journal.decimal_invalid")
        if len(obj) == 1 and "$stratbox_integer" in obj:
            val = obj["$stratbox_integer"]
            if type(val) is not str or len(val) > 1024 or not val.lstrip("-").isdigit():
                raise JournalDecodeError("journal.integer_invalid")
            return int(val)
        return {k: _restore(v) for k, v in obj.items()}
    return obj


def _ref(obj: ObjectRef) -> dict[str, object]:
    return {"namespace": obj.namespace, "object_id": obj.object_id, "relation": obj.relation,
            "version_id": obj.version_id,
            "identity": {"sha256": obj.identity.sha256, "size": obj.identity.size} if obj.identity else None}


def record_to_dict(record: JournalRecord) -> dict[str, object]:
    return {
        "schema_version": record.schema_version, "record_id": record.record_id,
        "record_type": record.record_type, "kind": record.kind,
        "occurred_at_utc": record.occurred_at_utc.isoformat(),
        "observed_at_utc": record.observed_at_utc.isoformat() if record.observed_at_utc else None,
        "correlation": {k: getattr(record.correlation, k) for k in Correlation.__dataclass_fields__},
        "invocation_id": record.invocation_id, "operation_id": record.operation_id,
        "fact_id": record.fact_id, "subject": _ref(record.subject) if record.subject else None,
        "references": [_ref(x) for x in record.references],
        "cause_record_ids": list(record.cause_record_ids), "outcome": record.outcome,
        "sequence": record.sequence, "payload": _value(record.payload),
    }


_REQUIRED_FIELDS = frozenset(record_to_dict(JournalRecord(
    "template", "diagnostic", "diagnostic.sample", datetime.fromisoformat("2026-01-01T00:00:00+00:00"), {}
)))


def _parse_ref(obj):
    if obj is None:
        return None
    if not isinstance(obj, dict):
        raise ValueError("Invalid reference")
    identity = obj.get("identity")
    if identity is not None and (not isinstance(identity, dict) or set(identity) != {"sha256", "size"}):
        raise ValueError("Invalid byte identity")
    return ObjectRef(obj["namespace"], obj["object_id"], obj.get("relation", "subject"),
                     obj.get("version_id"), ByteIdentity(**identity) if identity else None)


def record_from_dict(value: Mapping[str, object]) -> JournalRecord:
    try:
        if not isinstance(value, dict):
            raise ValueError("Expected journal mapping")
        if value.get("schema_version") != 1:
            raise JournalDecodeError("journal.unsupported_schema")
        if set(value) != _REQUIRED_FIELDS:
            raise ValueError("Journal schema mismatch")
        corr = value["correlation"]
        if not isinstance(corr, dict) or set(corr) != set(Correlation.__dataclass_fields__):
            raise ValueError("Invalid correlation")
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
    except JournalDecodeError:
        raise
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        raise JournalDecodeError("journal.record_invalid") from None


def _unique_keys(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError("Duplicate JSON key")
        out[k] = v
    return out


def _load_json(data: bytes):
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=_unique_keys,
                          parse_constant=lambda x: (_ for _ in ()).throw(ValueError("Invalid numeric")),
                          parse_int=lambda x: int(x) if len(x) <= 1024 else (_ for _ in ()).throw(ValueError("Oversized int")),
                          parse_float=lambda x: (_ for _ in ()).throw(ValueError("Floating numeric not permitted")))
    except (UnicodeError, ValueError, OverflowError, RecursionError):
        raise JournalDecodeError("journal.json_invalid") from None


def encode_record(record: JournalRecord) -> bytes:
    out = json.dumps(record_to_dict(record), ensure_ascii=False, sort_keys=True,
                     allow_nan=False, separators=(",", ":")).encode("utf-8")
    if len(out) > MAX_LINE_BYTES:
        raise ValueError("journal.record_too_large")
    return out


def decode_record(data: bytes) -> JournalRecord:
    if len(data) > MAX_LINE_BYTES:
        raise JournalDecodeError("journal.record_too_large")
    return record_from_dict(_load_json(data))


def encode_records(records: Iterable[JournalRecord], *, format: str = "jsonl",
                   max_bytes: int = DEFAULT_MAX_SEGMENT_BYTES, max_records: int = DEFAULT_MAX_RECORDS) -> bytes:
    if format not in {"json", "jsonl"}:
        raise ValueError("Unsupported journal format")
    chunks: list[bytes] = []
    total = 2 if format == "json" else 0
    for n, item in enumerate(records, 1):
        if n > max_records:
            raise ValueError("journal.record_limit")
        data = encode_record(item)
        count = len(data) + (1 if format == "jsonl" or n > 1 else 0)
        total += count
        if total > max_bytes:
            raise ValueError("journal.segment_too_large")
        chunks.append(data)
    return b"".join(x + b"\n" for x in chunks) if format == "jsonl" else b"[" + b",".join(chunks) + b"]"


def iter_decode_jsonl(lines: Iterable[bytes], *, max_records: int = DEFAULT_MAX_RECORDS) -> Iterator[JournalRecord]:
    for index, line in enumerate(lines, 1):
        if index > max_records:
            raise JournalDecodeError("journal.record_limit", line=index)
        if len(line) > MAX_LINE_BYTES + 1:
            raise JournalDecodeError("journal.record_too_large", line=index)
        if not line.strip():
            raise JournalDecodeError("journal.blank_line", line=index)
        try:
            yield decode_record(line)
        except JournalDecodeError as exc:
            raise JournalDecodeError(exc.code, line=index) from exc


def decode_records(data: bytes, *, format: str = "jsonl",
                   max_bytes: int = DEFAULT_MAX_SEGMENT_BYTES, max_records: int = DEFAULT_MAX_RECORDS) -> tuple[JournalRecord, ...]:
    if len(data) > max_bytes:
        raise JournalDecodeError("journal.segment_too_large")
    if format == "jsonl":
        return tuple(iter_decode_jsonl(data.splitlines(keepends=True), max_records=max_records))
    if format == "json":
        value = _load_json(data)
        if not isinstance(value, list):
            raise JournalDecodeError("journal.json_invalid")
        if len(value) > max_records:
            raise JournalDecodeError("journal.record_limit")
        return tuple(record_from_dict(obj) for obj in value)
    raise ValueError("Unsupported journal format")


