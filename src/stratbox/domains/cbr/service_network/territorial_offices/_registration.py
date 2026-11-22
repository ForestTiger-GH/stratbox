"""Published operation references for cbr_offices_reg."""

from stratbox.core.execution.catalog import OperationRegistration, OperationRef

REGISTRATION = OperationRegistration(
    owner_id="cbr.service_network.territorial_offices",
    operations=(
        OperationRef("cbr.offices_reg.discover", 1, 'stratbox.domains.cbr.service_network.territorial_offices.definitions:DISCOVER', "stratbox.domains.cbr.service_network.territorial_offices.operations:discover"),
        OperationRef("cbr.offices_reg.acquire", 1, 'stratbox.domains.cbr.service_network.territorial_offices.definitions:ACQUIRE', "stratbox.domains.cbr.service_network.territorial_offices.operations:acquire"),
        OperationRef("cbr.offices_reg.parse", 3, 'stratbox.domains.cbr.service_network.territorial_offices.definitions:PARSE', "stratbox.domains.cbr.service_network.territorial_offices.operations:parse"),
        OperationRef("cbr.offices_reg.capture", 3, 'stratbox.domains.cbr.service_network.territorial_offices.definitions:CAPTURE', "stratbox.domains.cbr.service_network.territorial_offices.operations:capture"),
        OperationRef("cbr.offices_reg.read_representation", 1, 'stratbox.domains.cbr.service_network.territorial_offices.definitions:READ', "stratbox.domains.cbr.service_network.territorial_offices.operations:read_representation"),
        OperationRef("cbr.offices_reg.compare", 2, 'stratbox.domains.cbr.service_network.territorial_offices.definitions:COMPARE', "stratbox.domains.cbr.service_network.territorial_offices.operations:compare"),
    ),
)
