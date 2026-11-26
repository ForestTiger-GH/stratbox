"""Resolve published column headers without presentation settings."""
from __future__ import annotations
import re
from stratbox.domains.cbr.methods.tables.project_finance.contracts import EscrowIndicatorSpec, ResolvedEscrowColumn
from stratbox.domains.cbr.common.escrow import ESCROW_INDICATOR_SPECS, ESCROW_COLUMN_RULES, INDICATORS, EscrowColumnRule

HEADER_SUBJECT_REQUIRED_TOKENS: tuple[str, ...] = (
    "субъект",
    "федерации",
    "округ",
)

HEADER_SUBJECT_ALTERNATIVE_TOKENS: tuple[str, ...] = (
    "российской",
    "рф",
)

_HEADER_MIN_RECOGNIZED_INDICATORS = 5


def normalize_header_text(value: object) -> str:
    """Normalize source typography for deterministic header recognition."""
    if value is None:
        return ""

    text = str(value)
    text = text.replace(" ", " ")
    text = text.replace("ё", "е").replace("Ё", "Е")
    text = re.sub(r"\([^)]*\)", " ", text, flags=re.S)
    text = text.replace("«", " ").replace("»", " ")
    text = text.replace('"', " ").replace("'", " ")
    text = text.replace("%", " процент ")
    text = re.sub(r"(?<=\D)\d+\)?(?=\s|$)", " ", text)
    text = re.sub(r"[^0-9A-Za-zА-Яа-я]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def is_subject_header_cell(value: object) -> bool:
    """Recognize the publication subject and federal-district header."""
    # Parentheses can identify the geography level in this particular header.
    text = str(value).replace("(", " ").replace(")", " ") if value is not None else ""
    normalized = normalize_header_text(text)
    tokens = set(normalized.split())
    return (
        "субъект" in tokens
        and "округ" in tokens
        and ("федерации" in tokens or "российской" in tokens or "рф" in tokens)
    )


def _spec_matches_header(spec: EscrowColumnRule, normalized_header: str) -> bool:
    """Match a source column rule against normalized header tokens."""
    if not normalized_header:
        return False

    tokens = set(normalized_header.split())
    required_tokens = set(spec.required_tokens)
    forbidden_tokens = set(spec.forbidden_tokens)

    if not required_tokens.issubset(tokens):
        return False
    if forbidden_tokens.intersection(tokens):
        return False
    return True


def resolve_indicator_spec_by_header(source_name: object) -> EscrowIndicatorSpec:
    """Resolve one header to its reviewed published metric."""
    normalized = normalize_header_text(source_name)
    matches = [spec for spec in ESCROW_COLUMN_RULES if _spec_matches_header(spec, normalized)]
    if not matches:
        raise ValueError(
            "Escrow indicator header is not recognized: "
            f"header={source_name!r}, normalized={normalized!r}"
        )

    if len(matches) == 1:
        return INDICATORS[matches[0].indicator_code]

    ranked = sorted(matches, key=lambda spec: (-len(spec.required_tokens), spec.indicator_code))
    best = ranked[0]
    if len(ranked) > 1 and len(ranked[0].required_tokens) == len(ranked[1].required_tokens):
        raise ValueError(
            "Ambiguous escrow indicator header mapping: "
            f"header={source_name!r}, candidates={[spec.indicator_code for spec in ranked]}"
        )
    return INDICATORS[best.indicator_code]


def probe_indicator_columns(
    header_values: list[object] | tuple[object, ...],
    *,
    allow_unknown: bool = True,
) -> tuple[list[ResolvedEscrowColumn], list[tuple[int, str]]]:
    """Return recognized source columns and preserve every unknown header."""
    if len(header_values) < 3:
        raise ValueError("Escrow header row has too few columns")

    resolved: list[ResolvedEscrowColumn] = []
    used_codes: set[str] = set()
    unknown_headers: list[tuple[int, str]] = []

    for source_index, source_name in enumerate(list(header_values)[2:], start=2):
        normalized = normalize_header_text(source_name)
        if not normalized:
            continue

        try:
            spec = resolve_indicator_spec_by_header(source_name)
        except ValueError:
            unknown_headers.append((source_index, str(source_name).strip()))
            continue

        if spec.code in used_codes:
            raise ValueError(
                "Duplicate escrow indicator header is detected: "
                f"header={source_name!r}, code={spec.code!r}"
            )

        used_codes.add(spec.code)
        resolved.append(
            ResolvedEscrowColumn(
                source_name=str(source_name),
                source_index=source_index,
                spec=spec,
            )
        )

    if unknown_headers and not allow_unknown:
        raise ValueError(
            "Escrow header row contains unrecognized non-empty indicator headers: "
            f"{unknown_headers}"
        )

    resolved = sorted(resolved, key=lambda item: item.source_index)
    return resolved, unknown_headers


def resolve_indicator_columns(
    header_values: list[object] | tuple[object, ...],
    *,
    allow_unknown: bool = False,
) -> list[ResolvedEscrowColumn]:
    """Require a reviewed header while retaining historically absent indicators."""
    resolved, unknown_headers = probe_indicator_columns(header_values, allow_unknown=allow_unknown)
    if len(resolved) < _HEADER_MIN_RECOGNIZED_INDICATORS:
        raise ValueError(
            "Escrow indicator header row is recognized too weakly: "
            f"recognized={len(resolved)}, unknown_headers={unknown_headers}"
        )
    return resolved
