from dataclasses import replace
from collections import Counter, defaultdict
import csv
import json
from io import StringIO

from stratbox.data import Comparison, ComparisonCoverage, ComparisonLayers, UsedInputReceipt, compare_releases
from stratbox.data.releases import CompareReleaseRequest, ParsedRelease

from .contracts import OperationFailure
from .runner import Invocation


def compare_release_inputs(
    request: CompareReleaseRequest,
    invocation: Invocation,
    dataset: str,
    profile: str,
) -> Comparison | None:
    invocation.stage("compare")

    def compatible(value: ParsedRelease) -> bool:
        return (
            isinstance(value, ParsedRelease)
            and value.dataset_version.dataset_id == dataset
            and value.dataset_version.release_id == value.as_of.isoformat()
            and value.representation.profile_id == profile
            and value.representation.version == 1
        )

    def use(value: ParsedRelease, role: str) -> None:
        representation = value.representation
        invocation.budget.charge("input_bytes", representation.identity.size)
        invocation.use(
            UsedInputReceipt(
                role, representation.identity, representation.media_type, "inline",
                source_id=dataset, version=value.dataset_version.identity,
            )
        )

    if not compatible(request.candidate):
        raise OperationFailure("comparison.candidate_incompatible")
    use(request.candidate, "candidate_representation")
    if request.baseline is not None and request.baseline_state == "available":
        if not compatible(request.baseline):
            return Comparison("indeterminate", "baseline.incompatible")
        use(request.baseline, "baseline_representation")
    return compare_releases(
        request.baseline.as_of if request.baseline is not None and request.baseline_state == "available" else None,
        request.candidate.as_of,
        request.baseline_state,
    )


def _layer(old, new):
    if old is None or new is None:
        return "unavailable"
    return "same" if old == new else "changed"


def _method(value):
    manifest = json.loads(value.dataset_version.manifest)
    return (value.facts_method or value.dataset_version.method_version,
            manifest["resources"], manifest["parameters"].get("epoch"))


def _header(value):
    try:
        stream = StringIO(value.representation.data.decode("utf-8"), newline="")
        return next(csv.reader(stream, strict=True), None)
    except (UnicodeError, csv.Error):
        return None


def _original(value):
    if value.acquisition is not None:
        return (value.acquisition.identity,)
    return tuple(item.identity for item in value.inputs if item.role.startswith("source_")) or None


def _observations(value):
    groups = defaultdict(Counter)
    for item in value.batch.observations if value.batch is not None else ():
        key = item.subject, item.metric, item.period, tuple(sorted(item.dimensions)), item.perimeter
        groups[key][(item.value_status, item.value)] += 1
    return groups


def explain_comparison(result, request, invocation):
    old, new = request.baseline, request.candidate
    if old is None or request.baseline_state != "available":
        return result
    if result.reason == "baseline.incompatible":
        return replace(result, layers=ComparisonLayers(facts="incompatible"))
    method = _layer(_method(old), _method(new))
    representations = _layer(old.representation.identity, new.representation.identity)
    facts = _layer(old.facts_identity, new.facts_identity)
    before, after = _observations(old), _observations(new)
    common = before.keys() & after.keys()
    changed = {key[0].id for key in common if before[key] != after[key]}
    scope = old.qualification.scope if old.qualification and new.qualification and (
        old.qualification.scope == new.qualification.scope
    ) else "intersection"
    before_counts = {key: sum(values.values()) for key, values in before.items()}
    after_counts = {key: sum(values.values()) for key, values in after.items()}
    coverage = ComparisonCoverage(
        sum(min(before_counts[key], after_counts[key]) for key in common),
        sum(before_counts.values()), sum(after_counts.values()), len({key[0] for key in common}), scope,
    )
    if old.as_of == new.as_of:
        if method == "changed":
            result = Comparison("indeterminate", "comparison.method_changed")
            facts = "incompatible"
        elif scope == "intersection" or (scope == "selected_fragment" and before.keys() != after.keys()):
            result = Comparison("indeterminate", "comparison.scope_changed")
            facts = "incompatible"
        elif facts != "unavailable" and before and after and not common:
            facts = "incompatible"
            if result.state != "indeterminate":
                result = Comparison("indeterminate", "comparison.observation_scope_changed")
        elif before and after and any(count > after_counts.get(key, 0) for key, count in before_counts.items()):
            facts = "incompatible"
            if result.state != "indeterminate":
                result = Comparison("indeterminate", "comparison.coverage_dropped")
        elif result.state == "unchanged" and facts == "unavailable":
            result = Comparison("indeterminate", "comparison.qualification_missing")
    invocation.check_cancelled()
    return replace(result, layers=ComparisonLayers(
        _layer(_original(old), _original(new)), _layer(_header(old), _header(new)), facts, method, representations,
    ), coverage=coverage, changed_subjects=result.changed_subjects or tuple(sorted(changed)))
