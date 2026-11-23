"""Shared source templates preserve source-specific bindings and port contracts."""
from copy import deepcopy
import json

import pytest

from stratbox.domains.registry import declarations as sources
from stratbox.operations import operation_catalog


def _processing(owner, source_id):
    return next(item['processing'] for item in sources.source_documents(owner)
                if item['series_id'] == source_id)


@pytest.mark.parametrize('source_id,template_id', [
    ('frg.regional.issuance', 'frg.report'),
    ('minfin.fedbud.annex3.monthly', 'minfin.fiscal'),
    ('fns.sme', 'fns.sme'),
])
def test_source_slots_resolve_exactly_to_qualified_operations(source_id, template_id):
    route = sources.source_route(source_id)
    assert route.template_id == template_id
    assert tuple(binding for _, binding in route.slots) == route.operations
    for name, binding in route.slots:
        assert route.slot(name) == binding


def test_shared_templates_preserve_independent_profiles():
    regional = sources.source_route('frg.regional.issuance')
    special = sources.source_route('frg.special.mortgage_refinancing')
    assert regional.template_id == special.template_id
    assert regional.operations == special.operations
    assert regional.profiles != special.profiles


def test_template_and_source_copies_are_isolated():
    value = sources.template_document('frank_rg', 'frg.report')
    value['slots'].clear()
    assert sources.template_document('frank_rg', 'frg.report')['slots']


@pytest.mark.parametrize('change', [
    lambda value: value.update(template='missing.template'),
    lambda value: value['bindings'].update(unknown_slot={'operation_id': 'frg.capture'}),
    lambda value: value.update(unknown='data'),
])
def test_invalid_specializations_fail_before_execution(change):
    value = _processing('frank_rg', 'frg.regional.issuance')
    change(value)
    with pytest.raises(ValueError):
        sources.source_processing(value, owner='frank_rg', source_id='frg.regional.issuance')


def test_incompatible_operation_substitution_is_rejected():
    value = _processing('fns', 'fns.sme')
    value['bindings']['fns_sme_extract'] = {'operation_id': 'workbook.extract'}
    with pytest.raises(ValueError, match='registry.source_slot_contract_mismatch'):
        sources.source_processing(value, owner='fns', source_id='fns.sme')


def test_templates_are_owned_by_their_publisher():
    with pytest.raises(ValueError, match='registry.template_unknown'):
        sources.template_document('minfin', 'frg.report')


def test_all_sources_have_complete_template_projection_without_duplicate_routes():
    catalog = operation_catalog().source_catalog()
    assert len(catalog.sources) == 90
    assert len({catalog.template(item.series_id)['template_id'] for item in catalog.sources}) == 19
    for item in catalog.sources:
        assert dict(catalog.slots(item.series_id))
        assert all(binding.operation_id in {op.operation_id for op in item.operations}
                   for _, binding in catalog.slots(item.series_id))


def test_derived_contracts_are_resolved_from_the_canonical_output():
    document = next(item for item in sources.source_documents('fns') if item['series_id'] == 'fns.sme')
    group = document['source_groups'][0]
    assert group['outputs']
    actual = sources.decode_source_group(group)
    catalog = operation_catalog()
    for output in group['outputs']:
        definition = catalog.metadata(output['operation_id'])
        port = next(port for port in definition.processing.outputs if port.name == output['port'])
        assert port.contract in actual.contracts
    broken = deepcopy(group)
    broken['outputs'][0]['port'] = 'missing'
    with pytest.raises(ValueError, match='registry.source_group_output_unavailable'):
        sources.decode_source_group(broken)
