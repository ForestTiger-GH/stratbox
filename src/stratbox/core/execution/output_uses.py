"""Logical output authority, independent of readable payload identity."""
from dataclasses import dataclass
from collections.abc import Mapping

SUCCESS = frozenset({'succeeded', 'partial'})
PENDING = frozenset({'pending', 'preparing', 'prepared', 'expanding', 'running', 'waiting_shared',
                     'awaiting_acceptance', 'accepting', 'preparing_inputs'})


@dataclass(frozen=True)
class OutputUse:
    run_id: str
    scope_id: str
    task_id: str
    output_name: str
    outcome: str
    disposition: str
    role: str = 'data'
    origins: tuple[tuple, ...] = ()

    @property
    def origin(self):
        return (self.run_id, self.scope_id, self.task_id, self.output_name,
                self.outcome, self.disposition)

    def fact(self):
        return {'output_disposition': self.disposition,
                'producer_outcome': self.outcome, 'output_role': self.role,
                'origin_uses': self.origins or (self.origin,)}


def referenced_uses(run, reference):
    if hasattr(reference, 'task_id') and hasattr(reference, 'port'):
        task = run.tasks[reference.task_id]
        use = task.output_uses.get(reference.port)
        if use is not None:
            yield use
    elif isinstance(reference, Mapping):
        for item in reference.values():
            yield from referenced_uses(run, item)
    elif isinstance(reference, (tuple, list)):
        for item in reference:
            yield from referenced_uses(run, item)


def unsuccessful(states):
    states = set(states)
    if 'unknown' in states:
        return 'unknown'
    if 'cancelled' in states:
        return 'cancelled'
    if states - SUCCESS:
        return 'failed'
    return 'partial' if 'partial' in states else 'succeeded'


def member_assessment(run, reference, *, required_tasks=(), effects=None):
    """Assess the declared member, not every transitive prerequisite.

    Independently accepted early outputs survive unrelated later failures.
    A collected composite contributes its explicit required member tasks.
    """
    uses = tuple(referenced_uses(run, reference))
    states = [use.outcome for use in uses]
    states.extend(run.tasks[key].state for key in required_tasks)
    if any(state in PENDING for state in states):
        return None, uses
    status = unsuccessful(states)
    if any(use.disposition == 'reported' or use.role == 'diagnostic' for use in uses):
        status = unsuccessful((*states, 'failed'))
    if effects == 'unknown':
        status = 'unknown'
    return status, uses


def output_use(run, task, name, *, role=None, accepted=None, origins=()):
    if role is None:
        command = getattr(task.spec, 'command', None)
        role = getattr(command.outputs.get(name), 'role', None) if command else None
    return OutputUse(run.run_id, task.spec.scope_id, task.spec.task_id, name,
        task.state, 'accepted' if (task.state in SUCCESS if accepted is None else accepted) else 'reported',
        role or 'data', tuple(dict.fromkeys(origins)))
