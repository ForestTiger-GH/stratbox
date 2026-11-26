"""Explicit unsuccessful outputs remain reports, with no execution authority."""
from dataclasses import replace
from threading import Event
from time import monotonic, sleep

import pytest

from stratbox.capabilities.catalog import Catalog
from stratbox.capabilities.catalog.domains import DomainCatalog
from stratbox.capabilities.model import (
    AcceptanceContract, Call, CommandDefinition, GraphBody, MethodRef,
    OperationDefinition, OutputRef, PortContract, ReuseContract, SemanticPredicate,
)
from stratbox.core.execution.service import CommandCompletion
from stratbox.core.observability.projections.source_state import SourceStateIndex
from stratbox.core.storage.source_state import MemorySourceState
from stratbox.sdk import StrategyBox
from stratbox.shared.data.history import make_validation_certificate
from stratbox.shared.data.values import SourceDataset, fingerprint


TERMINAL = frozenset({'succeeded', 'partial', 'failed', 'unknown', 'cancelled'})
REPORT = PortContract('diagnostic_report', tuple, outcomes=TERMINAL)
ENTERED, RELEASE = Event(), Event()
CALLS = []


@pytest.fixture(autouse=True)
def clear_gates():
    ENTERED.clear(); RELEASE.clear(); CALLS.clear()
    yield
    RELEASE.set()


def complete(inputs, settings, context):
    CALLS.append('complete')
    if context.parameters.get('uncertain'):
        def uncertain():
            raise OSError('unobservable physical completion')
        context.effect('storage.write', 'diagnostic-effect', uncertain, resource='fixture')
    outputs = {'normal': 41, 'report': context.parameters.get('report', ('checked',))}
    if context.parameters.get('extra'):
        outputs['undeclared'] = 7
    return CommandCompletion(outputs, context.parameters.get('outcome', 'failed'), ('fixture.work_incomplete',))


def consume(inputs, settings, context):
    CALLS.append('consume')
    return {'value': len(inputs['report'])}


def staged_after_wait(inputs, settings, context):
    CALLS.append('stage')
    with context.stage() as writer:
        writer.write(b'completed temporary bytes')
        value = writer.seal()
    ENTERED.set()
    assert RELEASE.wait(3), 'fixture.release_timeout'
    return CommandCompletion({'normal': value, 'report': ('finished physical work',)})


def failed_validation(inputs, settings, context):
    return CommandCompletion({'dataset': inputs['dataset']}, 'failed', ('fixture.validation_rejected',))


def command(*, outcome='failed', handler='complete', acceptance=None, parameters=None):
    return CommandDefinition('command.test.diagnostic',
        outputs={'normal': PortContract('value'), 'report': REPORT},
        method=MethodRef(__name__ + ':' + handler),
        parameters={'outcome': outcome, **(parameters or {})},
        effects=frozenset({'storage.write'}) if (parameters or {}).get('uncertain') else frozenset(),
        acceptance=acceptance or AcceptanceContract(),
        reuse=ReuseContract())


def client(*definitions, **kwargs):
    return StrategyBox(catalog=Catalog({value.id: value for value in definitions}),
        domains=DomainCatalog({}), build_identity='diagnostic-outputs-test', **kwargs)


@pytest.mark.parametrize('outcome', ('failed', 'unknown'))
def test_unsuccessful_reports_are_visible_and_dependencies_stay_blocked(outcome):
    work = command(outcome=outcome)
    consumer = CommandDefinition('command.test.consume', inputs={'report': REPORT},
        outputs={'value': PortContract('integer', int)}, method=MethodRef(__name__ + ':consume'))
    operation = OperationDefinition('operation.test.diagnostic',
        outputs={'report': REPORT}, body=GraphBody((
            Call('work', work.id), Call('consume', consumer.id, {'report': OutputRef('work', 'report')})),
            {'report': OutputRef('work', 'report')}, required_completions=('consume',)))
    with client(work, consumer, operation) as box:
        with box.invoke(operation.id) as result:
            assert result.outcome == outcome
            assert result.output('report') == ('checked',)
            assert result.scopes['root'] == 'failed'
            assert CALLS == ['complete']
            facts = box.session.journal.read(run_id=result.run_id)
            reports = [fact for fact in facts if fact.kind == 'output.reported']
            assert {fact.scope_id for fact in reports} == {'root/work', 'root'}
            assert all(fact.data['outcome'] == outcome for fact in reports)
            assert not any(fact.kind == 'output.accepted' for fact in facts)
            assert not box.session._accepted
            assert 'fixture.work_incomplete' in result.diagnostics


def test_success_only_scope_cannot_export_an_unsuccessful_report():
    work = command()
    operation = OperationDefinition('operation.test.success_only',
        outputs={'report': PortContract('diagnostic_report', tuple)},
        body=GraphBody((Call('work', work.id),), {'report': OutputRef('work', 'report')}))
    with client(work, operation) as box:
        with box.invoke(operation.id) as result:
            assert result.outcome == 'failed' and not result.outputs
            assert 'acceptance.output_outcome_not_admitted:failed' in result.diagnostics


@pytest.mark.parametrize('parameters,acceptance', (
    ({'report': 'wrong type'}, AcceptanceContract()),
    ({'extra': True}, AcceptanceContract()),
    ({}, AcceptanceContract(coherent_outputs=('normal', 'report'))),
    ({}, AcceptanceContract(predicates=(SemanticPredicate('report', 'equals', ('different',)),))),
))
def test_diagnostic_ports_still_require_full_port_and_acceptance_checks(parameters, acceptance):
    work = command(parameters=parameters, acceptance=acceptance)
    with client(work) as box:
        with box.invoke(work.id) as result:
            assert result.outcome == 'failed' and not result.outputs
            assert not any(fact.kind in {'output.accepted', 'output.reported'}
                for fact in box.session.journal.read(run_id=result.run_id))


def test_unknown_effect_remains_unknown_even_with_an_available_report():
    work = command(outcome='succeeded', parameters={'uncertain': True})
    with client(work) as box:
        with box.invoke(work.id) as result:
            assert result.outcome == 'unknown'
            assert result.output('report') == ('checked',)
            assert 'normal' not in result.outputs
            assert result.effects['diagnostic-effect'].status == 'unknown'
            assert not any(fact.kind == 'output.accepted'
                for fact in box.session.journal.read(run_id=result.run_id))


def test_invalid_diagnostic_never_turns_an_unknown_completion_into_a_known_failure():
    work = command(outcome='unknown', parameters={'report': 'wrong type'})
    with client(work) as box:
        with box.invoke(work.id) as result:
            assert result.outcome == 'unknown' and not result.outputs
            assert any('value_type_mismatch' in value for value in result.diagnostics)


def test_partial_completion_keeps_its_findings_with_the_declared_output():
    work = command(outcome='partial', acceptance=AcceptanceContract(partial_allowed=True))
    with client(work) as box:
        with box.invoke(work.id) as result:
            assert result.outcome == 'partial' and result.output('report') == ('checked',)
            assert 'fixture.work_incomplete' in result.diagnostics


@pytest.mark.parametrize('shared', (False, True))
def test_cancellation_keeps_only_declared_reports_and_releases_regular_stage_outputs(shared):
    work = command(outcome='succeeded', handler='staged_after_wait')
    with client(work) as box:
        first = box.submit(work.id)
        second = None
        try:
            assert ENTERED.wait(2)
            if shared:
                second = box.submit(work.id)
                until = monotonic() + 2
                while second.snapshot()['tasks']['root'] != 'waiting_shared':
                    assert monotonic() < until, 'fixture.shared_consumer_timeout'
                    sleep(.002)
            assert first.cancel()
        finally:
            RELEASE.set()
        with first.result(3) as cancelled:
            assert cancelled.outcome == 'cancelled'
            assert tuple(cancelled.outputs) == ('report',)
            assert cancelled.output('report') == ('finished physical work',)
            assert cancelled.scopes['root'] == 'failed'
            facts = box.session.journal.read(run_id=cancelled.run_id)
            reports = [fact for fact in facts if fact.kind == 'output.reported']
            assert len(reports) == 1 and reports[0].data['outcome'] == 'cancelled'
            assert not any(fact.kind == 'output.accepted' for fact in facts)
        if second is not None:
            with second.result(3) as survivor:
                assert survivor.outcome == 'succeeded'
                with box.session.staging.open(survivor.output('normal')) as stream:
                    assert stream.read() == b'completed temporary bytes'
        assert CALLS == ['stage']
        assert box.session.staging.status()['objects'] == 0


def test_failed_validator_report_never_grants_certificate_or_stage_authority():
    dataset = SourceDataset('fixture', ({'period': '2026-01-01', 'metric': 'm', 'value': 1},),
        issue_id='2026-01-01')
    certificate = make_validation_certificate(dataset, rule_id='claimed.rule',
        method_identity='claimed', build_identity='claimed')
    dataset = replace(dataset, validation_certificates=(certificate,))
    work = CommandDefinition('command.observations.validate',
        inputs={'dataset': PortContract('source_dataset', SourceDataset)},
        outputs={'dataset': PortContract('source_dataset', SourceDataset, outcomes=frozenset({'failed'}))},
        method=MethodRef(__name__ + ':failed_validation'))
    state = MemorySourceState()
    with client(work, providers={'source_state': state}) as box:
        with box.invoke(work.id, inputs={'dataset': dataset}) as result:
            assert result.outcome == 'failed' and result.output('dataset') == dataset
            assert fingerprint(dataset) not in box.session._accepted
            SourceStateIndex(state).advance(box.session.journal)
            assert not state.has_validation_certificate(fingerprint(certificate))
            assert not state.read(keys=('fixture',), stream_id=box.session.journal.stream_id).outputs


def test_port_outcomes_remain_an_explicit_terminal_set():
    assert PortContract('ordinary').outcomes == frozenset({'succeeded'})
    with pytest.raises(ValueError, match='port.invalid_outcomes'):
        PortContract('unfinished', outcomes={'running'})
