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
        is_required=False,
    ),
    EscrowIndicatorSpec(
        code="escrow_accounts_count",
        canonical_name="Кол-во счетов эскроу",
        sheet_code="КСЭ",
        required_tokens=("кол", "во", "счетов", "эскроу"),
        forbidden_tokens=("имеющих", "остатки"),
        order=4,
    ),
    EscrowIndicatorSpec(
        code="escrow_accounts_with_balance_count",
        canonical_name="Кол-во счетов эскроу, имеющих остатки",
        sheet_code="КСЭИО",
        required_tokens=("кол", "во", "счетов", "эскроу", "имеющих", "остатки"),
        order=5,
        is_required=False,
    ),
    EscrowIndicatorSpec(
        code="escrow_balance_mln_rub",
        canonical_name="Остатки средств на счетах эскроу, млн руб.",
        sheet_code="ОСНСЭМР",
        required_tokens=("остатки", "средств", "счетах", "эскроу", "млн", "руб"),
        order=6,
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
        order=7,
        value_kind="percent",
    ),
    EscrowIndicatorSpec(
        code="revealed_escrow_accounts_count",
        canonical_name="Кол-во «раскрытых» счетов эскроу",
        sheet_code="КРСЭ",
        required_tokens=("кол", "во", "раскрытых", "счетов", "эскроу"),
        order=8,
    ),
    EscrowIndicatorSpec(
        code="revealed_escrow_amount_mln_rub",
        canonical_name='Сумма средств, перечисленных с «раскрытых» счетов эскроу, млн руб.',
        sheet_code="ССПСРСЭМР",
        required_tokens=("сумма", "средств", "перечисленных", "раскрытых", "счетов", "эскроу", "млн", "руб"),
        order=9,
    ),
)

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
    """Нормализует заголовок столбца для устойчивого распознавания."""
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
    """Проверяет, что ячейка похожа на заголовок второго столбца таблицы."""
    normalized = normalize_header_text(value)
    tokens = set(normalized.split())
    return (
        "субъект" in tokens
        and "округ" in tokens
        and ("федерации" in tokens or "российской" in tokens or "рф" in tokens)
    )


def _spec_matches_header(spec: EscrowIndicatorSpec, normalized_header: str) -> bool:
    """Проверяет, что нормализованный заголовок соответствует спецификации."""
    if not normalized_header:
        return False

    tokens = set(normalized_header.split())
    required_tokens = set(spec.required_tokens)
    forbidden_tokens = set(spec.forbidden_tokens)

    # Для ставки по кредитным договорам в исторических файлах встречаются
    # как формулировки "Средневзвешенная ставка...", так и более старый
    # вариант "Средняя ставка...". Парсер должен устойчиво принимать оба
    # варианта, не смешивая показатель с другими столбцами.
    if spec.code == "weighted_rate_federal_district_percent":
        base_tokens = {"ставка", "кредитным", "договорам", "федеральному", "округу", "процент"}
        adjective_tokens = {"средняя", "средневзвешенная"}
        if not base_tokens.issubset(tokens):
            return False
        if not adjective_tokens.intersection(tokens):
            return False
        if forbidden_tokens.intersection(tokens):
            return False
        return True

    if not required_tokens.issubset(tokens):
        return False
    if forbidden_tokens.intersection(tokens):
        return False
    return True


def resolve_indicator_spec_by_header(source_name: object) -> EscrowIndicatorSpec:
    """Сопоставляет один заголовок со спецификацией показателя."""
    normalized = normalize_header_text(source_name)
    matches = [spec for spec in ESCROW_INDICATOR_SPECS if _spec_matches_header(spec, normalized)]
    if not matches:
        raise ValueError(
            "Escrow indicator header is not recognized: "
            f"header={source_name!r}, normalized={normalized!r}"
        )

    if len(matches) == 1:
        return matches[0]

    ranked = sorted(matches, key=lambda spec: (-len(spec.required_tokens), spec.order))
    best = ranked[0]
    if len(ranked) > 1 and len(ranked[0].required_tokens) == len(ranked[1].required_tokens):
        raise ValueError(
            "Ambiguous escrow indicator header mapping: "
            f"header={source_name!r}, candidates={[spec.code for spec in ranked]}"
        )
    return best


def probe_indicator_columns(
    header_values: list[object] | tuple[object, ...],
    *,
    allow_unknown: bool = True,
) -> tuple[list[ResolvedEscrowColumn], list[tuple[int, str]]]:
    """
    Мягко сопоставляет реальные столбцы Excel со стандартным реестром показателей.

    Возвращает:
    - resolved: распознанные столбцы;
    - unknown_headers: непустые нераспознанные заголовки после первых двух служебных колонок.
    """
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
                source_name=str(source_name).strip(),
                source_index=source_index,
                spec=spec,
            )
        )

    if unknown_headers and not allow_unknown:
        raise ValueError(
            "Escrow header row contains unrecognized non-empty indicator headers: "
            f"{unknown_headers}"
        )

    resolved = sorted(resolved, key=lambda item: item.spec.order)
    return resolved, unknown_headers


def resolve_indicator_columns(
    header_values: list[object] | tuple[object, ...],
    *,
    allow_unknown: bool = False,
) -> list[ResolvedEscrowColumn]:
    """
    Строго сопоставляет реальные столбцы Excel со стандартным набором показателей.

    Для исторических файлов допускается отсутствие части известных показателей.
    Это не считается ошибкой: в итоговых витринах соответствующие даты просто останутся пустыми.
    """
    resolved, unknown_headers = probe_indicator_columns(header_values, allow_unknown=allow_unknown)
    if len(resolved) < _HEADER_MIN_RECOGNIZED_INDICATORS:
        raise ValueError(
            "Escrow indicator header row is recognized too weakly: "
            f"recognized={len(resolved)}, unknown_headers={unknown_headers}"
        )
    return resolved


def get_output_indicator_specs() -> list[EscrowIndicatorSpec]:
    """Возвращает показатели, которые нужно выводить в итоговую книгу."""
    return [spec for spec in sorted(ESCROW_INDICATOR_SPECS, key=lambda item: item.order) if spec.is_output]


def sheet_code_by_indicator_code(indicator_code: str) -> str:
    """Возвращает фиксированный код листа по внутреннему коду показателя."""
    for spec in ESCROW_INDICATOR_SPECS:
        if spec.code == indicator_code:
            return spec.sheet_code
    raise KeyError(f"Unknown escrow indicator code: {indicator_code}")


__all__ = [
    "ESCROW_INDICATOR_SPECS",
    "HEADER_SUBJECT_ALTERNATIVE_TOKENS",
    "HEADER_SUBJECT_REQUIRED_TOKENS",
    "get_output_indicator_specs",
    "is_subject_header_cell",
    "normalize_header_text",
    "probe_indicator_columns",
    "resolve_indicator_columns",
    "resolve_indicator_spec_by_header",
    "sheet_code_by_indicator_code",
]
