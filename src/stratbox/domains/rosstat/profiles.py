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
    supported = {KEP2_PROFILE_ID: "rosstat.short_term_indicators",
        "rosstat.population.bulletin": "rosstat.population_municipalities",
        "rosstat.regional.industrial_indices": "rosstat.socioeconomic_regions"}
    if value.profile_id not in supported or value.profile_version != 1:
        return DomainAdmission("conditional", ("rosstat.profile.external_mapping_admission_required",))
    if value.series_id != supported[value.profile_id]:
        return DomainAdmission("rejected", ("rosstat.profile.family_mismatch",))
    if value.profile_id == "rosstat.population.bulletin" and any(
            row.period_kind != "as_of" or row.quantity_kind != "count" or not dict(row.dimensions).get("geography_edition")
            for row in value.values):
        return DomainAdmission("rejected", ("rosstat.profile.population_semantics_invalid",))
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
    return DomainAdmission("admitted", ("rosstat.profile.reviewed_kep2_periods_and_units" if value.profile_id == KEP2_PROFILE_ID
        else "rosstat.profile.reviewed_population_layout" if value.profile_id == "rosstat.population.bulletin"
        else "rosstat.profile.reviewed_regional_index_layout",))
