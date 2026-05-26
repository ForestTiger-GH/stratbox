"""
Заглушки парсеров для блока экспресс-мониторинга FRG.
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



def parse_express_issuance_stub(*, family_code: str, file_path: str) -> dict[str, object]:
    """Заглушка парсера месячных выдач."""
    return _stub_payload(family_code=family_code, file_path=file_path, parser_key="express_issuance_stub")



def parse_express_portfolios_stub(*, family_code: str, file_path: str) -> dict[str, object]:
    """Заглушка парсера месячных портфелей."""
    return _stub_payload(family_code=family_code, file_path=file_path, parser_key="express_portfolios_stub")



def parse_express_passives_stub(*, family_code: str, file_path: str) -> dict[str, object]:
    """Заглушка парсера пассивов."""
    return _stub_payload(family_code=family_code, file_path=file_path, parser_key="express_passives_stub")



def parse_express_issuance_weekly_stub(*, family_code: str, file_path: str) -> dict[str, object]:
    """Заглушка парсера недельных выдач внутри месяца."""
    return _stub_payload(family_code=family_code, file_path=file_path, parser_key="express_issuance_weekly_stub")



def parse_express_issuance_cards_stub(*, family_code: str, file_path: str) -> dict[str, object]:
    """Заглушка парсера выдач по кредитным картам."""
    return _stub_payload(family_code=family_code, file_path=file_path, parser_key="express_issuance_cards_stub")


# Алиасы сохранены для мягкой совместимости внутреннего слоя.
parse_weekly_express_issuance_stub = parse_express_issuance_weekly_stub
parse_cards_express_issuance_stub = parse_express_issuance_cards_stub
