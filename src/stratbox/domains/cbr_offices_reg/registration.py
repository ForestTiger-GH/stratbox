"""Published operation references for cbr_offices_reg."""

from stratbox.system.execution.registry import DomainRegistration, OperationRef

REGISTRATION = DomainRegistration(
    domain_id="cbr_offices_reg",
    operations=(
        OperationRef("cbr.offices_reg.discover", 1, "stratbox.domains.cbr_offices_reg.operations:DISCOVER", "stratbox.domains.cbr_offices_reg.operations:discover"),
        OperationRef("cbr.offices_reg.acquire", 1, "stratbox.domains.cbr_offices_reg.operations:ACQUIRE", "stratbox.domains.cbr_offices_reg.operations:acquire"),
        OperationRef("cbr.offices_reg.parse", 3, "stratbox.domains.cbr_offices_reg.operations:PARSE", "stratbox.domains.cbr_offices_reg.operations:parse"),
        OperationRef("cbr.offices_reg.capture", 3, "stratbox.domains.cbr_offices_reg.operations:CAPTURE", "stratbox.domains.cbr_offices_reg.operations:capture"),
        OperationRef("cbr.offices_reg.read_representation", 1, "stratbox.domains.cbr_offices_reg.operations:READ", "stratbox.domains.cbr_offices_reg.operations:read_representation"),
        OperationRef("cbr.offices_reg.compare", 2, "stratbox.domains.cbr_offices_reg.operations:COMPARE", "stratbox.domains.cbr_offices_reg.operations:compare"),
    ),
)
