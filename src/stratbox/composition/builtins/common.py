"""Small helpers for supplied, inspectable domain workflows."""
from __future__ import annotations

from stratbox.core.execution.handoff import PreparedInput, ProjectedOutput, prepare_input
from stratbox.shared.data.processing import DataContract, DataRole


def network_retry(policy=None):
    """The graph owns the single safe transport retry budget."""
    from stratbox.composition.models import RetryPolicy
    return RetryPolicy(max_attempts=3 if policy is None else policy.attempts,
        delay=0.5 if policy is None else policy.initial_delay_seconds,
        retry_codes=("http.connection_error", "http.timeout", "http.truncated",
                     "http.status_429", "http.status_500", "http.status_502", "http.status_503", "http.status_504"))


def value_input(value, schema, role=None):
    from stratbox.composition.models import InputRef, PlanOutputRef
    if isinstance(value, (PreparedInput, ProjectedOutput, InputRef, PlanOutputRef)):
        return value
    return prepare_input(value, DataContract(schema, role=None if role is None else DataRole(role)))


def selected_output(scenario, output):
    """Keep exactly the selected product's prerequisites."""
    from dataclasses import replace
    from stratbox.composition.compiler import iter_references
    if output is None or output == "all":
        return scenario
    if output not in scenario.outputs:
        raise ValueError("workflow.output_unavailable")
    selected = {output: scenario.outputs[output]}
    needed = {ref.task for ref in iter_references(selected)}
    by_id = {step.step_id: step for step in scenario.steps}
    pending = list(needed)
    while pending:
        step = by_id[pending.pop()]
        dependencies = {ref.task for ref in iter_references((getattr(step, "inputs", {}),
                        getattr(step, "parameters", {}),
                        getattr(getattr(step, "collect", None), "inputs", ())))} | set(step.depends_on)
        pending.extend(dependencies - needed)
        needed.update(dependencies)
    return replace(scenario, outputs=selected, steps=tuple(step for step in scenario.steps if step.step_id in needed))
