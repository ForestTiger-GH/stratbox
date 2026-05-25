"""
Заглушки парсеров для регионального блока Frank RG.
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


def parse_regional_issuance_stub(*, family_code: str, file_path: str) -> dict[str, object]:
    """Заглушка парсера общих региональных выдач."""
    return _stub_payload(family_code=family_code, file_path=file_path, parser_key="regional_issuance_stub")


def parse_regional_portfolios_stub(*, family_code: str, file_path: str) -> dict[str, object]:
    """Заглушка парсера общих региональных портфелей."""
    return _stub_payload(family_code=family_code, file_path=file_path, parser_key="regional_portfolios_stub")


def parse_regional_issuance_mortgage_stub(*, family_code: str, file_path: str) -> dict[str, object]:
    """Заглушка парсера региональных выдач по ипотеке."""
    return _stub_payload(family_code=family_code, file_path=file_path, parser_key="regional_issuance_mortgage_stub")


def parse_regional_portfolios_mortgage_stub(*, family_code: str, file_path: str) -> dict[str, object]:
    """Заглушка парсера региональных портфелей по ипотеке."""
    return _stub_payload(family_code=family_code, file_path=file_path, parser_key="regional_portfolios_mortgage_stub")


def parse_regional_issuance_cards_stub(*, family_code: str, file_path: str) -> dict[str, object]:
    """Заглушка парсера региональных выдач по кредитным картам."""
    return _stub_payload(family_code=family_code, file_path=file_path, parser_key="regional_issuance_cards_stub")
