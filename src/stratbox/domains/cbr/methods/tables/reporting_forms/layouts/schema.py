"""Physical table layouts and source-local token normalization."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping
import re

def _is_missing_scalar(value: Any) -> bool:
    """Recognize a missing scalar without importing a dataframe implementation."""
    return _is_na(value)


def normalize_regn(value: Any) -> str:
    """Normalize source registration tokens while preserving integer float IDs."""
    if value is None:
        return ""
    if isinstance(value, float):
        if value != value:
            return ""
        if float(value).is_integer():
            return str(int(value))
    if isinstance(value, int):
        return str(int(value))

    text = str(value).strip()
    if re.fullmatch(r"[0-9]+\.0+", text):
        return text.split(".", 1)[0]
    return re.sub(r"\D+", "", text)


def normalize_code_plain(value: Any) -> str:
    """Trim source codes without converting dotted identifiers to numbers."""
    return "" if _is_missing_scalar(value) else str(value).strip()


def normalize_code_metric(value: Any) -> str:
    """Normalize ratio identifiers, including the Cyrillic/Latin H spelling."""
    text = "" if _is_missing_scalar(value) else str(value)
    text = re.sub(r"\s+", "", text.strip().upper())
    return text.replace("Н", "H")


@dataclass(frozen=True)
class DirectDatasetSpec:
    """Physical field alternatives for one direct source dataset.

    Required and optional measure channels are separate. Financial models use
    channel identities independently of the physical DBF field spelling.
    """

    form: str
    dataset: str
    bank_fields: tuple[str, ...]
    code_fields: tuple[str, ...]
    measure_fields: dict[str, tuple[str, ...]]
    optional_measure_fields: dict[str, tuple[str, ...]] = field(default_factory=dict)
    prefer_stem_contains: str | None = None
    code_normalizer: Callable[[Any], str] = normalize_code_plain
    code_aliases: dict[str, str] = field(default_factory=dict)


def _build_alias_map(spec: DirectDatasetSpec) -> dict[str, str]:
    """Normalize the layout's explicitly reviewed indicator aliases."""
    aliases: dict[str, str] = {}
    for source, target in spec.code_aliases.items():
        source_n = spec.code_normalizer(source)
        target_n = spec.code_normalizer(target)
        if source_n:
            aliases[source_n] = target_n
    return aliases


def _normalize_code(value: Any, spec: DirectDatasetSpec, alias_map: dict[str, str]) -> str:
    """Apply a source-code normalizer and the reviewed physical aliases."""
    code = spec.code_normalizer(value)
    return alias_map.get(code, code)


def normalize_direct_snapshot(raw, spec: DirectDatasetSpec) -> object:
    alias_map = _build_alias_map(spec)
    frame = raw.copy()
    frame["REGN"] = frame["REGN"].map(normalize_regn)
    frame["CODE"] = frame["CODE"].map(lambda value: _normalize_code(value, spec, alias_map))
    return frame.loc[frame["REGN"].ne("") & frame["CODE"].ne("")].reset_index(drop=True)


def plain_account(value: object) -> str:
    if value is None or _is_na(value):
        return ""
    return str(value).strip().replace(",", ".")


def integer_account(value: object) -> str:
    token = plain_account(value)
    if re.fullmatch(r"[0-9]+(?:\.0+)?", token):
        return str(int(token.split(".")[0]))
    return ""


@dataclass(frozen=True)
class FormulaDatasetSpec:
    form: str
    dataset: str
    fields: Mapping[str, tuple[str, ...]]
    preferred_stem: str
    normalize_account: Callable[[object], str] = plain_account
    side_fields: tuple[str, ...] = ()
    account_plan: str | None = None


def _is_na(value):
    if value is None:
        return True
    try:
        return bool(value != value)
    except (TypeError, ValueError):
        return True
