"""Published operation references for cbr_offices."""

from stratbox.system.execution.registry import DomainRegistration, OperationRef

REGISTRATION = DomainRegistration(
    domain_id="cbr_offices",
    operations=(
        OperationRef("cbr.offices.parse", 1, "stratbox.domains.cbr_offices.operations:PARSE", "stratbox.domains.cbr_offices.operations:parse", "stratbox.domains.cbr_offices.machine:PARSE_CODEC"),
        OperationRef("cbr.offices.acquire", 2, "stratbox.domains.cbr_offices.operations:ACQUIRE", "stratbox.domains.cbr_offices.operations:acquire"),
        OperationRef("cbr.offices.capture", 2, "stratbox.domains.cbr_offices.operations:CAPTURE", "stratbox.domains.cbr_offices.operations:capture"),
        OperationRef("cbr.offices.read_representation", 1, "stratbox.domains.cbr_offices.operations:READ", "stratbox.domains.cbr_offices.operations:read_representation"),
        OperationRef("cbr.offices.compare", 2, "stratbox.domains.cbr_offices.operations:COMPARE", "stratbox.domains.cbr_offices.operations:compare", "stratbox.domains.cbr_offices.machine:COMPARE_CODEC"),
    ),
)
