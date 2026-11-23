"""A delivered package must retain the exact admitted implementation bytes."""
from pathlib import Path
import runpy

import pytest


def fixture():
    root = Path(__file__).resolve().parents[3]
    module = runpy.run_path(str(root / "scripts/inspect_reference_wheel.py"))
    inventory = module["_source_code_inventory"]()
    members = {name: (root / "src" / name).read_bytes() for name in inventory}
    return module["_verify_code_members"], members


def test_every_code_file_and_type_marker_has_one_delivery_identity():
    verify, members = fixture()
    result = verify(set(members), "", members.__getitem__)
    assert result["files"] == len(members)
    prefix = "stratbox-example/src/"
    source_members = {prefix + name: value for name, value in members.items()}
    assert verify(set(source_members), prefix, source_members.__getitem__) == result


@pytest.mark.parametrize("mutation", ["missing", "changed", "extra", "bytecode"])
def test_modified_implementation_or_undeclared_executable_is_rejected(mutation):
    verify, members = fixture()
    name = "stratbox/core/execution/runner.py"
    if mutation == "missing":
        del members[name]
    elif mutation == "changed":
        members[name] += b"\n# Changed distribution content\n"
    elif mutation == "extra":
        members["stratbox/undeclared.py"] = b"pass\n"
    else:
        members["stratbox/__pycache__/undeclared.pyc"] = b"executable bytecode"
    with pytest.raises(ValueError, match="Implementation distribution mismatch"):
        verify(set(members), "", members.__getitem__)
