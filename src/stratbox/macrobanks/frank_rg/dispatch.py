"""
Диспетчеризация актуальных файлов Frank RG в будущие парсеры.

На первом этапе диспетчер запускает только заглушки,
но уже проверяет правильность маршрутизации по семействам.
"""

from __future__ import annotations

import pandas as pd

from stratbox.macrobanks.frank_rg.parsers import (
    parse_cards_express_issuance_stub,
    parse_cards_volumes_q_stub,
    parse_express_issuance_stub,
    parse_express_passives_stub,
    parse_express_portfolios_stub,
    parse_mortgage_refinancing_stub,
    parse_rbm_portfolios_q_stub,
    parse_rbm_volumes_q_stub,
    parse_regional_issuance_cards_stub,
    parse_regional_issuance_mortgage_stub,
    parse_regional_issuance_stub,
    parse_regional_portfolios_mortgage_stub,
    parse_regional_portfolios_stub,
    parse_weekly_express_issuance_stub,
)


PARSER_DISPATCH = {
    "express_issuance_stub": parse_express_issuance_stub,
    "express_portfolios_stub": parse_express_portfolios_stub,
    "express_passives_stub": parse_express_passives_stub,
    "weekly_express_issuance_stub": parse_weekly_express_issuance_stub,
    "cards_express_issuance_stub": parse_cards_express_issuance_stub,
    "regional_issuance_stub": parse_regional_issuance_stub,
    "regional_portfolios_stub": parse_regional_portfolios_stub,
    "regional_issuance_mortgage_stub": parse_regional_issuance_mortgage_stub,
    "regional_portfolios_mortgage_stub": parse_regional_portfolios_mortgage_stub,
    "regional_issuance_cards_stub": parse_regional_issuance_cards_stub,
    "rbm_volumes_q_stub": parse_rbm_volumes_q_stub,
    "rbm_portfolios_q_stub": parse_rbm_portfolios_q_stub,
    "cards_volumes_q_stub": parse_cards_volumes_q_stub,
    "mortgage_refinancing_stub": parse_mortgage_refinancing_stub,
}


def dispatch_latest_frank_rg_files(latest_df: pd.DataFrame) -> pd.DataFrame:
    """Запускает заглушки парсеров по таблице актуальных файлов."""
    if latest_df is None or latest_df.empty:
        return pd.DataFrame(
            columns=[
                "family_code",
                "path",
                "parser_key",
                "status",
                "message",
            ]
        )

    rows: list[dict[str, object]] = []

    for row in latest_df.itertuples(index=False):
        parser = PARSER_DISPATCH.get(row.parser_key)
        if parser is None:
            rows.append(
                {
                    "family_code": row.family_code,
                    "path": row.path,
                    "parser_key": row.parser_key,
                    "status": "error",
                    "message": "Parser key is not registered in dispatcher.",
                }
            )
            continue

        result = parser(family_code=row.family_code, file_path=row.path)
        rows.append(result)

    return pd.DataFrame(rows)
