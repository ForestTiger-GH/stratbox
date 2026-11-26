"""Bounded journal acknowledgement recovery from durable subscription progress."""
from .consumption import NotificationRejected


def recover_journal_cursor(journal,state,subscription_id,*,consumer_id=None,max_pages=100,page_size=1000):
    """Acknowledge already committed source coverage without preparing it again.

    The journal and subscription remain separate owners. Only a durable matching
    state checkpoint permits acknowledgement across their crash window.
    """
    if (type(max_pages) is not int or max_pages<1 or type(page_size) is not int
            or not 1<=page_size<=10000):
        raise NotificationRejected('notification.invalid_recovery_limits')
    consumer_id=subscription_id if consumer_id is None else consumer_id
    committed=state.checkpoint(subscription_id)
    retained=journal.checkpoint()
    if committed is None:
        raise NotificationRejected('notification.subscription_checkpoint_required')
    if committed['stream_id']!=retained.stream_id:
        raise NotificationRejected('notification.journal_stream_changed')
    if consumer_id not in retained.consumers:
        raise NotificationRejected('notification.journal_consumer_required')
    position,target=retained.consumers[consumer_id],committed['sequence']
    if position>target:
        raise NotificationRejected('notification.journal_ahead_of_state')
    if target>retained.tail:
        raise NotificationRejected('notification.state_ahead_of_journal')
    for _ in range(max_pages):
        if position==target: break
        limit=min(page_size,target-position)
        page=journal.read_page(after=position,limit=limit,scan_limit=limit)
        if page.stream_id!=retained.stream_id or not position<page.scanned_through<=target:
            raise NotificationRejected('notification.recovery_coverage_conflict')
        position=journal.acknowledge(consumer_id,page)
    return {'sequence':position,'target':target,'complete':position==target}
