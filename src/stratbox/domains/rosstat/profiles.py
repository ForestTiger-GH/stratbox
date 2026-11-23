"""Reviewed Rosstat interpretation is distinct from physical document reading."""
from stratbox.domains.registry.requirements import DomainAdmission


def admit(requirement, instance, value):
    from .tables.contracts import RosstatSourceFlake
    from .tables.profiles import KEP2_PROFILE_ID
    from .integration.datasets import integrate_flakes
    if not isinstance(value, RosstatSourceFlake):
        return DomainAdmission("conditional", ("rosstat.profile.reviewed_mapping_required",))
    if value.series_id != instance.source_id or instance.issue_id and value.issue_id != instance.issue_id:
        return DomainAdmission("rejected", ("rosstat.profile.source_context_mismatch",))
    if value.profile_id != KEP2_PROFILE_ID or value.profile_version != 1:
        return DomainAdmission("conditional", ("rosstat.profile.external_mapping_admission_required",))
    if instance.semantic_profile_edition and instance.semantic_profile_edition not in {
            str(value.profile_version), value.profile_id + ":" + str(value.profile_version)}:
        return DomainAdmission("rejected", ("rosstat.profile.semantic_edition_mismatch",))
    if instance.report_date or instance.layout_edition:
        return DomainAdmission("conditional", ("rosstat.profile.publication_layout_evidence_required",))
    if instance.perimeter and {item.perimeter for item in value.values} != {instance.perimeter}:
        return DomainAdmission("rejected", ("rosstat.profile.perimeter_mismatch",))
    try:
        value.__post_init__()
        integrate_flakes((value,), dataset_id="rosstat.profile_admission", release_id=value.issue_id)
    except (TypeError, ValueError) as error:
        return DomainAdmission("rejected", (str(error),))
    return DomainAdmission("admitted", ("rosstat.profile.reviewed_kep2_periods_and_units",))
