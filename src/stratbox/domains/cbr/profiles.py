"""Scientific admission delegates to the CBR owners of each source value."""
from stratbox.domains.registry.requirements import DomainAdmission


def form_layout(profile_id):
    from .tables.reporting_forms.layouts.registry import LAYOUT_REGISTRY
    import re
    match = re.search(r"(?:f|model\.)(\d{3})", profile_id)
    if match is None or match[1] not in LAYOUT_REGISTRY:
        raise ValueError("cbr.profile.layout_unreviewed")
    return LAYOUT_REGISTRY[match[1]]


def admit(requirement, instance, value):
    from .tables.statistics.contracts import WorkbookFlake
    from .tables.statistics.validation import validate_workbook_flake
    from .tables.statistics.profiles import table_profile
    from .tables.reporting_forms.contracts import FormFlakes
    from .tables.reporting_forms.flakes import validate_flakes
    from stratbox.shared.data.observations import ObservationBatch
    from stratbox.shared.data.observation_snapshots import observation_snapshot
    try:
        if isinstance(value, WorkbookFlake):
            if value.series_id != instance.source_id or instance.issue_id and value.issue_id != instance.issue_id:
                return DomainAdmission("rejected", ("cbr.profile.source_context_mismatch",))
            validation = validate_workbook_flake(value)
            if validation.diagnostics:
                return DomainAdmission("conditional", tuple(dict.fromkeys(item.code for item in validation.diagnostics)))
            profile = table_profile(value.profile_id)
            if instance.layout_edition and instance.layout_edition not in {profile.edition, str(profile.version)}:
                return DomainAdmission("rejected", ("cbr.profile.layout_edition_mismatch",))
            if instance.semantic_profile_edition and instance.semantic_profile_edition not in {
                    str(profile.version), profile.profile_id + ":" + str(profile.version)}:
                return DomainAdmission("rejected", ("cbr.profile.semantic_edition_mismatch",))
            if instance.report_date or instance.perimeter:
                return DomainAdmission("conditional", ("cbr.profile.economic_mapping_required",))
            return DomainAdmission("admitted", ("cbr.profile.reviewed_source_layout",))
        if isinstance(value, FormFlakes):
            validate_flakes(value)
            if instance.source_id != "cbr.reporting_forms.f" + value.key.code:
                return DomainAdmission("rejected", ("cbr.profile.source_context_mismatch",))
            if instance.report_date and value.key.as_of.isoformat() != instance.report_date:
                return DomainAdmission("rejected", ("cbr.profile.reporting_date_mismatch",))
            if instance.layout_edition or instance.semantic_profile_edition or instance.perimeter:
                return DomainAdmission("conditional", ("cbr.profile.normalized_form_semantics_required",))
            return DomainAdmission("admitted", ("cbr.profile.source_records_only",))
        if isinstance(value, ObservationBatch):
            observation_snapshot(value)
            matches = [use for use in value.source_uses if use.coordinate.source_id == instance.source_id
                       and (instance.group_id is None or use.coordinate.source_group_id == instance.group_id)
                       and (instance.issue_id is None or use.coordinate.issue_id == instance.issue_id)]
            if matches:
                for name in ("layout_edition", "semantic_profile_edition"):
                    claimed = getattr(instance, name)
                    actual = {getattr(use.coordinate, name) for use in matches}
                    if claimed and (not actual or actual == {None}):
                        return DomainAdmission("conditional", ("cbr.profile.edition_evidence_required",))
                    if claimed and actual != {claimed}:
                        return DomainAdmission("rejected", ("cbr.profile.edition_mismatch",))
                if instance.perimeter and {item.perimeter for item in value.observations} != {instance.perimeter}:
                    return DomainAdmission("rejected", ("cbr.profile.perimeter_mismatch",))
                if instance.report_date:
                    dates = {(item.period.as_of or item.period.end).isoformat() for item in value.observations}
                    if len(dates) != 1:
                        return DomainAdmission("conditional", ("cbr.profile.unique_economic_period_required",))
                    if dates != {instance.report_date}:
                        return DomainAdmission("rejected", ("cbr.profile.economic_period_mismatch",))
            return DomainAdmission("admitted" if matches else "rejected",
                ("cbr.profile.explicit_observation_scope" if matches else "cbr.profile.source_context_mismatch",))
    except (TypeError, ValueError) as error:
        return DomainAdmission("rejected", (str(error).split(":", 1)[0],))
    return DomainAdmission("conditional", ("cbr.profile.typed_source_admission_required",))
