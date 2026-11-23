"""Fiscal source admission preserves source-specific period and value basis."""
from stratbox.core.registry.requirements import DomainAdmission


def admit(requirement, instance, value):
    from .tables.contracts import FlakeTable
    from .tables.flake_codec import validate_flake
    from .publications.catalog import family
    from .integration.observations import economic_period, reviewed_bindings
    if not isinstance(value, FlakeTable):
        return DomainAdmission("conditional", ("minfin.profile.interpreted_table_required",))
    try:
        validate_flake(value)
        specification = family(value.family_id).source(value.source_id)
        if (value.source_id != instance.source_id or value.frequency != specification.periodicity
                or value.value_basis != specification.basis or specification.kind != "table"):
            return DomainAdmission("rejected", ("minfin.profile.period_basis_mismatch",))
        if instance.issue_id and (value.publication is None or value.publication.issue_id != instance.issue_id):
            return DomainAdmission("rejected", ("minfin.profile.source_context_mismatch",))
        if instance.semantic_profile_edition and instance.semantic_profile_edition != value.method_version:
            return DomainAdmission("rejected", ("minfin.profile.semantic_edition_mismatch",))
        if instance.layout_edition:
            return DomainAdmission("conditional", ("minfin.profile.layout_edition_evidence_required",))
        if instance.report_date:
            period = economic_period(value.latest_period, value.frequency, value.value_basis)
            if (period.as_of or period.end).isoformat() != instance.report_date:
                return DomainAdmission("rejected", ("minfin.profile.economic_period_mismatch",))
        if instance.perimeter:
            try:
                perimeters = {binding.perimeter for binding in reviewed_bindings(value)}
            except ValueError:
                return DomainAdmission("conditional", ("minfin.profile.perimeter_mapping_required",))
            if perimeters != {instance.perimeter}:
                return DomainAdmission("rejected", ("minfin.profile.perimeter_mismatch",))
    except (TypeError, ValueError, KeyError) as error:
        return DomainAdmission("rejected", (str(error),))
    return DomainAdmission("admitted", ("minfin.profile.fiscal_basis_preserved",))
