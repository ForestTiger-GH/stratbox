"""Actual relational origin and coordinate coverage govern semantic admission."""
from dataclasses import dataclass, replace
from types import SimpleNamespace
import pytest

from stratbox.capabilities.model import PortContract, SourceRequirement, AcceptanceContract, SemanticPredicate
from stratbox.capabilities.model.immutable import freeze, fingerprint
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.data.values import SourceDataset, Assessment, Material, JsonEvidence
from stratbox.shared.data.source_context import SourceUse, SourceCoordinate
from stratbox.shared.data.assessment import CoverageCoordinate, CoverageAssessment


def use(source='A', group='main', *, role='operand', qualification='domain_validated', evidence=True):
    return SourceUse(SourceCoordinate(source, 'family', group, '2026-11-01',
        material_identity=ByteIdentity.of(source.encode()) if evidence else None,
        layout_identity='table-layout', semantic_identity='meaning'), role, qualification)


def dataset(*uses):
    return SourceDataset('A', (), source_uses=uses)


def test_source_label_and_lineage_cannot_replace_qualified_uses():
    requirement=SourceRequirement(frozenset({'A'}))
    for value in (dataset(), SourceDataset('A', (), lineage=('source:A',)), dataset(use('B'))):
        with pytest.raises(ValueError, match='qualified_use'):
            requirement.validate(value)
    assert requirement.validate(dataset(use()))


def test_relational_requirement_cannot_cross_join_sources_and_groups():
    requirement=SourceRequirement(frozenset({'A'}), source_group_ids=frozenset({'main'}), input_role='operand')
    with pytest.raises(ValueError, match='qualified_use'):
        requirement.validate(dataset(use('A', 'other'), use('B', 'main')))
    assert requirement.validate(dataset(use('A', 'main')))
    with pytest.raises(ValueError, match='qualified_use'):
        requirement.validate(dataset(use(role='reference')))


def test_evidence_and_explicit_attribution_are_independent_requirements():
    with pytest.raises(ValueError, match='qualified_use'):
        SourceRequirement(frozenset({'A'})).validate(dataset(use(evidence=False)))
    with pytest.raises(ValueError, match='qualified_use'):
        SourceRequirement(frozenset({'A'})).validate(dataset(use(qualification='declared')))
    requirement=SourceRequirement(frozenset({'A'}), attribution='asserted',
        qualifications=frozenset({'declared'}), require_evidence=False)
    supplied=dataset(use(qualification='declared', evidence=False))
    assert requirement.validate(supplied) is supplied
    assert supplied.source_uses[0].qualification=='declared'


def test_exact_source_pins_and_closed_origin_policy_are_checked():
    actual=use()
    requirement=SourceRequirement(frozenset({'A'}), '2026-11-01', input_role='operand',
        material_identity=actual.coordinate.material_identity, layout_identity='table-layout',
        semantic_identity='meaning', allow_additional_sources=False)
    assert requirement.validate(dataset(actual))
    for coordinate in (replace(actual.coordinate, material_identity=ByteIdentity.of(b'other')),
                       replace(actual.coordinate, semantic_identity='other'),
                       replace(actual.coordinate, issue_id='2026-10-01')):
        with pytest.raises(ValueError, match='qualified_use'):
            requirement.validate(dataset(replace(actual, coordinate=coordinate)))
    with pytest.raises(ValueError, match='undeclared_use'):
        requirement.validate(dataset(actual, use('B')))


def coordinate(subject, metric):
    return CoverageCoordinate('country', subject, metric, 'as_of', '2026-11-01', 'whole')


def coverage(*members, expected=None):
    return CoverageAssessment('table', tuple(c.identity for c in members), True,
        ('subject:A', 'subject:B', 'metric:x', 'metric:y'),
        ('subject:A', 'subject:B', 'metric:x', 'metric:y'), expected_coordinates=expected)


def test_axis_marginals_and_declared_complete_string_do_not_prove_joint_coverage():
    pair=(coordinate('A','x'),coordinate('B','y'))
    marginals=coverage(*pair)
    assert marginals.axis_status=='complete' and marginals.status=='unknown'
    contract=PortContract('dataset', SourceDataset, expected_coverage=frozenset({'coverage.complete'}))
    for assessment in (Assessment(observed=('coverage.complete',)), Assessment(coverage=marginals)):
        with pytest.raises(ValueError, match='coverage_missing'):
            contract.validate(replace(dataset(use()), assessment=assessment))
    expected=tuple(coordinate(s,m) for s in ('A','B') for m in ('x','y'))
    with pytest.raises(ValueError, match='coverage_missing'):
        contract.validate(replace(dataset(use()), assessment=Assessment(coverage=coverage(*pair,expected=expected))))
    complete=replace(dataset(use()), assessment=Assessment(coverage=coverage(*expected,expected=expected)))
    assert contract.validate(complete) is complete


def test_coverage_assessment_and_exact_requested_coordinates_are_required():
    point=coordinate('A','x')
    contract=PortContract('dataset', object, expected_coordinates=(point,))
    with pytest.raises(ValueError, match='assessment_required'):
        contract.validate(object())
    with pytest.raises(ValueError, match='coordinate_coverage_missing'):
        contract.validate(SimpleNamespace(assessment=Assessment()))
    qualified=SimpleNamespace(assessment=Assessment(coverage=coverage(point)))
    assert contract.validate(qualified) is qualified
    with pytest.raises(ValueError, match='assessment_required'):
        PortContract('v',object, qualifications=frozenset({'reviewed'})).validate(object())


def test_typed_runtime_maps_and_competent_scientific_carriers_freeze_exactly():
    physical=JsonEvidence(Material(b'{}'), {}, tokens={('rows',0):'0.10'})
    frozen=freeze({'physical':physical})
    assert frozen['physical'].tokens[('rows',0)]=='0.10'
    assert fingerprint(frozen)==fingerprint(freeze(frozen))
    with pytest.raises(TypeError, match='string_keys'):
        freeze({('bad','metadata'):'x'})
    @dataclass(frozen=True)
    class ScientificState:
        native: object
        fingerprint: str = 'competent-exact-content'
    state=ScientificState(object())
    assert freeze(state) is state
    assert fingerprint(state)


def test_output_acceptance_settles_independent_outputs_and_coherent_groups():
    contract=AcceptanceContract(predicates=(SemanticPredicate('bad','minimum',0,'negative'),))
    errors,pending=contract.assess_outputs({'good':3,'bad':-1},names=('good','bad'),settled=('good','bad'))
    assert errors=={'bad':('negative',)} and not pending
    coherent=replace(contract, coherent_outputs=('good','bad'))
    errors,pending=coherent.assess_outputs({'good':3},names=('good','bad'),settled=('good',))
    assert pending==frozenset({'good','bad'}) and not errors
    errors,pending=coherent.assess_outputs({'good':3,'bad':-1},names=('good','bad'),settled=('good','bad'))
    assert set(errors)=={'good','bad'} and not pending


def test_runtime_payload_maps_keep_typed_keys_while_authored_controls_remain_finite():
    from stratbox.sdk import StrategyBox
    from stratbox.capabilities.model import CommandDefinition, MethodRef
    supplied={1:'numeric key','1':'text key'}
    with StrategyBox() as box:
        encoded=box.invoke('command.value.encode',inputs={'value':supplied})
        assert encoded.outcome=='succeeded',encoded.diagnostics
        restored=box.invoke('command.value.decode',inputs={'representation':encoded.output('representation')})
        assert restored.outcome=='succeeded',restored.diagnostics
        assert restored.output('value')==supplied
    metadata=CommandDefinition('command.test.control',method=MethodRef('operator:neg'),
        parameters={'limit':float('inf')})
    with pytest.raises(ValueError,match='nonfinite'):
        fingerprint(metadata)
