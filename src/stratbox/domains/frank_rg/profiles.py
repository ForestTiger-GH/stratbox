"""Physical workbook delivery never substitutes for byte-bound semantic review."""
from stratbox.domains.registry.requirements import DomainAdmission


def admit(requirement, instance, value):
    from .tables.contracts import SemanticFlake
    from .tables.snapshots import validate_flake, flake_snapshot
    if not isinstance(value, SemanticFlake):
        return DomainAdmission("conditional", ("frg.profile.byte_bound_semantics_required",))
    try:
        validate_flake(value)
        if value.series_id != instance.source_id or instance.issue_id and value.issue_id != instance.issue_id:
            return DomainAdmission("rejected", ("frg.profile.source_context_mismatch",))
        if (instance.material_identity is not None and instance.material_identity != value.original_identity
                and instance.material_identity != flake_snapshot(value).identity):
            return DomainAdmission("rejected", ("frg.profile.original_binding_mismatch",))
        if instance.source_material_identity is not None and instance.source_material_identity != value.original_identity:
            return DomainAdmission("rejected", ("frg.profile.original_binding_mismatch",))
        if instance.consumed_identity is not None and instance.consumed_identity != flake_snapshot(value).identity:
            return DomainAdmission("rejected", ("frg.profile.consumed_identity_mismatch",))
        if instance.semantic_profile_edition and instance.semantic_profile_edition not in {
                str(value.profile_version), value.profile_id + ":" + str(value.profile_version)}:
            return DomainAdmission("rejected", ("frg.profile.semantic_edition_mismatch",))
        if instance.profile_id and instance.profile_id != value.profile_id:
            return DomainAdmission("rejected", ("frg.profile.semantic_profile_mismatch",))
        if instance.layout_edition:
            return DomainAdmission("conditional", ("frg.profile.physical_layout_evidence_required",))
        if instance.report_date:
            dates = {(item.period.as_of or item.period.end).isoformat() for item in value.batch.observations}
            if len(dates) != 1:
                return DomainAdmission("conditional", ("frg.profile.unique_economic_period_required",))
            if dates != {instance.report_date}:
                return DomainAdmission("rejected", ("frg.profile.economic_period_mismatch",))
        if instance.perimeter and {item.perimeter for item in value.batch.observations} != {instance.perimeter}:
            return DomainAdmission("rejected", ("frg.profile.perimeter_mismatch",))
    except (TypeError, ValueError) as error:
        return DomainAdmission("rejected", (str(error),))
    return DomainAdmission("admitted", ("frg.profile.byte_bound_source_cells",))
