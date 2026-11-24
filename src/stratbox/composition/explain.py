"""Bounded plan projections expose selection, scopes and shared physical work."""
from .plan import ExecutionPlan
from ._validation import CompositionError


def explain_plan(plan, *, task_limit=1000):
    if not isinstance(plan,ExecutionPlan):
        raise CompositionError("composition.plan_required")
    if type(task_limit) is not int or task_limit < 0:
        raise CompositionError("composition.invalid_limit")
    return {
        "plan_id": plan.plan_id,
        "definition_id": plan.definition_id,
        "root_kind": plan.root_kind,
        "physical_work_count": len({plan.logical_to_physical[task.task_id] for task in plan.tasks if task.operation_id is not None}),
        "sharing_basis": "Prepared identities; execution rechecks resolved values and consumer eligibility",
        "logical_use_count": sum(1 + len(task.aliases) for task in plan.tasks if task.operation_id is not None),
        "task_count": len(plan.tasks),
        "complete": len(plan.tasks) <= task_limit,
        "outputs": tuple(plan.outputs),
        "bindings": dict(plan.selected_bindings),
        "scopes": tuple({"scope_id":scope.scope_id,"definition_id":scope.definition_id,"kind":scope.kind,
                         "parent_id":scope.parent_id,"required":scope.required,
                         "outputs":tuple(scope.outputs),"required_checks":scope.required_checks,
                         "required_effects":scope.required_effects} for scope in plan.scopes),
        "tasks": tuple({"task_id":task.task_id,"capability_id":task.operation_id,
                        "kind":task.capability_kind,"scope_id":task.scope_id,
                        "acceptance_scope":task.acceptance_scope,"dependencies":task.dependencies,
                        "logical_uses":(task.task_id,*task.aliases),"work_identity":task.work_identity,
                        "reuse_eligible":task.reuse_eligible} for task in plan.tasks[:task_limit]),
        "logical_to_physical": dict(plan.logical_to_physical),
        "physical_to_logical": dict(plan.physical_to_logical),
    }
