"""Published operation references for cbr_forms."""

from stratbox.system.execution.registry import DomainRegistration, OperationRef

REGISTRATION = DomainRegistration(
    domain_id="cbr_forms",
    operations=(
        OperationRef("cbr.forms.select_sources", 1, "stratbox.domains.cbr_forms.operations:SELECT", "stratbox.domains.cbr_forms.operations:select_sources"),
        OperationRef("cbr.forms.acquire", 1, "stratbox.domains.cbr_forms.operations:ACQUIRE", "stratbox.domains.cbr_forms.operations:acquire"),
        OperationRef("cbr.forms.parse", 2, "stratbox.domains.cbr_forms.operations:PARSE", "stratbox.domains.cbr_forms.operations:parse_form"),
        OperationRef("cbr.forms.build_data", 2, "stratbox.domains.cbr_forms.operations:BUILD", "stratbox.domains.cbr_forms.operations:build_form_data"),
        OperationRef("cbr.forms.build_views", 2, "stratbox.domains.cbr_forms.operations:VIEWS", "stratbox.domains.cbr_forms.operations:build_form_views"),
        OperationRef("cbr.forms.render_workbook", 2, "stratbox.domains.cbr_forms.operations:RENDER", "stratbox.domains.cbr_forms.operations:render_workbook"),
    ),
)
