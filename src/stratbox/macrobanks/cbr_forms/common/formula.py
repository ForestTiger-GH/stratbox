"""Evaluate the admitted additive form models against dated source rows."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext
import re
from typing import Callable, Mapping

import pandas as pd

from .direct_form import normalize_regn
from .models import get_model_rows

_TERM = re.compile(r"([+-]?)([0-9A-Za-zА-Яа-я]+(?:\.[0-9]+)?)")


def plain_account(value: object) -> str:
    if value is None or pd.isna(value):
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


def _number(value: object) -> Decimal | None:
    if value is None or pd.isna(value):
        return None
    try:
        number = Decimal(str(value).strip().replace(",", "."))
    except InvalidOperation:
        return None
    return number if number.is_finite() else None


def _terms(text, normalize):
    compact = re.sub(r"\s+", "", text)
    tokens = tuple(_TERM.finditer(compact))
    if (
        not tokens
        or "".join(match[0] for match in tokens) != compact
        or any(not match[1] for match in tokens[1:])
    ):
        raise ValueError("Invalid formula model expression")
    return tuple(
        (-1 if match[1] == "-" else 1, normalize(match[2])) for match in tokens
    )


def build_formula_long(snapshots, banks, model, spec):
    rows = get_model_rows(model, kind="formula", dataset=spec.dataset)
    if rows.empty:
        raise ValueError("Formula model has no applicable rows")
    prepared = []
    for row in rows.to_dict("records"):
        side = re.fullmatch(r"a_p=([12])", row["params"]) if spec.side_fields else None
        if row["params"] and side is None:
            raise ValueError("Invalid account-side model")
        prepared.append(
            (
                row,
                _terms(row["expression"], spec.normalize_account),
                side[1] if side is not None else "",
            )
        )
    result = []
    for as_of, frame in snapshots:
        values = {}
        for bank, account, value, *sides in frame.itertuples(index=False, name=None):
            side = integer_account(sides[0]) if sides else ""
            key = (normalize_regn(bank), spec.normalize_account(account), side)
            if not all(key[:2]):
                continue
            numeric = _number(value)
            if key in values and values[key] != numeric:
                raise ValueError("Conflicting source account rows")
            values[key] = numeric
        side_is_reported = any(side for _, _, side in values)
        for bank, regn in banks[["bank", "regn"]].itertuples(index=False, name=None):
            identity = normalize_regn(regn)
            for row, terms, side in prepared:
                physical_side = side if side_is_reported else ""
                numbers = [
                    (sign, values.get((identity, code, physical_side)))
                    for sign, code in terms
                ]
                with localcontext() as context:
                    context.prec = 40
                    numeric = (
                        sum((sign * amount for sign, amount in numbers), Decimal(0))
                        if all(amount is not None for _, amount in numbers)
                        else ""
                    )
                result.append(
                    {
                        "Форма": spec.form,
                        "Дата": as_of,
                        "REGN": identity,
                        "Банк": bank,
                        "IndicatorId": row["id"],
                        "Код": "",
                        "Показатель": row["name"],
                        "Раздел": row["section"],
                        "Measure": row["measure"],
                        "Значение": numeric,
                        "Единица": row["unit"],
                    }
                )
    return pd.DataFrame(result), {
        row["id"]: int(row["order"]) for row, _, _ in prepared
    }
