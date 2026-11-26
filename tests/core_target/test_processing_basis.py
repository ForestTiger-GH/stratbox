"""Stable semantic work identity preserves qualifications and input roles."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from stratbox.capabilities.catalog.domains import DomainCatalog
from stratbox.sdk import StrategyBox
from stratbox.shared.data.materials import StagedMaterialRef
from stratbox.shared.data.processing import processing_input_identity, processing_basis
from stratbox.shared.data.source_context import SourceCoordinate, SourceUse
from stratbox.shared.data.values import Material, FetchEvidence, IdentifiedMaterial, SourceClaim, SourceDataset, fingerprint


def material(observation='first'):
    value = Material(b'same content', source_id='source', metadata={'filename': 'data.xlsx', 'member': 'part/data.xlsx'})
    use = SourceUse(SourceCoordinate('source', issue_id='2026-01-01', material_identity=value.identity),
                    'material', 'verified', observation)
    evidence = FetchEvidence('request', datetime(2026, 1, 1, tzinfo=timezone.utc), 200,
        value.identity, {'etag': observation}, observation_id=observation, representation_identity='representation')
    return replace(value, source_uses=(use,), lineage=(evidence,))


def test_poll_occurrence_and_stage_ownership_do_not_change_content_work():
    first, later = material(), material('later')
    assert fingerprint(first) != fingerprint(later)
    assert processing_input_identity(first) == processing_input_identity(later)
    stage = StagedMaterialRef('token', 'temp', 'session', first.identity, source_id=first.source_id,
                              metadata=first.metadata, source_uses=first.source_uses)
    assert processing_input_identity(stage) == processing_input_identity(first)
    for changed in (replace(later, metadata={'filename': 'other.xlsx', 'member': 'part/data.xlsx'}),
                    replace(later, source_uses=(replace(later.source_uses[0], qualification='asserted'),)),
                    replace(later, source_uses=(replace(later.source_uses[0], coordinate=replace(
                        later.source_uses[0].coordinate, issue_id='2026-02-01')),))):
        assert processing_input_identity(changed) != processing_input_identity(first)


def test_dataset_work_uses_rows_semantics_and_qualifications_without_native_cache():
    source = material()
    original = SourceDataset('source', ({'metric': 'm', 'value': 1},), {'unit': 'RUB'}, '2026-01-01',
                             source.lineage, native=object(), source_uses=source.source_uses)
    later = replace(original, native=object(), lineage=material('later').lineage,
                    source_uses=material('later').source_uses)
    assert processing_input_identity(original) == processing_input_identity(later)
    assert processing_input_identity(original) != processing_input_identity(replace(later, semantics={'unit': 'USD'}))
    assert processing_input_identity(original) != processing_input_identity(replace(later, rows=({'metric': 'm', 'value': 2},)))


def test_compact_carrier_replay_preserves_the_same_qualified_material_basis():
    original = material()
    claim = SourceClaim('source', '2026-01-01', 'main', 'verified')
    full = replace(original, source_uses=(), metadata={**original.metadata, 'url': 'https://example.test/data.xlsx',
        'role': 'asset', 'discovery': 'explicit_locator'})
    first = IdentifiedMaterial(full, claim, source_uses=original.source_uses)
    restored = IdentifiedMaterial(original, claim, source_uses=original.source_uses)
    assert processing_input_identity(first) == processing_input_identity(restored)


def test_work_basis_keeps_input_port_roles_parameters_and_build():
    def basis(inputs, **changes):
        return processing_basis(inputs, capability_id='command.calculate.ratio', method='method:run',
            settings={}, parameters=changes.get('parameters', {}), build_identity=changes.get('build', 'build'))
    first = basis({'numerator': 2, 'denominator': 4})
    assert first != basis({'numerator': 4, 'denominator': 2})
    assert first != basis({'numerator': 2, 'denominator': 4}, parameters={'label': 'chosen'})
    assert first != basis({'numerator': 2, 'denominator': 4}, build='new-build')


def test_frame_object_cells_contribute_their_nested_content_to_the_work_key():
    import pandas as pd
    first = pd.DataFrame({'data': pd.Series([[{'value': 7}]], dtype=object)})
    same = pd.DataFrame({'data': pd.Series([[{'value': 7}]], dtype=object)})
    changed = pd.DataFrame({'data': pd.Series([[{'value': 8}]], dtype=object)})
    assert processing_input_identity(first) == processing_input_identity(same)
    assert processing_input_identity(first) != processing_input_identity(changed)
    assert processing_input_identity(first) != processing_input_identity(first.rename(columns={'data': 'other'}))


def test_sdk_basis_prepares_a_direct_command_without_starting_a_session():
    with StrategyBox(domains=DomainCatalog({}), build_identity='known-build') as box:
        value = SourceDataset('source', ({'metric': 'm', 'value': 1},))
        desired = box.processing_basis('command.observations.validate', inputs={'dataset': value})
        assert len(desired) == 3 and desired[-1] == 'known-build' and box._session is None
        with pytest.raises(ValueError, match='direct_command_required'):
            box.processing_basis('operation.dataset.retain', inputs={'dataset': value, 'destination': 'out'})
