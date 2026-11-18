"""Bank of Russia official workbook with explicit alias and selection resources."""

from __future__ import annotations

from io import BytesIO, StringIO
import csv
import json
import re
from typing import TYPE_CHECKING

from stratbox.shared.evidence import UsedInputReceipt
from stratbox.shared.reference.assets import LoadedReference, ReferenceError, load_reference
from .names import normalize_bank_spelling, normalize_bank_name

if TYPE_CHECKING:
    import pandas as pd

_PACKAGE = "stratbox.shared.reference.banks"


def _csv(bundle: LoadedReference, role: str, *, inputs: list[UsedInputReceipt] | None = None):
    import pandas as pd
    return pd.read_csv(BytesIO(bundle.read(role, inputs=inputs)), dtype=str, encoding="utf-8-sig")


def _aliases(bundle: LoadedReference, inputs: list[UsedInputReceipt] | None = None) -> tuple[dict[str, str], dict[str, list[str]]]:
    raw = bundle.read("aliases", inputs=inputs).decode("utf-8-sig")
    reader = csv.DictReader(StringIO(raw))
    if not reader.fieldnames or not {"canon", "alias"}.issubset(reader.fieldnames):
        raise ReferenceError("Bank aliases require columns canon and alias")
    direct: dict[str, str] = {}
    by_canon: dict[str, list[str]] = {}
    for number, row in enumerate(reader, 2):
        canonical = normalize_bank_spelling(row.get("canon"), placement="omit", case_mode="upper", drop_bank="left")
        alias = normalize_bank_spelling(row.get("alias"), placement="omit", case_mode="upper", drop_bank="left")
        if not canonical or not alias:
            raise ReferenceError(f"Empty bank alias entry at row {number}")
        existing = direct.get(alias)
        if existing is not None and existing != canonical:
            raise ReferenceError(f"Conflicting bank alias {alias!r} at row {number}")
        direct[alias] = canonical
        if alias != canonical and alias not in by_canon.setdefault(canonical, []):
            by_canon[canonical].append(alias)
    for alias, canonical in direct.items():
        if canonical in direct and direct[canonical] != canonical:
            raise ReferenceError(f"Chained/cyclic bank alias mapping is not allowed: {alias!r}")
    return direct, by_canon


def _registration_number(value: object) -> str:
    """Remove only a terminal Excel numeric '.0' marker, preserving other digits."""
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none"}:
        return ""
    return re.sub(r"^(\\d+)\\.0$", r"\\1", text)


def _enabled_selection(bundle: LoadedReference, aliases: dict[str, str], inputs):
    df = _csv(bundle, "default_selection", inputs=inputs)
    if not {"enabled", "bank"}.issubset(df.columns):
        raise ReferenceError("Bank selection requires enabled/bank columns")
    enabled = df["enabled"].astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})
    return {name for name in (
        normalize_bank_name(value, aliases=aliases) for value in df.loc[enabled, "bank"]
    ) if name}


def _legacy_sort(bundle: LoadedReference, inputs):
    df = _csv(bundle, "legacy_selection", inputs=inputs)
    if not {"regn", "sort"}.issubset(df.columns):
        raise ReferenceError("Legacy selection requires regn/sort columns")
    result: dict[str, int] = {}
    for _, row in df.iterrows():
        key = _registration_number(row["regn"])
        rank = str(row["sort"]).strip()
        if not key or not rank or rank.lower() == "nan":
            continue
        try:
            number = int(rank) if rank.isdigit() else int(float(rank))
        except (TypeError, ValueError):
            continue
        if key not in result or number < result[key]:
            result[key] = number
    return result


def read(*, inputs: list[UsedInputReceipt] | None = None, edition_id: str | None = None):
    """Build the bank profile from a complete, byte-verified bundled edition."""
    import pandas as pd
    bundle = load_reference(_PACKAGE, edition_id=edition_id)
    # Every declared resource participates in the returned profile.
    raw = bundle.read("official_xlsx", inputs=inputs)
    df = pd.read_excel(BytesIO(raw))
    cols = {str(c).lower(): c for c in df.columns}
    if not {"cregnum", "bnk_name"}.issubset(cols):
        raise ReferenceError("Official bank workbook requires cregnum/bnk_name columns")
    aliases, by_canon = _aliases(bundle, inputs)
    selected = _enabled_selection(bundle, aliases, inputs)
    legacy = _legacy_sort(bundle, inputs)
    out = df.copy()
    out["regn"] = out[cols["cregnum"]].map(_registration_number)
    out["bank_name"] = out[cols["bnk_name"]].astype(str).str.strip()
    out["bank_name_norm"] = out["bank_name"].map(lambda value: normalize_bank_name(value, aliases=aliases))
    out["is_canonical"] = out["bank_name_norm"].isin(selected)
    out["replacements_list"] = out["bank_name_norm"].map(lambda value: by_canon.get(value, []))
    out["replacements_json"] = out["replacements_list"].map(lambda values: json.dumps(values, ensure_ascii=False))
    sort = out["regn"].map(legacy)
    out["is_legacy"] = sort.astype(object).where(pd.notna(sort), False)
    if "lic_status" in cols:
        out["lic_status"] = out[cols["lic_status"]]
    return out


def lookup(regn: str, *, edition_id: str | None = None) -> dict | None:
    if regn is None:
        return None
    frame = read(edition_id=edition_id)
    hit = frame[frame["regn"] == _registration_number(regn)]
    return None if hit.empty else hit.iloc[0].to_dict()


def normalize_registered_bank(name, *, edition_id: str | None = None):
    """Convenience operation explicitly declaring reference asset access."""
    bundle = load_reference(_PACKAGE, edition_id=edition_id)
    aliases, _ = _aliases(bundle)
    return normalize_bank_name(name, aliases=aliases)
