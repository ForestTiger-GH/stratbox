"""
Заглушки парсеров для квартального блока Retail Banking Market.
"""

from __future__ import annotations


def _stub_payload(*, family_code: str, file_path: str, parser_key: str) -> dict[str, object]:
    """Формирует единый ответ заглушки парсера."""
    return {
        "family_code": family_code,
        "path": file_path,
        "parser_key": parser_key,
        "status": "stub",
        "message": "Parser stub executed. Real parsing is not implemented yet.",
    }


def parse_rbm_volumes_q_stub(*, family_code: str, file_path: str) -> dict[str, object]:
    """Заглушка парсера квартальных объемов Retail Banking Market."""
    return _stub_payload(family_code=family_code, file_path=file_path, parser_key="rbm_volumes_q_stub")


def parse_rbm_portfolios_q_stub(*, family_code: str, file_path: str) -> dict[str, object]:
    """Заглушка парсера квартальных портфелей Retail Banking Market."""
    return _stub_payload(family_code=family_code, file_path=file_path, parser_key="rbm_portfolios_q_stub")


def parse_cards_volumes_q_stub(*, family_code: str, file_path: str) -> dict[str, object]:
    """Заглушка парсера квартальных объемов по картам."""
    return _stub_payload(family_code=family_code, file_path=file_path, parser_key="cards_volumes_q_stub")
