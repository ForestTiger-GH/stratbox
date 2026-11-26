"""Optional callbacks cannot own coordinator progress, resources or shutdown."""
from threading import Event,Thread
from time import monotonic,sleep
from dataclasses import replace

from stratbox.core.execution.service import ExecutionService,ExecutionSettings
from stratbox.capabilities.model import MethodRef,PortContract,ReuseContract
from stratbox.capabilities.plan.models import BoundCommand,CommandTask,PreparedPlan,ValueRef


def echo(inputs,settings,context): return {'value':inputs['value']}


def plan(value):
    command=BoundCommand('command.test.echo',MethodRef(__name__+':echo'),None,
        {'value':PortContract('integer',int)},{'value':PortContract('integer',int)},
        resources={'cpu':1},reuse=ReuseContract(shareable=False,completed=False))
    return PreparedPlan('test.observer',(CommandTask('echo',command,{'value':value}),),(),
        {'value':ValueRef('echo')},'plan','build')


def eventually(predicate):
    until=monotonic()+2
    while monotonic()<until:
        if predicate():return
        sleep(.001)
    assert predicate()


def test_blocked_optional_callback_does_not_block_work_close_or_spawn_replacements():
    entered,release=Event(),Event()
    calls=[]
    def observer(fact):
        calls.append(fact);entered.set()
        release.wait(5)
    settings=ExecutionSettings(observer_queue_capacity=2,observer_queue_bytes=100000,
        observer_diagnostic_capacity=3)
    service=ExecutionService(settings=settings,observer=observer)
    try:
        first=service.submit(plan(1))
        assert entered.wait(1)
        assert first.result(1).output()==1
        assert service.run(plan(2)).output()==2
        health=service.observer_status()
        assert health.active and health.dropped and health.queued<=2
        assert health.queued_bytes+health.active_bytes<=settings.observer_queue_bytes
        assert len(health.diagnostics)<=3 and health.history_truncated
        assert len(calls)==1
        started=monotonic();service.close()
        assert monotonic()-started<1
        assert service.state=='closed' and service.observer_status().active
        assert service.observer_status().closed
        assert service.observer_status().replay_after
    finally:
        release.set();service.close()


def test_observer_can_reenter_run_without_the_coordinator_lock():
    entered,finished=Event(),Event()
    outputs=[]
    service=None
    def observer(fact):
        if entered.is_set():return
        entered.set()
        outputs.append(service.run(plan(99)).output())
        finished.set()
    with ExecutionService(settings=ExecutionSettings(max_workers=1),observer=observer) as service:
        outer=service.run(plan(3))
        assert outer.output()==3 and finished.wait(2)
        assert outputs==[99]


def test_observer_can_close_service_with_wait_without_self_join():
    finished=Event()
    service=None
    def observer(fact):
        if fact.kind=='run.finished':
            service.close(wait=True)
            finished.set()
    service=ExecutionService(observer=observer)
    try:
        assert service.run(plan(1)).output()==1
        assert finished.wait(2)
        assert service.state=='closed'
    finally:service.close()


def test_failure_and_overflow_preserve_authoritative_fact_replay_coordinates():
    called=Event()
    def observer(fact):
        called.set()
        raise RuntimeError('private observer failure')
    with ExecutionService(observer=observer) as service:
        result=service.run(plan(7))
        assert result.outcome=='succeeded' and result.output()==7
        assert called.wait(1)
        eventually(lambda:service.observer_status().failed>0)
        health=service.observer_status()
        assert all(item.code=='observation.optional_sink_failed' for item in health.diagnostics)
        assert 'private observer failure' not in repr(health)
        stream,after=health.replay_after[0]
        facts=service.journal.read(after=after)
        assert facts and facts[0].stream_id==stream


def test_oversized_fact_is_dropped_without_retaining_it_or_calling_the_sink():
    called=Event()
    with ExecutionService(settings=ExecutionSettings(observer_queue_bytes=1),observer=lambda fact:called.set()) as service:
        assert service.run(plan(4)).output()==4
        health=service.observer_status()
        assert health.dropped and not health.queued and not health.active and not called.is_set()


def test_later_inflight_delivery_never_advances_replay_past_the_first_missed_fact():
    from stratbox.core.execution.observers import ObserverStatus
    health=ObserverStatus(0,0,True,1,10,0,5,False,(),True,('stream',4),('stream',100))
    assert health.replay_after==(('stream',3),)
