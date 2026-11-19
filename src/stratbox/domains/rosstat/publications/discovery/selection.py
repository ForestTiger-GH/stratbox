"""Selection and index diffs are pure and make no network/storage effects."""

from __future__ import annotations

from ..contracts import DiscoveredAsset, PublicationIndexDelta, RosstatPublicationIndex


def _assets(index: RosstatPublicationIndex) -> dict[str, DiscoveredAsset]:
    return {item.key.source_id: item for item in index.qualified_assets if item.key}


def compare_publication_indices(
    before: RosstatPublicationIndex, after: RosstatPublicationIndex,
) -> PublicationIndexDelta:
    if before.series_id != after.series_id:
        raise ValueError("rosstat.index_series_mismatch")
    if before.coverage != "complete" or after.coverage != "complete":
        return PublicationIndexDelta("indeterminate", (), (), (), "rosstat.index_coverage_incomplete")
    old, new = _assets(before), _assets(after)
    added = tuple(sorted(new.keys() - old.keys()))
    missing = tuple(sorted(old.keys() - new.keys()))
    relocated = tuple(sorted(
        key for key in old.keys() & new.keys() if old[key].url != new[key].url
    ))
    return PublicationIndexDelta(
        "changed" if added or missing or relocated else "unchanged",
        added, missing, relocated,
        "rosstat.index_changed" if added or missing or relocated else "rosstat.index_equivalent",
    )


def select_assets(
    index: RosstatPublicationIndex, *,
    issue_ids: tuple[str, ...] = (),
    asset_roles: tuple[str, ...] = ("primary",),
    policy: str = "explicit",
    max_assets: int = 20,
) -> tuple[DiscoveredAsset, ...]:
    if policy not in {"explicit", "latest_qualified", "all_qualified"}:
        raise ValueError("rosstat.selection_policy_invalid")
    if not 1 <= max_assets <= 100 or not asset_roles:
        raise ValueError("rosstat.selection_limit_invalid")
    selected = tuple(
        item for item in index.qualified_assets
        if item.asset_role in asset_roles and (not issue_ids or item.key.issue.issue_id in issue_ids)
    )
    if policy == "explicit" and not issue_ids:
        raise ValueError("rosstat.selection_issue_required")
    if policy == "latest_qualified":
        if index.coverage != "complete" or not selected:
            raise ValueError("rosstat.selection_order_unqualified")
        latest = max(item.key.issue.issue_id for item in selected)
        selected = tuple(item for item in selected if item.key.issue.issue_id == latest)
    if len(selected) > max_assets:
        raise ValueError("rosstat.selection_limit_exceeded")
    return selected
