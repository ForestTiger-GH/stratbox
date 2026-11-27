"""Readiness is derived from the selected plan, bindings and actual inputs."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReadinessCheck:
    code: str
    phase: str
    status: str
    task_id: str | None = None
    detail: str = ''
    conditional: bool = False

    def __post_init__(self):
        if self.status not in {'ready', 'deferred', 'blocked'}:
            raise ValueError('readiness.status_invalid')


@dataclass(frozen=True, slots=True)
class PreflightReport:
    capability_id: str
    plan_identity: str | None
    build_identity: str | None
    checks: tuple[ReadinessCheck, ...]
    required_providers: tuple[str, ...] = ()
    target_id: str | None = None

    @property
    def admissible(self):
        return not any(check.status == 'blocked' and not check.conditional for check in self.checks)

    @property
    def status(self):
        if not self.admissible:
            return 'blocked'
        return 'conditional' if any(check.status != 'ready' for check in self.checks) else 'ready'


def _commands(plan, *, conditional=False, prefix=''):
    from stratbox.capabilities.plan.models import CommandTask, MapTask, RepeatTask, DispatchTask
    for task in plan.tasks:
        condition = conditional or task.condition is not None
        path = prefix + task.task_id
        if isinstance(task, CommandTask):
            yield path, task, condition
        elif isinstance(task, (MapTask, RepeatTask)):
            yield from _commands(task.template, conditional=condition, prefix=path + '/')
        elif isinstance(task, DispatchTask):
            for name, alternative in sorted(task.alternatives.items()):
                yield from _commands(alternative, conditional=True, prefix=path + '/' + name + '/')


def assess_plan(box, plan, *, resolve_methods=True):
    """A successful check permits an attempt; output qualification remains live.

    Scientific input checks run in their owning methods after material inspection
    and operand resolution. Preflight never labels an unseen layout as reviewed.
    """
    from stratbox.core.runtime.capabilities import ProviderBinding, CapabilityRequirement, select_provider
    from stratbox.capabilities.plan.validation import validate_plan
    validate_plan(plan)
    checks, providers = [], set()
    for path, task, conditional in _commands(plan):
        command = task.command
        declared = command.scientific_limitations
        if declared:
            for limitation in declared:
                checks.append(ReadinessCheck(limitation, 'scientific_binding', 'blocked', path,
                    'Declared by the selected immutable domain binding and enforced before method invocation.', conditional))
        else:
            checks.append(ReadinessCheck('readiness.binding_selected', 'binding', 'ready', path,
                                          command.method.locator, conditional))
        if resolve_methods:
            try:
                command.method.resolve()
            except (ImportError, AttributeError, TypeError, ValueError) as error:
                checks.append(ReadinessCheck('readiness.method_unavailable', 'binding', 'blocked', path,
                                              type(error).__name__ + ': ' + str(error), conditional))
        for role in sorted(command.required_providers):
            providers.add(role)
            if role in box.providers:
                provider = box.providers[role]
                try:
                    if isinstance(provider, ProviderBinding):
                        select_provider(CapabilityRequirement(role), (provider,))
                    elif provider is None:
                        raise ValueError('provider.unavailable')
                except ValueError as error:
                    checks.append(ReadinessCheck(str(error), 'provider', 'blocked', path, role, conditional))
                else:
                    status = 'deferred' if isinstance(provider, ProviderBinding) and provider.readiness == 'degraded' else 'ready'
                    checks.append(ReadinessCheck('readiness.provider_bound', 'provider', status, path, role, conditional))
            elif role == 'notification_state':
                checks.append(ReadinessCheck('readiness.default_notification_state', 'provider', 'ready', path,
                                              'The execution session supplies its ordinary in-memory notification state.', conditional))
            elif role in {'http', 'filestore', 'secrets'}:
                checks.append(ReadinessCheck('readiness.default_provider_resolution', 'provider', 'deferred', path, role, conditional))
            else:
                checks.append(ReadinessCheck('provider.missing:' + role, 'provider', 'blocked', path, role, conditional))
        if command.source_requirements:
            checks.append(ReadinessCheck('readiness.source_layout_and_semantics', 'semantic_use', 'deferred', path,
                                          'Actual source attribution, layout and period/subject semantics are checked by this method.', conditional))
        if command.id.startswith(('command.calculate.', 'command.calculation.')):
            checks.append(ReadinessCheck('readiness.operand_closure', 'calculation', 'deferred', path,
                                          'Method-specific operands, comparability and coverage are checked on resolved input.', conditional))
        if command.effects:
            checks.append(ReadinessCheck('readiness.effect_preconditions', 'effect', 'deferred', path,
                                          ', '.join(sorted(command.effects)), conditional))
    checks.append(ReadinessCheck('readiness.output_acceptance', 'acceptance', 'deferred',
                                 detail='Actual outcomes, output contracts and selected member obligations are assessed after execution.'))
    return PreflightReport(plan.capability_id, plan.fingerprint, plan.build_identity, tuple(checks),
                           tuple(sorted(providers)), getattr(plan.target, 'id', plan.target) if isinstance(plan.target, str) or hasattr(plan.target, 'id') else None)


def preflight(box, capability, *, inputs=None, parameters=None, target=None, outputs=None, resolve_methods=True):
    from stratbox.capabilities.plan import PreparedPlan
    try:
        if isinstance(capability, PreparedPlan):
            if any(value is not None for value in (inputs, parameters, target, outputs)):
                raise ValueError('sdk.prepared_plan_arguments')
            plan = capability
        else:
            plan = box.prepare(capability, inputs=inputs, parameters=parameters, target=target, outputs=outputs)
        return assess_plan(box, plan, resolve_methods=resolve_methods)
    except (ValueError, TypeError, KeyError) as error:
        identifier = getattr(capability, 'id', getattr(capability, 'capability_id', str(capability)))
        return PreflightReport(identifier, None, None,
            (ReadinessCheck(str(error), 'preparation', 'blocked', detail=type(error).__name__),),
            target_id=target if isinstance(target, str) else getattr(target, 'id', None))
