"""FRG cleanup planning. Filesystem commands are supplied by the store."""

from dataclasses import dataclass
from typing import Literal

from stratbox.base.filestore import FileVersion
from stratbox.base.filestore.paths import child_path
from stratbox.base.ioapi.bytes import inspect_file_version
from stratbox.data import ByteIdentity, canonical_manifest_bytes
from stratbox.execution import OperationFailure

from .filename_scheme import build_internal_file_name

Action = Literal["keep", "copy", "rename", "remove"]


@dataclass(frozen=True, slots=True)
class CleanupAction:
    kind: Action
    source: FileVersion
    destination: str | None = None


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


def _should_remove(row, latest_paths):
    return (
        row["path"] not in latest_paths
        and row["is_recognized"]
        and (
            row["is_valid"]
            or row["validity_reason"]
            in {
                "period_older_than_family_min_date",
                "superseded_by_newer_week_in_same_month",
            }
        )
    )


def create_plan(request, store, invocation):
    from .catalog import build_frg_catalog
    from .selection import select_latest_frg_files

    directory_identity = store.directory_identity(request.directory)
    budget, checkpoint = invocation.budget, invocation.check_cancelled
    catalog = build_frg_catalog(request.directory, filestore=store, budget=budget, checkpoint=checkpoint)
    latest = select_latest_frg_files(catalog)
    latest_paths = set(latest["path"])
    actions = []
    destinations = set()
    for row in latest.to_dict("records"):
        invocation.check_cancelled()
        target_name = build_internal_file_name(
            period_text=row["period_date_text"],
            file_label=row["file_label"] or row["family_name"],
            extension=row["extension"],
        )
        target = child_path(request.directory, target_name)
        source = inspect_file_version(row["path"], store=store, budget=budget, checkpoint=checkpoint)
        if target.casefold() in destinations:
            raise OperationFailure("effect.destination_conflict")
        destinations.add(target.casefold())
        if target == source.path:
            kind = "keep"
        elif store.exists(target):
            raise OperationFailure("effect.destination_conflict")
        else:
            kind = "rename" if request.delete_others else "copy"
        actions.append(CleanupAction(kind, source, target))
    if request.delete_others:
        for row in catalog.to_dict("records"):
            invocation.check_cancelled()
            if _should_remove(row, latest_paths):
                source = inspect_file_version(row["path"], store=store, budget=budget, checkpoint=checkpoint)
                actions.append(CleanupAction("remove", source))
    identity = ByteIdentity.of(
        canonical_manifest_bytes(
            {
                "version": 1,
                "directory": request.directory,
                "directory_identity": directory_identity,
                "delete_others": request.delete_others,
                "actions": [
                    {
                        "kind": action.kind,
                        "source": action.source.path,
                        "destination": action.destination,
                        "revision": action.source.revision,
                        "sha256": action.source.identity.sha256,
                        "size": action.source.identity.size,
                    }
                    for action in actions
                ],
            }
        )
    )
    return CleanupPlan(request, tuple(actions), directory_identity, identity)
