"""
Заглушки парсеров для специальных семейств FRG.
"""

from __future__ import annotations


def parse_mortgage_refinancing_stub(*, family_code: str, file_path: str) -> dict[str, object]:
    """Заглушка парсера файла по рефинансированию ипотеки."""
    return {
        "family_code": family_code,
        "path": file_path,
        "parser_key": "mortgage_refinancing_stub",
        "status": "stub",
        "message": "Parser stub executed. Real parsing is not implemented yet.",
    }
