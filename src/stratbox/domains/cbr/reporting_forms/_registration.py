"""Published operation references for cbr_forms."""

from stratbox.core.execution.catalog import OperationRegistration, OperationRef

REGISTRATION = OperationRegistration(
    owner_id="cbr.reporting_forms",
    operations=(
        OperationRef("cbr.forms.select_sources", 1, "stratbox.domains.cbr.reporting_forms.operations:SELECT", "stratbox.domains.cbr.reporting_forms.operations:select_sources"),
        OperationRef("cbr.forms.acquire", 1, "stratbox.domains.cbr.reporting_forms.operations:ACQUIRE", "stratbox.domains.cbr.reporting_forms.operations:acquire"),
        OperationRef("cbr.forms.parse", 2, "stratbox.domains.cbr.reporting_forms.operations:PARSE", "stratbox.domains.cbr.reporting_forms.operations:parse_form"),
        OperationRef("cbr.forms.build_data", 2, "stratbox.domains.cbr.reporting_forms.operations:BUILD", "stratbox.domains.cbr.reporting_forms.operations:build_form_data"),
        OperationRef("cbr.forms.build_views", 2, "stratbox.domains.cbr.reporting_forms.operations:VIEWS", "stratbox.domains.cbr.reporting_forms.operations:build_form_views"),
        OperationRef("cbr.forms.render_workbook", 2, "stratbox.domains.cbr.reporting_forms.operations:RENDER", "stratbox.domains.cbr.reporting_forms.operations:render_workbook"),
    ),
)
