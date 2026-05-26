"""
Домен обработки данных ЦБ РФ по финансированию долевого строительства (счета эскроу).

Публичный вход:
- run_escrow_to_xlsx
"""

from stratbox.macrobanks.escrow.api import run_escrow_to_xlsx

__all__ = ["run_escrow_to_xlsx"]
