"""Plan report file effects using logical sources and bound naming profiles."""

from dataclasses import dataclass
from typing import Literal

from stratbox.core.execution import OperationFailure
from stratbox.core.storage.bytes import inspect_file_version
from stratbox.core.storage.filestore import FileVersion
from stratbox.core.storage.filestore.paths import child_path
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes

from .contracts import Asset, DiscoveryRequest


Action = Literal["keep", "copy", "rename", "remove"]


@dataclass(frozen=True, slots=True)
class CleanupAction:
    kind: Action
    source: FileVersion
    destination: str | None = None
    source_id: str | None = None


@dataclass(frozen=True, slots=True)
class PlanCleanupRequest:
    directory: str
    delete_others: bool = False


@dataclass(frozen=True, slots=True)
class CleanupPlan:
    request: PlanCleanupRequest
    actions: tuple[CleanupAction, ...]
    directory_identity: str
    identity: ByteIdentity


@dataclass(frozen=True, slots=True)
class ApplyCleanupRequest:
    plan: CleanupPlan
    authorized_directory: str
    expected_sha256: str


@dataclass(frozen=True, slots=True)
class CleanupReceipt:
    action: CleanupAction
    state: Literal["confirmed", "failed", "unknown", "not_attempted"]
    diagnostic: str | None = None


def _profile_versions(bound_families) -> dict:
    return {
        item.source.family_id: {
            role: {
                "profile_id": getattr(item, role).profile_id,
                "method_version": getattr(item, role).method_version,
            }
            for role in ("discovery", "identification", "selection", "naming")
        }
        for item in bound_families
    }


def _plan_identity(request, actions, directory_identity, profile_versions) -> ByteIdentity:
    return ByteIdentity.of(canonical_manifest_bytes({
        "version": 2,
        "directory": request.directory,
        "directory_identity": directory_identity,
        "delete_others": request.delete_others,
        "profiles": profile_versions,
        "actions": [
            {
                "kind": action.kind,
                "source_id": action.source_id,
                "source": action.source.path,
                "destination": action.destination,
                "revision": action.source.revision,
                "sha256": action.source.identity.sha256,
                "size": action.source.identity.size,
            }
            for action in actions
        ],
    }))


def validate_plan(plan: CleanupPlan, *, bound_families: tuple, bound_sources: dict) -> None:
    """Check plan integrity and shallow directory scope without reading files."""

    def invalid():
        raise OperationFailure("effect.plan_invalid")

    if (
        not isinstance(plan, CleanupPlan)
        or not isinstance(plan.request, PlanCleanupRequest)
        or not isinstance(plan.request.directory, str)
        or not plan.request.directory
        or "\x00" in plan.request.directory
        or type(plan.request.delete_others) is not bool
        or not isinstance(plan.actions, tuple)
        or not isinstance(plan.directory_identity, str)
        or not plan.directory_identity
        or not isinstance(plan.identity, ByteIdentity)
    ):
        invalid()
    sources, destinations = set(), set()
    for action in plan.actions:
        if (
            not isinstance(action, CleanupAction)
            or not isinstance(action.kind, str)
            or action.kind not in {"keep", "copy", "rename", "remove"}
            or not isinstance(action.source, FileVersion)
            or not isinstance(action.source.path, str)
            or not action.source.path
            or not isinstance(action.source.identity, ByteIdentity)
            or not isinstance(action.source.revision, str)
            or not action.source.revision
            or not isinstance(action.source_id, str)
        ):
            invalid()
        try:
            bound_sources[action.source_id]
        except (ValueError, KeyError):
            invalid()
        for path in (action.source.path, action.destination):
            if path is None and action.kind == "remove":
                continue
            if not isinstance(path, str):
                invalid()
            normalized = path.replace("\\", "/")
            try:
                if normalized != child_path(plan.request.directory, normalized.rsplit("/", 1)[-1]):
                    invalid()
            except ValueError:
                invalid()
        if action.source.path in sources:
            invalid()
        sources.add(action.source.path)
        if action.kind == "remove":
            if action.destination is not None or not plan.request.delete_others:
                invalid()
            continue
        if action.destination.casefold() in destinations:
            invalid()
        destinations.add(action.destination.casefold())
        if action.kind == "keep" and action.source.path != action.destination:
            invalid()
        if action.kind in {"copy", "rename"} and action.source.path == action.destination:
            invalid()
        if (action.kind == "copy" and plan.request.delete_others) or (
            action.kind == "rename" and not plan.request.delete_others
        ):
            invalid()
    if plan.identity != _plan_identity(
        plan.request, plan.actions, plan.directory_identity, _profile_versions(bound_families),
    ):
        invalid()


def _should_remove(asset: Asset, latest_paths: set[str]) -> bool:
    return (
        asset.entry.path not in latest_paths
        and asset.recognition in {"supplier", "canonical"}
        and asset.source_id is not None
        and (
            asset.valid
            or asset.diagnostic == "frg.file.period_before_minimum"
        )
    )


def create_plan(request: PlanCleanupRequest, store, invocation, *, bound_families: tuple, bound_sources: dict) -> CleanupPlan:
    """Read and qualify inputs; the caller must separately apply the proposal."""
    from .naming import build_internal_file_name, identify_index

    if type(request.delete_others) is not bool:
        raise OperationFailure("frg.cleanup.invalid_delete_flag")
    directory_identity = store.directory_identity(request.directory)
    discovery = bound_families[0].discovery
    if any(item.discovery != discovery for item in bound_families):
        raise OperationFailure("frg.profile.discovery_incompatible")
    index = discovery.discover(DiscoveryRequest(request.directory), store, invocation)
    inventory = identify_index(
        index,
        sources=tuple((item.source, item.identification) for item in bound_families),
    )
    selections = tuple(
        selection
        for item in bound_families
        for selection in item.selection.select(
            inventory, source_ids=tuple(series.source_id for series in item.source.series),
        )
    )
    versions: dict[str, FileVersion] = {}

    def inspect(asset: Asset) -> FileVersion:
        path = asset.entry.path
        if path not in versions:
            versions[path] = inspect_file_version(
                path, store=store, budget=invocation.budget,
                checkpoint=invocation.check_cancelled,
            )
        return versions[path]

    latest = []
    for selection in selections:
        if selection.state == "missing":
            continue
        if selection.state == "selected":
            latest.append(selection.asset)
            continue
        candidates = selection.candidates
        if not candidates or len({item.format for item in candidates}) != 1:
            raise OperationFailure("frg.selection.ambiguous")
        if len({inspect(item).identity for item in candidates}) != 1:
            raise OperationFailure("frg.selection.ambiguous")
        bound = bound_sources[selection.source_id]
        canonical = child_path(request.directory, build_internal_file_name(
            candidates[0].period, bound.rule, format=candidates[0].format,
            profile=bound.parent.naming,
        ))
        # A canonical filename wins only after every candidate has the same
        # exact byte identity. This keeps copy mode safely repeatable.
        latest.append(min(
            candidates,
            key=lambda item: (item.entry.path != canonical, item.entry.path),
        ))
    latest_paths = {item.entry.path for item in latest}
    actions = []
    destinations = set()
    for asset in latest:
        invocation.check_cancelled()
        bound = bound_sources[asset.source_id]
        target_name = build_internal_file_name(
            asset.period, bound.rule, format=asset.format, profile=bound.parent.naming,
        )
        target = child_path(request.directory, target_name)
        source = inspect(asset)
        if target.casefold() in destinations:
            raise OperationFailure("effect.destination_conflict")
        destinations.add(target.casefold())
        if target == source.path:
            kind = "keep"
        elif store.exists(target):
            raise OperationFailure("effect.destination_conflict")
        else:
            kind = "rename" if request.delete_others else "copy"
        actions.append(CleanupAction(kind, source, target, asset.source_id))
    if request.delete_others:
        for asset in inventory.assets:
            invocation.check_cancelled()
            if _should_remove(asset, latest_paths):
                source = inspect(asset)
                actions.append(CleanupAction("remove", source, source_id=asset.source_id))
    identity = _plan_identity(request, actions, directory_identity, _profile_versions(bound_families))
    return CleanupPlan(request, tuple(actions), directory_identity, identity)
