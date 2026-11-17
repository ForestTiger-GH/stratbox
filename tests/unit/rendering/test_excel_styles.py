"""Optional Excel engine boundaries and real workbook styling."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import openpyxl
import pytest

from stratbox.core.rendering.excel import (
    BUILTIN_STYLES, BlockStyle, ExcelStylesRegistry, StyleSpec, apply_preset,
    get_default_preset_name, list_available_presets, resolve_preset_name,
)
from stratbox.core.rendering.excel.api import active_styles


def test_base_imports_and_excel_metadata_without_optional_packages():
    root = Path(__file__).resolve().parents[3] / "src"
    script = """
import importlib
import sys
sys.path.insert(0, sys.argv[1])
for name in (
    "stratbox", "stratbox.core", "stratbox.core.runtime",
    "stratbox.core.storage", "stratbox.core.network",
    "stratbox.core.formats", "stratbox.core.execution",
    "stratbox.core.observability", "stratbox.core.notifications",
    "stratbox.core.rendering.excel", "stratbox.shared", "stratbox.domains",
):
    importlib.import_module(name)
from stratbox.core.rendering.excel import BUILTIN_STYLES, list_available_presets, apply_preset
from stratbox.core.runtime.dependencies import MissingExtra
assert list_available_presets(registry=BUILTIN_STYLES)
try:
    apply_preset(object(), "DEFAULT", registry=BUILTIN_STYLES)
except MissingExtra as exc:
    assert exc.extra == "excel"
else:
    raise AssertionError("Expected missing optional dependency")
"""
    subprocess.run([sys.executable, "-I", "-S", "-c", script, str(root)],
                   check=True, capture_output=True, text=True)


def test_excel_preset_applies_styles_without_changing_cell_values():
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.append(("Name", "Amount", "Formula"))
    sheet.append(("Example", 1234.5, "=1+2"))
    before = [tuple(cell.value for cell in row) for row in sheet]
    apply_preset(sheet, "DEFAULT", registry=BUILTIN_STYLES)
    assert [tuple(cell.value for cell in row) for row in sheet] == before
    assert sheet.sheet_view.showGridLines is False
    assert sheet.freeze_panes == "C2"
    assert sheet["A1"].font.bold is True
    assert sheet["A1"].fill.patternType == "solid"
    assert sheet["B2"].number_format == "#,##0"
    assert sheet["C2"].number_format == "#,##0"


def test_custom_registry_and_explicit_freeze_panes():
    custom = ExcelStylesRegistry(
        {"plain": StyleSpec(freeze_rows=2, freeze_cols=0,
                            values_block=BlockStyle(bold=True))},
        "plain",
    )
    assert get_default_preset_name(registry=custom) == "PLAIN"
    assert list_available_presets(registry=custom) == ["PLAIN"]
    assert resolve_preset_name(" default ", registry=custom) == "PLAIN"
    sheet = openpyxl.Workbook().active
    sheet["A1"] = "Value"
    apply_preset(sheet, "plain", freeze_panes="D4", registry=custom)
    assert sheet.freeze_panes == "D4"
    assert sheet["A1"].font.bold is True


def test_invalid_presets_and_registry():
    with pytest.raises(ValueError, match="Unknown Excel style preset"):
        apply_preset(openpyxl.Workbook().active, "missing", registry=BUILTIN_STYLES)
    with pytest.raises(TypeError, match="Expected ExcelStylesRegistry"):
        active_styles(registry=object())
