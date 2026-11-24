"""Real typed material and retained observations survive exact plan encoding."""
import json
import pytest

from stratbox.composition import ExecutionPlan,validate_plan
from stratbox.composition.codec import decode
from stratbox.sdk import StrategyBox


def test_real_workbook_plan_and_retained_extract_roundtrip(profiled_catalog,two_tables):
    with StrategyBox(capabilities=profiled_catalog) as box:
        plan = box.prepare("extract.observations",inputs={"material":two_tables},profile_id="fixture.debt")
        restored = ExecutionPlan.from_dict(json.loads(json.dumps(plan.to_dict())))
        assert restored == plan
        assert validate_plan(restored,box.operations) is restored
        extracted = box.submit(restored).result(10)
        assert extracted.outcome == "succeeded",extracted.diagnostics
        observations = extracted.output("observations")
        assert [row.value for row in observations.observations] == [10,20]
        view = box.prepare("view.table",inputs={"observations":observations})
        replayed = ExecutionPlan.from_dict(json.loads(json.dumps(view.to_dict())))
        assert replayed == view
        result = box.submit(replayed).result(10)
        assert result.outcome == "succeeded",result.diagnostics
        assert result.output("view").batch == observations
        assert result.output("view").batch.lineage == observations.lineage
        result.close()
        extracted.close()


def test_material_digest_is_recomputed_during_plan_decode(profiled_catalog,two_tables):
    with StrategyBox(capabilities=profiled_catalog) as box:
        encoded = box.prepare("convert.readable",inputs={"material":two_tables}).to_dict()
    def corrupt(value):
        if isinstance(value,dict):
            if value.get("$type") == "SourcePayload":
                value["fields"]["data"] = {"$type":"bytes","value":""}
                return True
            return any(corrupt(child) for child in value.values())
        if isinstance(value,list):
            return any(corrupt(child) for child in value)
        return False
    assert corrupt(encoded)
    with pytest.raises(ValueError,match="composition.value_identity_mismatch"):
        ExecutionPlan.from_dict(encoded)


def test_type_descriptors_cannot_import_code():
    with pytest.raises(ValueError,match="composition.unknown_type"):
        decode({"$type":"python_type","value":"os:system"})
