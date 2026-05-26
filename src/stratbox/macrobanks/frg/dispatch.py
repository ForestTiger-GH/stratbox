"""
Диспетчеризация актуальных файлов FRG в будущие парсеры.

На первом этапе диспетчер запускает только заглушки,
но уже проверяет правильность маршрутизации по семействам.
"""

from __future__ import annotations

import pandas as pd

from stratbox.macrobanks.frg.parsers import (
    parse_express_issuance_cards_stub,
    parse_express_issuance_stub,
    parse_express_issuance_weekly_stub,
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
    parse_volumes_cards_q_stub,
)


PARSER_DISPATCH = {
    "express_issuance_stub": parse_express_issuance_stub,
    "express_portfolios_stub": parse_express_portfolios_stub,
    "express_passives_stub": parse_express_passives_stub,
    "express_issuance_weekly_stub": parse_express_issuance_weekly_stub,
    "express_issuance_cards_stub": parse_express_issuance_cards_stub,
    "regional_issuance_stub": parse_regional_issuance_stub,
    "regional_portfolios_stub": parse_regional_portfolios_stub,
    "regional_issuance_mortgage_stub": parse_regional_issuance_mortgage_stub,
    "regional_portfolios_mortgage_stub": parse_regional_portfolios_mortgage_stub,
    "regional_issuance_cards_stub": parse_regional_issuance_cards_stub,
    "rbm_volumes_q_stub": parse_rbm_volumes_q_stub,
    "rbm_portfolios_q_stub": parse_rbm_portfolios_q_stub,
    "volumes_cards_q_stub": parse_volumes_cards_q_stub,
    "mortgage_refinancing_stub": parse_mortgage_refinancing_stub,
}



def dispatch_latest_frg_files(latest_df: pd.DataFrame) -> pd.DataFrame:
    """Запускает заглушки парсеров по таблице актуальных файлов."""
    if latest_df is None or latest_df.empty:
        return pd.DataFrame(
            columns=[
                "family_code",
                "file_name",
                "path",
                "parser_key",
                "status",
                "message",
            ]
        )

    rows: list[dict[str, object]] = []

    for row in latest_df.to_dict(orient="records"):
        parser_key = row.get("parser_key")
        parser = PARSER_DISPATCH.get(parser_key)

        if parser is None:
            rows.append(
                {
                    "family_code": row.get("family_code"),
                    "file_name": row.get("file_name"),
                    "path": row.get("path"),
                    "parser_key": parser_key,
                    "status": "error",
                    "message": "Parser is not registered in dispatch map.",
                }
            )
            continue

        parsed = parser(
            family_code=str(row.get("family_code")),
            file_path=str(row.get("path")),
        )
        parsed["file_name"] = row.get("file_name")
        rows.append(parsed)

    return pd.DataFrame(rows)[
        [
            "family_code",
            "file_name",
            "path",
            "parser_key",
            "status",
            "message",
        ]
    ]
