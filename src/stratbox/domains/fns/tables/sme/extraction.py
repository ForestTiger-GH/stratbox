"""Complete JSON extraction; selection, interpretation and rendering are downstream."""
from decimal import Decimal
import json

from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.data.snapshots import CoverageDimension, SnapshotCoverage

from ..contracts import JsonField, JsonFlake, JsonRecord
from .parser import FnsError, LIMIT_JSON, _invalid_constant, _unique_object, require

_DECODER = json.JSONDecoder(object_pairs_hook=_unique_object, parse_float=Decimal,
                           parse_constant=_invalid_constant)


def _space(text, position):
    while position < len(text) and text[position] in " \t\r\n":
        position += 1
    return position


def _kind(value):
    return ("null" if value is None else "boolean" if type(value) is bool else
            "integer" if type(value) is int else "decimal" if type(value) is Decimal else
            "string" if type(value) is str else "array" if type(value) is list else "object")


def fields_from_json(text):
    """Retain each literal value token, including nesting and native JSON types."""
    require(text.startswith("{"), "SOURCE_ITEM_NOT_OBJECT")
    position = _space(text, 1)
    result = []
    while position < len(text) and text[position] != "}":
        key, end = _DECODER.raw_decode(text, position)
        require(type(key) is str, "JSON_OBJECT_KEY_INVALID")
        require(key not in {item.name for item in result}, "JSON_DUPLICATE_KEY")
        position = _space(text, end)
        require(position < len(text) and text[position] == ":", "JSON_INVALID")
        position = _space(text, position + 1)
        value, end = _DECODER.raw_decode(text, position)
        result.append(JsonField(key, _kind(value), text[position:end]))
        position = _space(text, end)
        if position < len(text) and text[position] == "}":
            break
        require(position < len(text) and text[position] == ",", "JSON_INVALID")
        position = _space(text, position + 1)
        require(position < len(text) and text[position] != "}", "JSON_INVALID")
    require(position < len(text) and text[position] == "}" and
            _space(text, position + 1) == len(text), "JSON_INVALID")
    return tuple(result)


def extract_json(payload, context, *, budget=None, checkpoint=None):
    require(context.series_id == "fns.sme", "SOURCE_SERIES_MISMATCH")
    require(0 < len(payload.data) <= LIMIT_JSON, "JSON_SIZE_INVALID")
    try:
        text = payload.data.decode("utf-8-sig")
        position = _space(text, 0)
        require(position < len(text) and text[position] == "[", "SOURCE_ROWS_INVALID")
        position = _space(text, position + 1)
        records = []
        while position < len(text) and text[position] != "]":
            if checkpoint is not None:
                checkpoint()
            value, end = _DECODER.raw_decode(text, position)
            require(type(value) is dict, "SOURCE_ITEM_NOT_OBJECT")
            fields = fields_from_json(text[position:end])
            records.append(JsonRecord(len(records), fields))
            if budget is not None:
                budget.charge("cells", len(fields))
            require(len(records) <= 10000, "SOURCE_ROW_LIMIT")
            position = _space(text, end)
            if position < len(text) and text[position] == "]":
                break
            require(position < len(text) and text[position] == ",", "JSON_INVALID")
            position = _space(text, position + 1)
            require(position < len(text) and text[position] != "]", "JSON_INVALID")
        require(position < len(text) and text[position] == "]" and
                _space(text, position + 1) == len(text), "JSON_INVALID")
        require(bool(records), "SOURCE_ROWS_INVALID")
    except (UnicodeError, ValueError, RecursionError):
        raise FnsError("JSON_INVALID") from None
    fields = tuple(dict.fromkeys(field.name for record in records for field in record.fields))
    levels = tuple(dict.fromkeys(str(record.values().get("cnt_level", "unclassified")) for record in records))
    coverage = SnapshotCoverage("complete", "All supplied JSON records, field kinds and literal tokens.", (
        CoverageDimension("fields", requested=fields, materialized=fields, validated=fields, output=fields),
        CoverageDimension("geographic_levels", requested=levels, materialized=levels, output=levels),
    ))
    return JsonFlake(context, payload.identity, tuple(records),
                     (UsedInputReceipt.for_payload(payload, "source_json"),), coverage=coverage)


def json_text(flake):
    """A lossless semantic JSON projection; literal field tokens remain unchanged."""
    return "[" + ",".join("{" + ",".join(
        json.dumps(item.name, ensure_ascii=False) + ":" + item.raw_token
        for item in record.fields) + "}" for record in flake.records) + "]"
