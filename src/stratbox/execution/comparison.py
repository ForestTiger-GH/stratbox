from stratbox.data import Comparison, SourcePayload, UsedInputReceipt, compare_releases
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
            UsedInputReceipt.for_payload(
                SourcePayload(
                    representation.data,
                    representation.media_type,
                    expected_sha256=representation.identity.sha256,
                ),
                role,
            )
        )

    if not compatible(request.candidate):
        raise OperationFailure("comparison.candidate_incompatible")
    use(request.candidate, "candidate_representation")
    if request.baseline is not None:
        if not compatible(request.baseline):
            return Comparison("indeterminate", "baseline.incompatible")
        use(request.baseline, "baseline_representation")
    return compare_releases(
        request.baseline.as_of if request.baseline else None,
        request.candidate.as_of,
        request.baseline_state,
    )
