"""Technical notification commands reuse the canonical transaction handlers."""
from stratbox.capabilities.model import AcceptanceContract, CommandDefinition, PortContract, ReuseContract
from stratbox.shared.data.processing import DataContract
from stratbox.shared.evidence import StoredBytesReceipt

PREPARED = PortContract(DataContract('notification.prepared', 1))
HANDOFFS = PortContract(DataContract('notification.handoffs', 1), tuple)


def definitions():
    return (
        CommandDefinition('notification.prepare_intents', 'stratbox.core.notifications.capability_handlers:prepare_intents',
            inputs={'effect': PortContract(DataContract('storage.receipt', 1), StoredBytesReceipt, required=False)},
            outputs={'value': PREPARED}, parameters={'max_dispatches': 128, 'after_position': 0,
                'source_run_id': None, 'allow_historical': False}, required_parameters=('key',),
            required_capabilities=frozenset({'notification_runtime'}),
            effects=frozenset({'notification.state_commit'}),
            acceptance=AcceptanceContract(partial_allowed=True),
            reuse=ReuseContract(shareable=False, completed=False, effects=frozenset({'notification.state_commit'}))),
        CommandDefinition('notification.handoff', 'stratbox.core.notifications.capability_handlers:handoff',
            inputs={'prepared': PREPARED}, outputs={'value': HANDOFFS},
            required_capabilities=frozenset({'notification_runtime'}),
            effects=frozenset({'notification.state_commit', 'notification.handoff'}),
            resources={'notification': 1, 'network': 1},
            acceptance=AcceptanceContract(partial_allowed=True),
            reuse=ReuseContract(shareable=False, completed=False,
                effects=frozenset({'notification.state_commit', 'notification.handoff'}))),
        CommandDefinition('notification.reconcile_handoff', 'stratbox.core.notifications.capability_handlers:reconcile_handoff',
            inputs={'prepared': PREPARED}, outputs={'value': HANDOFFS},
            required_capabilities=frozenset({'notification_runtime'}),
            effects=frozenset({'notification.state_commit', 'notification.handoff'}),
            resources={'notification': 1},
            acceptance=AcceptanceContract(partial_allowed=True),
            reuse=ReuseContract(shareable=False, completed=False,
                effects=frozenset({'notification.state_commit', 'notification.handoff'}))),
    )
