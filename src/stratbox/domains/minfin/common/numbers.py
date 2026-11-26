"""Source-local exact numeric tokens with distinct missing-value meanings."""
from decimal import Decimal, InvalidOperation
import re


def numeric_value(raw: str | None):
    if raw is None:
        return None, "missing"
    token = raw.strip()
    if not token:
        return None, "blank"
    if token in {"-", "—", "–"}:
        return None, "dash"
    normalized = token.replace("\u00a0", "").replace("\u202f", "").replace(" ", "").replace(",", ".")
    if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?", normalized):
        raise ValueError("minfin.integration.numeric_value_invalid")
    try:
        value = Decimal(normalized)
    except InvalidOperation:
        raise ValueError("minfin.integration.numeric_value_invalid") from None
    if not value.is_finite():
        raise ValueError("minfin.integration.numeric_value_invalid")
    return value, "reported"

