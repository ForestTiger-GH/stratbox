"""Frozen conditional maintenance with explicit retained prerequisites."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import Mapping

from stratbox.core.execution.errors import error_code
from stratbox.core.execution.service import CommandCompletion, ExecutionFailure
from stratbox.core.formats.archives.members import ArchiveLimits, open_zip_stream
from stratbox.core.formats.archives.store import validate_output_names
from stratbox.core.storage.filestore import MutationRejected
from stratbox.core.storage.readable import open_provider, scan_identity
from stratbox.shared.data.materials import NamedEffectIntent, NamedMaterialReceipt
from stratbox.shared.data.values import ImmutableMaterialRef, fingerprint
from stratbox.shared.identity import ByteIdentity
from ._physical import open_material
from ._settings import _get, _option
from ._storage import _compact_reference, _confirmed_reference, _provider_scope


def _prerequisite(requirement):
    if isinstance(requirement, ImmutableMaterialRef):
        return {"reference": _compact_reference(requirement)}
    if not isinstance(requirement, Mapping) or not isinstance(requirement.get("reference"), ImmutableMaterialRef):
        raise ExecutionFailure("maintenance.retained_prerequisite_required")
    result = {"reference": _compact_reference(requirement["reference"])}
    if "archive_members" in requirement:
        members = tuple(requirement["archive_members"])
        if not members or len(members) > 10000:
            raise ExecutionFailure("maintenance.archive_prerequisite_limit")
        if any(not isinstance(member, Mapping) or not isinstance(member.get("identity"), ByteIdentity)
               or not isinstance(member.get("name"), str) for member in members):
            raise ExecutionFailure("maintenance.archive_prerequisite_invalid")
        validate_output_names(tuple(member["name"] for member in members))
        result["archive_members"] = tuple({"name": member["name"], "identity": member["identity"]} for member in members)
    return result


def _verify_prerequisites(requirements, context):
    """Read exact archived members; metadata alone never permits deletion."""
    if not isinstance(requirements, (tuple, list)) or len(requirements) > 1000:
        raise ExecutionFailure("maintenance.prerequisite_limit")
    preserved = set()
    for raw in requirements:
        requirement = _prerequisite(raw)
        reference = _confirmed_reference(requirement["reference"], context)
        expected = requirement.get("archive_members")
        if expected is None:
            preserved.add(reference.identity)
            continue
        total = sum(item["identity"].size for item in expected)
        limits = ArchiveLimits(10000, max(1, total),
            max(1, max(item["identity"].size for item in expected)), max(1, reference.identity.size))
        with open_material(reference, context) as stream, open_zip_stream(
                stream, reference.identity.size, limits, budget=getattr(context, "budget", None)) as archive:
            actual = tuple(info.filename for info in archive.infolist() if not info.is_dir())
            if actual != tuple(item["name"] for item in expected):
                raise ExecutionFailure("maintenance.archive_plan_mismatch")
            for item in expected:
                with archive.open(item["name"]) as member:
                    observed = scan_identity(member, limit=item["identity"].size,
                        checkpoint=context.checkpoint, budget=getattr(context, "budget", None), resource="decoded_bytes")
                if observed != item["identity"]:
                    raise ExecutionFailure("maintenance.archive_member_mismatch")
                preserved.add(observed)
    return preserved


def material_maintenance_plan(inputs, settings, context):
    actions = tuple(_option(context, settings, "actions", ()))
    if not actions:
        return {"plan": ()}
    if len(actions) > _option(context, settings, "max_actions", 1000):
        raise ExecutionFailure("maintenance.action_limit")
    available = {str(item.get("path")) if isinstance(item, Mapping) else str(item) for item in inputs["inventory"]}
    if any(str(_get(action, "source")) not in available for action in actions):
        raise ExecutionFailure("maintenance.inventory_mismatch")
    prerequisites = tuple(_prerequisite(item) for item in inputs.get("prerequisites", _option(context, settings, "prerequisites", ())))
    planned = _normalize_actions(actions, _option(context, settings, "scope"), prerequisites)
    plan_identity = fingerprint((inputs["inventory"], planned))
    return {"plan": tuple({**action, "plan_identity": plan_identity} for action in planned)}


def _within(path, scope):
    if not isinstance(path, str) or not path or "\x00" in path:
        return False
    path, scope = Path(path.replace("\\", "/")), Path(str(scope).replace("\\", "/"))
    return ".." not in path.parts and ".." not in scope.parts and path.is_relative_to(scope)


def _normalize_actions(actions, scope, common=()):
    """Validate the complete finite order before any provider mutation."""
    if not isinstance(scope, str) or not scope or "\x00" in scope:
        raise ExecutionFailure("maintenance.explicit_scope_required")
    planned, known = [], set()
    for ordinal, action in enumerate(actions):
        action_id = _get(action, "action_id", "action-" + str(ordinal + 1))
        if not isinstance(action_id, str) or not action_id or len(action_id) > 256 or "\x00" in action_id:
            raise ExecutionFailure("maintenance.action_id_required")
        if action_id in known:
            raise ExecutionFailure("maintenance.duplicate_action_id")
        depends_on = _get(action, "depends_on", ())
        if (not isinstance(depends_on, (tuple, list)) or any(not isinstance(item, str) for item in depends_on)
                or len(set(depends_on)) != len(depends_on) or not set(depends_on) <= known):
            raise ExecutionFailure("maintenance.dependency_order_invalid")
        source, operation = _get(action, "source"), _get(action, "operation")
        if operation not in {"copy", "move", "delete"}:
            raise ExecutionFailure("maintenance.operation_invalid")
        if _get(action, "scope", scope) != scope:
            raise ExecutionFailure("maintenance.scope_conflict")
        if not _within(source, scope):
            raise ExecutionFailure("maintenance.explicit_scope_required")
        destination = _get(action, "destination") if operation in {"copy", "move"} else source
        if not _within(destination, scope):
            raise ExecutionFailure("maintenance.destination_outside_scope")
        if operation in {"copy", "move"} and Path(source) == Path(destination):
            raise ExecutionFailure("maintenance.source_destination_same")
        if operation == "move" and Path(source).parent != Path(destination).parent:
            raise ExecutionFailure("maintenance.same_directory_required")
        expected = _get(action, "expected_identity")
        if not isinstance(expected, ByteIdentity):
            raise ExecutionFailure("maintenance.expected_identity_required")
        policy, expected_destination = _get(action, "policy", "create_only"), _get(action, "expected_destination")
        if (policy not in {"create_only", "replace_if_matches"}
                or policy == "replace_if_matches" and (operation != "copy" or not isinstance(expected_destination, ByteIdentity))
                or policy == "create_only" and expected_destination is not None):
            raise ExecutionFailure("maintenance.conditional_policy_required")
        expected_revision = _get(action, "expected_destination_revision")
        if expected_revision is not None and (policy != "replace_if_matches" or not isinstance(expected_revision, str) or not expected_revision):
            raise ExecutionFailure("maintenance.destination_revision_invalid")
        ancestor = _get(action, "retained_ancestor")
        if ancestor is not None:
            if operation != "copy" or not isinstance(ancestor, ImmutableMaterialRef) or ancestor.identity != expected:
                raise ExecutionFailure("maintenance.retained_ancestor_invalid")
            ancestor = _compact_reference(ancestor)
        prerequisites = (*common, *(tuple(_prerequisite(item) for item in _get(action, "prerequisites", ()))))
        planned.append({"action_id": action_id, "depends_on": tuple(depends_on), "scope": scope,
            "source": source, "operation": operation, "destination": destination, "expected_identity": expected,
            "policy": policy, "expected_destination": expected_destination,
            "expected_destination_revision": expected_revision, "retained_ancestor": ancestor,
            "prerequisites": prerequisites, "plan_identity": _get(action, "plan_identity")})
        known.add(action_id)
    return tuple(planned)


@contextmanager
def _open_copy_source(store, path, context):
    with open_provider(store, path) as stream:
        class AccountedReader:
            def read(self, size):
                data = stream.read(size)
                if getattr(context, "budget", None):
                    context.budget.charge("input_bytes", len(data))
                return data
        yield AccountedReader()


def _perform(intent, effect_id, context):
    store = context.provider("filestore")
    try:
        inspect = getattr(store, "inspect_file_budgeted", None)
        observed = inspect(intent.source, budget=getattr(context, "budget", None), checkpoint=context.checkpoint) \
            if callable(inspect) else store.inspect_file(intent.source)
    except FileNotFoundError:
        raise MutationRejected("Source is absent", code="maintenance.state_conflict") from None
    except Exception as error:
        raise MutationRejected("Source could not be verified", code=error_code(error)) from error
    if observed.identity != intent.expected_source:
        raise MutationRejected("Source changed", code="maintenance.state_conflict")
    enriched = replace(intent, expected_source_revision=observed.revision)
    context.update_effect_intent(effect_id, enriched)
    if intent.operation == "copy":
        from .artifacts import _copy_named
        return _copy_named(None, enriched, context,
            source_opener=lambda: _open_copy_source(store, intent.source, context),
            update_intent=lambda updated: context.update_effect_intent(effect_id, updated), effect_id=effect_id)
    apply = getattr(store, "apply_named_mutation", None)
    if callable(apply):
        return apply(effect_id, enriched, checkpoint=context.checkpoint)
    # A provider with guarded mutations can confirm its synchronous result;
    # restart reconciliation needs its separate transition-evidence capability.
    with store.guard_directory(str(Path(intent.source).parent)):
        current = store.inspect_file(intent.source)
        if current != observed:
            raise MutationRejected("Source changed", code="maintenance.state_conflict")
        success = store.rename_expected(observed, intent.destination) if intent.operation == "move" else store.remove_expected(observed)
        if not success:
            raise MutationRejected("Conditional mutation rejected", code="maintenance.state_conflict")
    return NamedMaterialReceipt(intent.destination, intent.identity, intent.provider_scope,
        operation=intent.operation, guarantee="guarded_conditional_transition")


def _outcome(action, ordinal, outcome, *, receipt=None, findings=(), blocked_by=()):
    return {"action_id": action["action_id"], "ordinal": ordinal, "operation": action["operation"],
        "source": action["source"], "destination": action["destination"], "depends_on": action["depends_on"],
        "outcome": outcome, "effect_id": getattr(receipt, "effect_id", None),
        "effect_state": getattr(receipt, "status", None), "findings": tuple(findings), "blocked_by": tuple(blocked_by)}


def material_maintenance_apply(inputs, settings, context):
    from .artifacts import _named_observation, _verified_ancestor
    store, receipts = context.provider("filestore"), []
    plan = tuple(inputs["plan"])
    if len(plan) > _option(context, settings, "max_actions", 1000):
        raise ExecutionFailure("maintenance.action_limit")
    common = tuple(_prerequisite(item) for item in inputs.get("prerequisites", _option(context, settings, "prerequisites", ())))
    prepared = _normalize_actions(plan, _option(context, settings, "scope"), common)
    plan_identity = fingerprint(prepared)
    for action in prepared:
        operation = action["operation"]
        methods = ("inspect_file", "stage_write") if operation == "copy" else (
            "guard_directory", "inspect_file", "rename_expected" if operation == "move" else "remove_expected")
        if operation == "copy" and action["policy"] == "replace_if_matches":
            methods += ("guard_directory",)
        if not all(callable(getattr(store, name, None)) for name in methods):
            raise ExecutionFailure("maintenance.conditional_provider_required")
    if getattr(context, "budget", None):
        context.budget.charge("objects", len(prepared))
    outcomes, completed, verified, cancelled = [], {}, {}, False
    for ordinal, action in enumerate(prepared):
        blocked_by = tuple(key for key in action["depends_on"] if completed[key] != "succeeded")
        receipt = None
        if cancelled:
            report = _outcome(action, ordinal, "cancelled", findings=("maintenance.cancelled",))
        elif blocked_by:
            report = _outcome(action, ordinal, "blocked", blocked_by=blocked_by,
                findings=("maintenance.dependency_unsatisfied",))
        else:
            try:
                context.checkpoint()
                source, operation, destination, expected = (action[key] for key in (
                    "source", "operation", "destination", "expected_identity"))
                prerequisites = action["prerequisites"]
                if _option(context, settings, "require_preservation", False) and not prerequisites:
                    raise ExecutionFailure("maintenance.preservation_prerequisite_required")
                key = fingerprint(prerequisites)
                if key not in verified:
                    verified[key] = _verify_prerequisites(prerequisites, context)
                if _option(context, settings, "preserve_sources", False) and expected not in verified[key]:
                    raise ExecutionFailure("maintenance.source_not_preserved")
                ancestor = action["retained_ancestor"]
                if ancestor is not None:
                    _verified_ancestor(ancestor, expected, context)
                intent = NamedEffectIntent(operation, _provider_scope(store, destination), destination,
                    expected if operation in {"copy", "move"} else None, source, expected,
                    expected_destination=action["expected_destination"], policy=action["policy"], retained_ancestor=ancestor,
                    source_provider_scope=_provider_scope(store, source),
                    expected_destination_revision=action["expected_destination_revision"], prerequisites=prerequisites)
                effect_id = fingerprint(("maintenance", action["plan_identity"] or plan_identity, action["action_id"], intent))
                if operation == "copy" and getattr(context, "budget", None):
                    context.budget.account_output(effect_id, expected)
                receipt = context.effect("storage.write", effect_id,
                    lambda intent=intent, effect_id=effect_id: _perform(intent, effect_id, context),
                    reconcile=lambda previous: _named_observation(previous.effect_id, previous.intent, context),
                    resource=destination if operation == "copy" else source, intent=intent)
                receipts.append(receipt)
                if receipt.status != "confirmed":
                    report = _outcome(action, ordinal, "unknown" if receipt.status == "unknown" else "failed",
                        receipt=receipt, findings=tuple(dict.fromkeys(("maintenance." + receipt.status,
                            *( (receipt.finding,) if receipt.finding else () )))))
                elif _named_observation(effect_id, receipt.intent, context) is None:
                    report = _outcome(action, ordinal, "failed", receipt=receipt,
                        findings=("maintenance.postcondition_changed",))
                else:
                    report = _outcome(action, ordinal, "succeeded", receipt=receipt)
            except Exception as error:
                cancelled = getattr(error, "outcome", None) == "cancelled"
                report = _outcome(action, ordinal, "cancelled" if cancelled else "failed",
                    receipt=receipt, findings=(error_code(error),))
        outcomes.append(report)
        completed[action["action_id"]] = report["outcome"]
    states = set(completed.values())
    outcome = "unknown" if "unknown" in states else "cancelled" if cancelled else (
        "succeeded" if states <= {"succeeded"} else "partial" if "succeeded" in states else "failed")
    findings = tuple(dict.fromkeys(finding for report in outcomes for finding in report["findings"]))
    return CommandCompletion({"receipts": tuple(receipts), "outcomes": tuple(outcomes)}, outcome=outcome, findings=findings)
