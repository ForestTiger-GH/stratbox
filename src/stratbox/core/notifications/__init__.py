"""Qualified notifications with lazily resolved public exports."""

from importlib import import_module

_SYMBOL_MODULES = {'AccessDecision': 'stratbox.core.notifications.contracts',
 'AccessRequest': 'stratbox.core.notifications.contracts',
 'AdmittedHandoff': 'stratbox.core.notifications.contracts',
 'Attempt': 'stratbox.core.notifications.state.contracts',
 'AuditBatch': 'stratbox.core.notifications.state.contracts',
 'CheckpointKey': 'stratbox.core.notifications.state.contracts',
 'CheckpointUpdate': 'stratbox.core.notifications.state.contracts',
 'ConsumerBinding': 'stratbox.core.notifications.runtime',
 'DeliverRequest': 'stratbox.core.notifications.dispatch.contracts',
 'DeliveryResult': 'stratbox.core.notifications.dispatch.contracts',
 'Dispatch': 'stratbox.core.notifications.state.contracts',
 'DispatchStatus': 'stratbox.core.notifications.projections',
 'DispatchUpdate': 'stratbox.core.notifications.state.contracts',
 'DownstreamStage': 'stratbox.core.notifications.projections',
 'EventPointer': 'stratbox.core.notifications.contracts',
 'ExternalDeliveryReceipt': 'stratbox.core.notifications.projections',
 'FilterCondition': 'stratbox.core.notifications.contracts',
 'HandoffLookup': 'stratbox.core.notifications.contracts',
 'HandoffReceipt': 'stratbox.core.notifications.contracts',
 'InspectRequest': 'stratbox.core.notifications.dispatch.preparation',
 'Inspection': 'stratbox.core.notifications.dispatch.preparation',
 'MemoryNotificationState': 'stratbox.core.notifications.state.memory',
 'NotificationAuthority': 'stratbox.core.notifications.contracts',
 'NotificationConsumer': 'stratbox.core.notifications.contracts',
 'NotificationHealth': 'stratbox.core.notifications.projections',
 'NotificationIntent': 'stratbox.core.notifications.contracts',
 'NotificationReadRuntime': 'stratbox.core.notifications.runtime',
 'NotificationRoute': 'stratbox.core.notifications.contracts',
 'NotificationRuntime': 'stratbox.core.notifications.runtime',
 'NotificationStateReader': 'stratbox.core.notifications.state.contracts',
 'NotificationStateStore': 'stratbox.core.notifications.state.contracts',
 'NotificationTopic': 'stratbox.core.notifications.topics',
 'PreparationReport': 'stratbox.core.notifications.dispatch.preparation',
 'PrepareRequest': 'stratbox.core.notifications.dispatch.preparation',
 'Projection': 'stratbox.core.notifications.topics',
 'QualifiedHandoff': 'stratbox.core.notifications.dispatch.contracts',
 'QualifyDeliveryRequest': 'stratbox.core.notifications.dispatch.contracts',
 'ReconcileDeliveryRequest': 'stratbox.core.notifications.dispatch.contracts',
 'RecordIdentity': 'stratbox.core.notifications.state.contracts',
 'Replay': 'stratbox.core.notifications.state.contracts',
 'RetryPolicy': 'stratbox.core.notifications.dispatch.contracts',
 'SourceBinding': 'stratbox.core.notifications.runtime',
 'StateMutation': 'stratbox.core.notifications.state.contracts',
 'StateReceipt': 'stratbox.core.notifications.state.contracts',
 'Subscription': 'stratbox.core.notifications.contracts',
 'SubscriptionChange': 'stratbox.core.notifications.subscriptions',
 'SubscriptionSpec': 'stratbox.core.notifications.contracts',
 'TopicAvailability': 'stratbox.core.notifications.projections',
 'TopicCatalog': 'stratbox.core.notifications.topics',
 'accessible_topics': 'stratbox.core.notifications.projections',
 'amend_checkpoint': 'stratbox.core.notifications.subscriptions',
 'build_catalog': 'stratbox.core.notifications.topics',
 'configure_subscription': 'stratbox.core.notifications.subscriptions',
 'decode_state_mutation': 'stratbox.core.notifications.state.codec',
 'deliver': 'stratbox.core.notifications.operations',
 'encode_state_mutation': 'stratbox.core.notifications.state.codec',
 'flush_audit': 'stratbox.core.notifications.state.audit',
 'inspect': 'stratbox.core.notifications.dispatch.preparation',
 'inspect_dispatch': 'stratbox.core.notifications.projections',
 'notification_health': 'stratbox.core.notifications.projections',
 'prepare': 'stratbox.core.notifications.operations',
 'project_downstream': 'stratbox.core.notifications.projections',
 'qualify': 'stratbox.core.notifications.operations',
 'reconcile': 'stratbox.core.notifications.operations',
 'record_external_delivery': 'stratbox.core.notifications.projections',
 'register_replay': 'stratbox.core.notifications.subscriptions'}
__all__ = tuple(_SYMBOL_MODULES)


def __getattr__(name):
    module = _SYMBOL_MODULES.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module), name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))
