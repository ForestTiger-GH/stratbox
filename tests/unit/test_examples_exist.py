"""Maintained runnable examples follow the final public owners."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def test_examples_exist():
    for name in ('source_route.py','capability_session.py','universal_storage_flow.py','cbr_sors_restoration.py'):
        assert (ROOT/'examples'/name).is_file()
