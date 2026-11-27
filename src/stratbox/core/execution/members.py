"""Stable collection outcomes independent of completion order."""
from collections.abc import Mapping
from stratbox.shared.data.materials import StagedMaterialRef
from stratbox.shared.data.selection import MemberOutcome
from stratbox.shared.data.values import ImmutableMaterialRef, SnapshotRef, fingerprint


def member_key(value, ordinal, identity=None):
    if identity is not None:
        return identity
    from stratbox.core.storage.readable import carrier
    physical = carrier(value)
    metadata = getattr(physical,'metadata',{})
    coordinate = (getattr(value,'source_id',None),getattr(value,'issue_id',None) or metadata.get('issue_id'),
        getattr(value,'asset_id',None) or metadata.get('asset_id'),
        getattr(value,'locator',None),getattr(physical,'identity',None),metadata.get('member'))
    if any(part is not None for part in coordinate):
        return fingerprint(coordinate)
    try:
        return fingerprint(value)
    except (ValueError,TypeError):
        return fingerprint(('member',ordinal))


def referenced_tasks(value):
    if hasattr(value, 'task_id') and hasattr(value, 'port'):
        return {value.task_id}
    parts = value.values() if isinstance(value, Mapping) else value if isinstance(value, (tuple, list)) else ()
    return set().union(*(referenced_tasks(part) for part in parts)) if parts else set()


def dependency_members(run, item):
    pending, found = list(referenced_tasks(item)), {}
    while pending:
        key = pending.pop()
        if key in found or key not in run.tasks:
            continue
        task = run.tasks[key]
        found[key] = task
        pending.extend(getattr(task.spec, 'deps', ()))
    return tuple(found[key] for key in sorted(found))


def outcome(value, ordinal, status, children=(), result=None, *, effect_state=None, identity=None):
    from stratbox.core.observability.projections.source_state import output_stage
    references, stages, diagnostics = [], [], []
    def retain(item):
        if isinstance(item,(ImmutableMaterialRef,SnapshotRef,StagedMaterialRef)):
            references.append(item)
        elif isinstance(item, Mapping):
            for part in item.values():
                retain(part)
        elif isinstance(item, (tuple, list)):
            for part in item:
                retain(part)
        elif getattr(item, 'material', None) is not None:
            retain(item.material)
    if result is not None:
        retain(result)
    for child in children:
        diagnostics.extend(child.findings)
        command = getattr(child.spec,'command',None)
        if command:
            for name, output in child.outputs.items():
                stage = output_stage(command.id,name)
                use = child.output_uses.get(name)
                if stage and use is not None and use.disposition == 'accepted' and use.role != 'diagnostic':
                    stages.append(stage)
                retain(output)
    unique = {fingerprint(reference):reference for reference in references}
    effect_state = 'unknown' if any(child.state == 'unknown' for child in children) else effect_state
    return MemberOutcome(member_key(value,ordinal,identity),ordinal,status,
        tuple(dict.fromkeys(stages)),tuple(unique.values()),tuple(dict.fromkeys(diagnostics)),effect_state)
