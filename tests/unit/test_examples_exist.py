from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_examples_exist() -> None:
    expected = [
        'examples/cbr_file_collector_example.py',
        'examples/cbr_industries_0105a_debt_corp_example.py',
        'examples/cbr_sors_restoration_colab.py',
        'examples/cbr_sors_restoration_crosswalk.py',
        'examples/escrow_example.py',
        'examples/frg_cleanup_example.py',
        'examples/frg_scan_example.py',
        'examples/universal_storage_flow.py',
    ]
    for rel in expected:
        assert (ROOT / rel).is_file(), rel
