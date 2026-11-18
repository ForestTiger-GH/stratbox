"""Published operation references for cbr_industries."""

from stratbox.core.execution.catalog import OperationRegistration, OperationRef

REGISTRATION = OperationRegistration(
    owner_id="cbr.corporate_lending.industries",
    operations=(
        OperationRef("cbr.industries.0105a.discover", 1, "stratbox.domains.cbr.corporate_lending.industries.operations:DISCOVER", "stratbox.domains.cbr.corporate_lending.industries.operations:discover"),
        OperationRef("cbr.industries.0105a.acquire", 1, "stratbox.domains.cbr.corporate_lending.industries.operations:ACQUIRE", "stratbox.domains.cbr.corporate_lending.industries.operations:acquire"),
        OperationRef("cbr.industries.0105a.parse", 3, "stratbox.domains.cbr.corporate_lending.industries.operations:PARSE", "stratbox.domains.cbr.corporate_lending.industries.operations:parse"),
        OperationRef("cbr.industries.0105a.build_stream", 3, "stratbox.domains.cbr.corporate_lending.industries.operations:BUILD_STREAM", "stratbox.domains.cbr.corporate_lending.industries.operations:build_stream"),
        OperationRef("cbr.industries.0105a.calculate_apk", 2, "stratbox.domains.cbr.corporate_lending.industries.operations:CALCULATE_APK", "stratbox.domains.cbr.corporate_lending.industries.operations:calculate_apk"),
        OperationRef("cbr.industries.0105a.build_pivots", 2, "stratbox.domains.cbr.corporate_lending.industries.operations:PIVOT", "stratbox.domains.cbr.corporate_lending.industries.operations:build_pivots"),
        OperationRef("cbr.industries.0105a.render_pivots", 2, "stratbox.domains.cbr.corporate_lending.industries.operations:RENDER_PIVOTS", "stratbox.domains.cbr.corporate_lending.industries.operations:render_pivots"),
        OperationRef("cbr.industries.0105a.render_industry", 2, "stratbox.domains.cbr.corporate_lending.industries.operations:RENDER_INDUSTRY", "stratbox.domains.cbr.corporate_lending.industries.operations:render_industry"),
        OperationRef("cbr.industries.0105a.render_industries", 1, "stratbox.domains.cbr.corporate_lending.industries.operations:RENDER_INDUSTRIES", "stratbox.domains.cbr.corporate_lending.industries.operations:render_industries"),
    ),
)
