"""Required same-run or exact-save handoff with independent delivery evidence."""
from stratbox.capabilities.model import OperationDefinition, GraphBody, Call, InputRef, OutputRef, ParameterRef
from stratbox.capabilities.commands import RECEIPT
from stratbox.capabilities.commands.notifications import HANDOFFS, PREPARED


def definitions():
    return tuple(OperationDefinition(capability_id, GraphBody((
        Call('prepare', 'notification.prepare_intents', {'effect': InputRef('effect')} if saved else {},
             {'key': ParameterRef('key'), 'max_dispatches': ParameterRef('max_dispatches'),
              'after_position': ParameterRef('after_position'), 'source_run_id': ParameterRef('source_run_id'),
              'allow_historical': historical}),
        Call('handoff', command_id, {'prepared': OutputRef('prepare')}),
    ), {'handoffs': OutputRef('handoff'), 'prepared': OutputRef('prepare')}, required_effects=('handoff',)),
        inputs={'effect': RECEIPT} if saved else {}, outputs={'handoffs': HANDOFFS, 'prepared': PREPARED},
        parameters={'max_dispatches': 128, 'after_position': 0, 'source_run_id': None}, required_parameters=('key',),
        effects=frozenset({'notification.state_commit', 'notification.handoff'}))
        for capability_id, command_id, saved, historical in (
            ('notify.accepted', 'notification.handoff', False, False),
            ('notify.saved', 'notification.handoff', True, False),
            ('notify.reconcile', 'notification.reconcile_handoff', False, True)))
