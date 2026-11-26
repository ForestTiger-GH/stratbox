"""Completed byte ownership survives sharing, close and bounded failures."""
from dataclasses import replace
from threading import Event

import pytest

from stratbox.capabilities.model import MethodRef, PortContract, ReuseContract
from stratbox.capabilities.plan.models import BoundCommand, CommandTask, PreparedPlan, ValueRef
from stratbox.core.execution.service import ExecutionService, ExecutionSettings
from stratbox.core.limits import ExecutionBudget
from stratbox.shared.data.materials import StagedMaterialRef
from stratbox.shared.data.values import canonical_tree, validate_portable_tree, restore_tree

ENTERED, RELEASE = Event(), Event()


def create(inputs, settings, context):
    with context.stage(metadata={"nested": {"items": [1, 2]}}) as stage:
        for _ in range(settings.get("chunks", 1)):
            stage.write(b"x" * settings.get("size", 1024))
        result = stage.seal()
    return {"value": result}


def consume(inputs, settings, context):
    ENTERED.set()
    assert RELEASE.wait(3)
    with context.open_material(inputs["value"]) as stream:
        return {"value": len(stream.read(2048))}


def build(method, value=None, *, settings=None, reuse=False):
    command = BoundCommand("command.test.stage_" + method,
        MethodRef(__name__ + ":" + method), settings or {},
        {} if value is None else {"value": PortContract("staged", StagedMaterialRef)},
        {"value": PortContract("staged", StagedMaterialRef) if method == "create" else PortContract("number", int)},
        resources={"cpu": 1}, reuse=ReuseContract(shareable=reuse, completed=reuse))
    return PreparedPlan("staged.test", (CommandTask("work", command, {} if value is None else {"value": value}),),
                        (), {"value": ValueRef("work")}, "staged.test", "test")


def test_result_owns_completed_file_after_service_close_and_expires_on_close():
    service = ExecutionService()
    result = service.run(build("create"))
    reference = result.output()
    assert result.outcome == "succeeded"
    assert service.staging.status()["live_bytes"] == 1024
    service.close()
    with service.staging.open(reference) as stream:
        assert stream.read(4) == b"xxxx"
    result.close()
    assert service.staging.status()["objects"] == 0
    assert not service.staging.directory.exists()
    with pytest.raises(ValueError, match="expired"):
        with service.staging.open(reference):
            pass


def test_admitted_consumer_survives_closed_producer():
    ENTERED.clear()
    RELEASE.clear()
    with ExecutionService() as service:
        producer = service.run(build("create"))
        handle = service.submit(build("consume", producer.output()))
        producer.close()
        assert ENTERED.wait(2)
        RELEASE.set()
        with handle.result(3) as result:
            assert result.output() == 1024
        assert service.staging.status()["objects"] == 0


def test_stage_output_budget_uses_bytes_and_cleans_failed_acceptance():
    settings = ExecutionSettings(run_limits=ExecutionBudget(output_bytes=4000))
    with ExecutionService(settings=settings) as service:
        with service.run(build("create", settings={"size": 8192})) as result:
            assert result.outcome == "failed"
            assert "budget.output_bytes" in result.diagnostics
        assert service.staging.status()["objects"] == 0


def test_live_quota_fails_without_waiting_for_dependent_release():
    with ExecutionService(settings=ExecutionSettings(max_staged_bytes=1500)) as service:
        first = service.run(build("create"))
        with service.run(build("create")) as second:
            assert second.outcome == "failed"
            assert "stage.byte_limit" in second.diagnostics
        assert service.staging.status()["live_bytes"] == 1024
        first.close()
        with service.run(build("create")) as third:
            assert third.outcome == "succeeded"


def test_no_completed_cache_leases_and_nested_codec_rejection():
    with ExecutionService() as service:
        first = service.run(build("create", reuse=True))
        reference = first.output()
        assert not service._completed
        with pytest.raises(TypeError):
            reference.metadata["nested"]["items"][0] = 9
        tree = canonical_tree({"nested": (reference,)})
        for fn in (validate_portable_tree, restore_tree):
            with pytest.raises(ValueError, match="session_local"):
                fn(tree)
            with pytest.raises(ValueError, match="session_local"):
                fn(tree, admitted_types={"stratbox.shared.data.materials:StagedMaterialRef": StagedMaterialRef})
        first.close()
        with pytest.raises(ValueError, match="expired"):
            service.submit(build("consume", reference))


def test_forged_and_cross_session_descriptors_reject_before_work():
    with ExecutionService() as first, ExecutionService() as second:
        with first.run(build("create")) as result:
            reference = result.output()
            with pytest.raises(ValueError, match="foreign_session"):
                second.submit(build("consume", reference))
            forged = replace(reference, metadata={"changed": True})
            with pytest.raises(ValueError, match="descriptor_mismatch"):
                first.submit(build("consume", forged))
def test_abandoned_cleanup_preserves_active_results_and_unmarked_directories(tmp_path):
    import subprocess
    import sys
    from stratbox.core.storage.staging_ownership import cleanup_abandoned_staging
    from stratbox.core.storage.staged_values import StagedValueStore
    other = tmp_path/'stratbox-stage-caller'
    other.mkdir()
    (other/'important').write_text('caller data')
    active = StagedValueStore(directory=tmp_path)
    with active.builder('held') as writer:
        writer.write(b'held')
        reference = writer.seal()
    code = ('from stratbox.core.storage.staged_values import StagedValueStore; '
            'import sys; s=StagedValueStore(directory=sys.argv[1]); '
            'w=s.builder("orphan"); w.write(b"orphan"); w.seal(); print(s.directory)')
    orphan = subprocess.check_output([sys.executable,'-c',code,str(tmp_path)],text=True).strip()
    result = cleanup_abandoned_staging(tmp_path)
    assert result['removed'] == 1 and result['busy'] == 1
    from pathlib import Path
    assert not Path(orphan).exists()
    assert (other/'important').read_text() == 'caller data'
    with active.open(reference) as stream:
        assert stream.read() == b'held'
    active.release('held')
    active.close()
