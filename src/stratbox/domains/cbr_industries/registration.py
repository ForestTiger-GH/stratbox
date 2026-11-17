"""Published operation references for cbr_industries."""

from stratbox.core.execution.catalog import OperationRegistration, OperationRef

REGISTRATION = OperationRegistration(
    owner_id="cbr_industries",
    operations=(
        OperationRef("cbr.industries.0105a.discover", 1, "stratbox.domains.cbr_industries.operations:DISCOVER", "stratbox.domains.cbr_industries.operations:discover"),
        OperationRef("cbr.industries.0105a.acquire", 1, "stratbox.domains.cbr_industries.operations:ACQUIRE", "stratbox.domains.cbr_industries.operations:acquire"),
        OperationRef("cbr.industries.0105a.parse", 3, "stratbox.domains.cbr_industries.operations:PARSE", "stratbox.domains.cbr_industries.operations:parse"),
        OperationRef("cbr.industries.0105a.build_stream", 3, "stratbox.domains.cbr_industries.operations:BUILD_STREAM", "stratbox.domains.cbr_industries.operations:build_stream"),
        OperationRef("cbr.industries.0105a.calculate_apk", 2, "stratbox.domains.cbr_industries.operations:CALCULATE_APK", "stratbox.domains.cbr_industries.operations:calculate_apk"),
        OperationRef("cbr.industries.0105a.build_pivots", 2, "stratbox.domains.cbr_industries.operations:PIVOT", "stratbox.domains.cbr_industries.operations:build_pivots"),
        OperationRef("cbr.industries.0105a.render_pivots", 2, "stratbox.domains.cbr_industries.operations:RENDER_PIVOTS", "stratbox.domains.cbr_industries.operations:render_pivots"),
        OperationRef("cbr.industries.0105a.render_industry", 2, "stratbox.domains.cbr_industries.operations:RENDER_INDUSTRY", "stratbox.domains.cbr_industries.operations:render_industry"),
        OperationRef("cbr.industries.0105a.render_industries", 1, "stratbox.domains.cbr_industries.operations:RENDER_INDUSTRIES", "stratbox.domains.cbr_industries.operations:render_industries"),
        OperationRef("cbr.industries.0104a.discover", 1, "stratbox.domains.cbr_industries.issuance_0104.operations:DISCOVER", "stratbox.domains.cbr_industries.issuance_0104.operations:discover"),
        OperationRef("cbr.industries.0104a.acquire", 1, "stratbox.domains.cbr_industries.issuance_0104.operations:ACQUIRE", "stratbox.domains.cbr_industries.issuance_0104.operations:acquire"),
        OperationRef("cbr.industries.0104a.parse", 3, "stratbox.domains.cbr_industries.issuance_0104.operations:PARSE", "stratbox.domains.cbr_industries.issuance_0104.operations:parse"),
        OperationRef("cbr.industries.0104a.build_stream", 3, "stratbox.domains.cbr_industries.issuance_0104.operations:BUILD_STREAM", "stratbox.domains.cbr_industries.issuance_0104.operations:build_stream"),
        OperationRef("cbr.industries.0104a.calculate_apk", 2, "stratbox.domains.cbr_industries.issuance_0104.operations:CALCULATE_APK", "stratbox.domains.cbr_industries.issuance_0104.operations:calculate_apk"),
        OperationRef("cbr.industries.0104a.build_pivots", 2, "stratbox.domains.cbr_industries.issuance_0104.operations:PIVOT", "stratbox.domains.cbr_industries.issuance_0104.operations:build_pivots"),
        OperationRef("cbr.industries.0104a.render_industry", 2, "stratbox.domains.cbr_industries.issuance_0104.operations:RENDER_INDUSTRY", "stratbox.domains.cbr_industries.issuance_0104.operations:render_industry"),
        OperationRef("cbr.industries.0104a.render_industries", 1, "stratbox.domains.cbr_industries.issuance_0104.operations:RENDER_INDUSTRIES", "stratbox.domains.cbr_industries.issuance_0104.operations:render_industries"),
    ),
)
