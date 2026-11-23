"""Small explicit scalar vocabulary for source cells and retained views."""
from datetime import date, datetime, time, timedelta
from decimal import Decimal


def encode_scalar(value):
    if value is None:
        return "null", ""
    if type(value) is bool:
        return "boolean", "true" if value else "false"
    if type(value) is int:
        return "integer", str(value)
    if type(value) is Decimal and value.is_finite():
        return "decimal", str(value)
    if type(value) is str:
        return "text", value
    if type(value) in {date, datetime, time}:
        return type(value).__name__, value.isoformat()
    if type(value) is timedelta:
        return "duration", str((value.days * 86400 + value.seconds) * 1_000_000 + value.microseconds)
    raise ValueError("cells.scalar_unsupported")


def decode_scalar(kind, text):
    if kind == "null" and text == "":
        return None
    if kind == "boolean" and text in {"true", "false"}:
        return text == "true"
    if kind == "integer":
        value = int(text)
    elif kind == "decimal":
        value = Decimal(text)
    elif kind == "text":
        value = text
    elif kind in {"date", "datetime", "time"}:
        value = {"date": date, "datetime": datetime, "time": time}[kind].fromisoformat(text)
    elif kind == "duration":
        value = timedelta(microseconds=int(text))
    else:
        raise ValueError("cells.scalar_invalid")
    if encode_scalar(value) != (kind, text):
        raise ValueError("cells.scalar_noncanonical")
    return value
