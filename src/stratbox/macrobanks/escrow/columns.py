"""
columns — распознавание показателей таблицы счетов эскроу.

Листовые коды фиксируются словарем и не вычисляются динамически.
Это позволяет сохранить существующие рабочие ссылки на листы итогового Excel.
"""

from __future__ import annotations

import re

from stratbox.macrobanks.escrow.models import EscrowIndicatorSpec, ResolvedEscrowColumn


ESCROW_INDICATOR_SPECS: tuple[EscrowIndicatorSpec, ...] = (
    EscrowIndicatorSpec(
        code="active_credit_contracts_count",
        canonical_name="Кол-во действующих кредитных договоров",
        sheet_code="КДКД",
        required_tokens=("кол", "во", "действующих", "кредитных", "договоров"),
        order=1,
    ),
    EscrowIndicatorSpec(
        code="active_credit_contracts_amount_mln_rub",
        canonical_name="Сумма действующих кредитных договоров, млн руб.",
        sheet_code="СДКДМР",
        required_tokens=("сумма", "действующих", "кредитных", "договоров", "млн", "руб"),
        order=2,
    ),
    EscrowIndicatorSpec(
        code="debt_mln_rub",
        canonical_name="Задолженность, млн руб.",
        sheet_code="ЗМР",
        required_tokens=("задолженность", "млн", "руб"),
        order=3,
    ),
    EscrowIndicatorSpec(
        code="escrow_accounts_count",
        canonical_name="Кол-во счетов эскроу",
        sheet_code="КСЭ",
        required_tokens=("кол", "во", "счетов", "эскроу"),
        order=4,
    ),
    EscrowIndicatorSpec(
        code="escrow_balance_mln_rub",
        canonical_name="Остатки средств на счетах эскроу, млн руб.",
        sheet_code="ОСНСЭМР",
        required_tokens=("остатки", "средств", "счетах", "эскроу", "млн", "руб"),
        order=5,
    ),
    EscrowIndicatorSpec(
        code="weighted_rate_federal_district_percent",
        canonical_name="Средневзвешенная ставка по кредитным договорам по федеральному округу, %",
        sheet_code="ССПКДПФО",
        required_tokens=(
            "средневзвешенная",
            "ставка",
            "кредитным",
            "договорам",
            "федеральному",
            "округу",
            "процент",
        ),
        order=6,
        value_kind="percent",
    ),
    EscrowIndicatorSpec(
        code="revealed_escrow_accounts_count",
        canonical_name="Кол-во «раскрытых» счетов эскроу",
        sheet_code="КРСЭ",
        required_tokens=("кол", "во", "раскрытых", "счетов", "эскроу"),
        order=7,
    ),
    EscrowIndicatorSpec(
        code="revealed_escrow_amount_mln_rub",
        canonical_name='Сумма средств, перечисленных с «раскрытых» счетов эскроу, млн руб.',
        sheet_code="ССПСРСЭМР",
        required_tokens=("сумма", "средств", "перечисленных", "раскрытых", "счетов", "эскроу", "млн", "руб"),
        order=8,
    ),
)

HEADER_SUBJECT_REQUIRED_TOKENS: tuple[str, ...] = (
    "субъект",
    "российской",
    "федерации",
    "федеральный",
    "округ",
)


def normalize_header_text(value: object) -> str:
    """Нормализует заголовок столбца для устойчивого распознавания."""
    if value is None:
        return ""

    text = str(value)
    text = text.replace("\u00a0", " ")
    text = text.replace("ё", "е").replace("Ё", "Е")
    text = text.replace("«", " ").replace("»", " ")
    text = text.replace('"', " ").replace("'", " ")
    text = text.replace("%", " процент ")
    text = re.sub(r"(?<=\D)\d+\)?(?=\s|$)", " ", text)
    text = re.sub(r"[^0-9A-Za-zА-Яа-я]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def is_subject_header_cell(value: object) -> bool:
    """Проверяет, что ячейка похожа на заголовок второго столбца таблицы."""
    normalized = normalize_header_text(value)
    tokens = set(normalized.split())
    return set(HEADER_SUBJECT_REQUIRED_TOKENS).issubset(tokens)


def _spec_matches_header(spec: EscrowIndicatorSpec, normalized_header: str) -> bool:
    """Проверяет, что нормализованный заголовок соответствует спецификации."""
    if not normalized_header:
        return False
    tokens = set(normalized_header.split())
    return set(spec.required_tokens).issubset(tokens)


def _select_best_spec(
    candidates: list[EscrowIndicatorSpec],
    *,
    sequential_position: int,
    used_codes: set[str],
) -> EscrowIndicatorSpec:
    """Выбирает лучшую спецификацию из списка кандидатов с учетом позиции."""
    unused_candidates = [spec for spec in candidates if spec.code not in used_codes]
    if not unused_candidates:
        raise ValueError("No unused escrow indicator spec is available for the current column")

    expected_order = sequential_position + 1
    exact_position = [spec for spec in unused_candidates if spec.order == expected_order]
    if len(exact_position) == 1:
        return exact_position[0]

    if len(unused_candidates) == 1:
        return unused_candidates[0]

    ranked = sorted(
        unused_candidates,
        key=lambda spec: (abs(spec.order - expected_order), spec.order),
    )
    best = ranked[0]
    if len(ranked) > 1 and abs(ranked[0].order - expected_order) == abs(ranked[1].order - expected_order):
        raise ValueError(
            "Ambiguous escrow indicator header mapping: "
            f"candidates={[spec.code for spec in ranked]}"
        )
    return best



def resolve_indicator_spec_by_header(source_name: object, *, sequential_position: int | None = None) -> EscrowIndicatorSpec:
    """Сопоставляет один заголовок со спецификацией показателя."""
    normalized = normalize_header_text(source_name)
    matches = [spec for spec in ESCROW_INDICATOR_SPECS if _spec_matches_header(spec, normalized)]
    if not matches:
        raise ValueError(
            "Escrow indicator header is not recognized: "
            f"header={source_name!r}, normalized={normalized!r}"
        )

    if sequential_position is not None:
        expected_order = sequential_position + 1
        same_position = [spec for spec in matches if spec.order == expected_order]
        if len(same_position) == 1:
            return same_position[0]

    if len(matches) == 1:
        return matches[0]

    ranked = sorted(
        matches,
        key=lambda spec: (-len(spec.required_tokens), spec.order),
    )
    if len(ranked) > 1 and len(ranked[0].required_tokens) == len(ranked[1].required_tokens):
        raise ValueError(
            "Ambiguous escrow indicator header mapping: "
            f"candidates={[spec.code for spec in ranked]}"
        )
    return ranked[0]


def resolve_indicator_columns(header_values: list[object] | tuple[object, ...]) -> list[ResolvedEscrowColumn]:
    """
    Сопоставляет реальные столбцы Excel со стандартным набором показателей.

    Ожидается, что первые два значения header_values соответствуют служебным столбцам:
    - № п/п
    - субъект РФ / федеральный округ
    """
    if len(header_values) < 10:
        raise ValueError("Escrow header row has too few columns")

    resolved: list[ResolvedEscrowColumn] = []
    used_codes: set[str] = set()

    indicator_headers = list(header_values[2:])
    for sequential_position, source_name in enumerate(indicator_headers):
        normalized = normalize_header_text(source_name)
        if not normalized:
            continue

        spec = resolve_indicator_spec_by_header(source_name, sequential_position=sequential_position)
        if spec.code in used_codes:
            raise ValueError(f"Duplicate escrow indicator header is detected: {source_name!r}")
        used_codes.add(spec.code)
        resolved.append(
            ResolvedEscrowColumn(
                source_name=str(source_name).strip(),
                source_index=sequential_position + 2,
                spec=spec,
            )
        )

    expected_codes = {spec.code for spec in ESCROW_INDICATOR_SPECS}
    if used_codes != expected_codes:
        missing = [spec.code for spec in ESCROW_INDICATOR_SPECS if spec.code not in used_codes]
        extra = sorted([code for code in used_codes if code not in expected_codes])
        raise ValueError(
            "Escrow indicators are resolved incompletely: "
            f"missing={missing}, extra={extra}"
        )

    resolved = sorted(resolved, key=lambda item: item.spec.order)
    return resolved


def sheet_code_by_indicator_code(indicator_code: str) -> str:
    """Возвращает фиксированный код листа по внутреннему коду показателя."""
    for spec in ESCROW_INDICATOR_SPECS:
        if spec.code == indicator_code:
            return spec.sheet_code
    raise KeyError(f"Unknown escrow indicator code: {indicator_code}")


__all__ = [
    "ESCROW_INDICATOR_SPECS",
    "HEADER_SUBJECT_REQUIRED_TOKENS",
    "is_subject_header_cell",
    "normalize_header_text",
    "resolve_indicator_columns",
    "resolve_indicator_spec_by_header",
    "sheet_code_by_indicator_code",
]
