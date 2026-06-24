from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_examples_exist() -> None:
    expected = [
        'examples/cbr_file_collector_example.py',
        'examples/escrow_example.py',
        'examples/frg_cleanup_example.py',
        'examples/frg_stage1_example.py',
    ]
    for rel in expected:
        assert (ROOT / rel).is_file(), rel
