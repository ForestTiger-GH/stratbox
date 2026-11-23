"""The public facade preserves catalog, execution and provider semantics."""
import subprocess
import sys
import os
from pathlib import Path

import pytest


def test_sdk_discovery_stays_lightweight():
    code = """
import sys
from stratbox.sdk import StrategyBox
with StrategyBox() as box:
    assert len(box.operations.list_refs()) >= 353
    assert len(box.sources.select()) == 90
    assert box._session is None
assert not ({'pandas', 'numpy', 'openpyxl', 'requests', 'PySide6'} & set(sys.modules))
"""
    import stratbox
    env = {**os.environ, "PYTHONPATH": str(Path(stratbox.__file__).parent.parent)}
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
    assert result.returncode == 0, result.stderr


def test_invoke_and_submitted_plan_share_typed_result(tmp_path):
    from stratbox.sdk import StrategyBox, OperationStep, ScenarioDefinition, PlanOutputRef
    from stratbox.core.storage.filestore import LocalFileStore
    (tmp_path / "original.csv").write_bytes(b"period,value\n2026-01,12\n")
    parameters = {"locator": "original.csv", "media_type": "text/csv"}
    store = LocalFileStore(str(tmp_path))
    with StrategyBox(providers={"filestore": store}) as box:
        metadata = box.operations.get("material.read_location")
        port = metadata.processing.outputs[0].name
        workflow = ScenarioDefinition("read", (
            OperationStep("read", "material.read_location", parameters=parameters),
        ), outputs={"original": PlanOutputRef("read", port)})
        immediate = box.invoke("material.read_location", parameters=parameters)
        submitted = box.submit(box.compile(workflow)).result(timeout=10)
        assert immediate.outcome == submitted.outcome == "succeeded"
        assert immediate.output(port) == submitted.output("original")
        assert box.session is box.session
    with pytest.raises(RuntimeError, match="sdk.closed"):
        box.submit(workflow)


def test_sdk_rejects_conflicting_provider_ownership():
    from stratbox.sdk import StrategyBox
    from stratbox.core.execution import ExecutionContext
    from stratbox.core.runtime import ProviderBinding, CapabilityRequirement
    binding = ProviderBinding("files", CapabilityRequirement("filestore"), "ready", object())
    with pytest.raises(ValueError, match="sdk.provider_conflict"):
        StrategyBox(context=ExecutionContext(bindings=(binding,)),
                    providers={"filestore": object()})
