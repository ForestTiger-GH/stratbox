"""Published 01_04_A issuance operation references."""

from stratbox.core.execution.catalog import OperationRegistration, OperationRef

REGISTRATION = OperationRegistration(
    owner_id="cbr.corporate_lending.industries.issuance_0104",
    operations=(
        OperationRef("cbr.industries.0104a.discover", 1, 'stratbox.domains.cbr.corporate_lending.industries.issuance_0104.definitions:DISCOVER', "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.operations:discover"),
        OperationRef("cbr.industries.0104a.acquire", 1, 'stratbox.domains.cbr.corporate_lending.industries.issuance_0104.definitions:ACQUIRE', "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.operations:acquire"),
        OperationRef("cbr.industries.0104a.parse", 3, 'stratbox.domains.cbr.corporate_lending.industries.issuance_0104.definitions:PARSE', "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.operations:parse"),
        OperationRef("cbr.industries.0104a.build_stream", 3, 'stratbox.domains.cbr.corporate_lending.industries.issuance_0104.definitions:BUILD_STREAM', "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.operations:build_stream"),
        OperationRef("cbr.industries.0104a.calculate_apk", 2, 'stratbox.domains.cbr.corporate_lending.industries.issuance_0104.definitions:CALCULATE_APK', "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.operations:calculate_apk"),
        OperationRef("cbr.industries.0104a.build_pivots", 2, 'stratbox.domains.cbr.corporate_lending.industries.issuance_0104.definitions:PIVOT', "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.operations:build_pivots"),
        OperationRef("cbr.industries.0104a.render_industry", 2, 'stratbox.domains.cbr.corporate_lending.industries.issuance_0104.definitions:RENDER_INDUSTRY', "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.operations:render_industry"),
        OperationRef("cbr.industries.0104a.render_industries", 1, 'stratbox.domains.cbr.corporate_lending.industries.issuance_0104.definitions:RENDER_INDUSTRIES', "stratbox.domains.cbr.corporate_lending.industries.issuance_0104.operations:render_industries"),
    ),
)
