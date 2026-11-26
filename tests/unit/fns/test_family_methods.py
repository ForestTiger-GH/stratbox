"""Compatible table families supply direct methods without dispatch-table edits."""
from dataclasses import replace
from types import SimpleNamespace
import pytest

from stratbox.capabilities.model.domains import CommandSpec, DomainSpec, SeriesSpec
from stratbox.capabilities.model.methods import MethodRef
from stratbox.domains.fns.common.semantics import SME_RULES
from stratbox.domains.fns.series.sme import SME
from stratbox.shared.data.values import JsonEvidence, Material


def test_explicit_future_family_reuses_a_command_method_without_a_builder():
    rules = replace(SME_RULES, source_id="fns.fixture")
    specification = CommandSpec(MethodRef("stratbox.domains.fns.methods.sme:select_records"), rules)
    series = SeriesSpec("fns.fixture", SME.publication, SME.semantics,
        {"command.table.extract": specification})
    domain = DomainSpec("fns", {}, {series.id: series})
    context = SimpleNamespace(parameters={}, checkpoint=lambda: None)
    physical = JsonEvidence(Material(b'[{}]', source_id="fns.fixture"), ({},))
    result = domain.series["fns.fixture"].commands["command.table.extract"].method.resolve()(
        {"physical": physical}, rules, context)
    assert result["tables"].source_id == "fns.fixture"
    assert result["tables"].tables == ({},)
    with pytest.raises(ValueError, match="source_mismatch"):
        specification.method.resolve()({"physical": replace(physical,
            material=Material(b'[{}]', source_id="fns.other"))}, rules, context)
