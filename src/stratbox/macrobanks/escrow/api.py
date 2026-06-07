"""api — совместимый фасад на канонические operations домена escrow."""

from stratbox.macrobanks.escrow.contracts import EscrowExportResult as EscrowRunResult
from stratbox.macrobanks.escrow.operations import run_escrow_export as run_escrow_to_xlsx

__all__ = ["EscrowRunResult", "run_escrow_to_xlsx"]
