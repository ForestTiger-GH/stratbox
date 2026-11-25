"""Required same-run or exact-save handoff with independent delivery evidence."""
from stratbox.capabilities.model import OperationDefinition, GraphBody, Call, InputRef, OutputRef, ParameterRef
from stratbox.capabilities.commands import RECEIPT
from stratbox.capabilities.commands.notifications import HANDOFFS, PREPARED


def definitions():
    return tuple(OperationDefinition(capability_id, GraphBody((
        Call('prepare', 'notification.prepare_intents', {'effect': InputRef('effect')} if saved else {},
             {'key': ParameterRef('key'), 'max_dispatches': ParameterRef('max_dispatches'),
              'after_position': ParameterRef('after_position'), 'source_run_id': ParameterRef('source_run_id'),
              'allow_historical': historical, 'selector': ParameterRef('selector'),
              'dispatch_ids': ParameterRef('dispatch_ids'), 'max_pages': ParameterRef('max_pages'),
              'max_scan_pages': ParameterRef('max_scan_pages'), 'max_selected_dispatches': ParameterRef('max_selected_dispatches'),
              'expected_topic': ParameterRef('expected_topic')}),
        Call('handoff', command_id, {'prepared': OutputRef('prepare')}),
    ), {'handoffs': OutputRef('handoff'), 'prepared': OutputRef('prepare')}, required_effects=('handoff',)),
        inputs={'effect': RECEIPT} if saved else {}, outputs={'handoffs': HANDOFFS, 'prepared': PREPARED},
        parameters={'max_dispatches': 128, 'after_position': 0, 'source_run_id': None,
            'selector': None, 'dispatch_ids': (), 'max_pages': 50, 'max_scan_pages': 1000,
            'max_selected_dispatches': 10_000, 'expected_topic': None}, required_parameters=('key',),
        fixed={} if expected_topic is None else {'expected_topic': expected_topic},
        effects=frozenset({'notification.state_commit', 'notification.handoff'}))
        for capability_id, command_id, saved, historical, expected_topic in (
            ('notify.required', 'notification.handoff', False, False, None),
            ('notify.accepted', 'notification.handoff', False, False, 'value.accepted'),
            ('notify.saved', 'notification.handoff', True, False, 'effect.confirmed'),
            ('notify.reconcile', 'notification.reconcile_handoff', False, True, None)))
