"""Published operation references for fns_1yur."""

from stratbox.core.execution.catalog import OperationRegistration, OperationRef

REGISTRATION = OperationRegistration(
    owner_id="fns_1yur",
    operations=(
        OperationRef("fns.1yur.discover", 1, "stratbox.domains.fns_1yur.operations:DISCOVER", "stratbox.domains.fns_1yur.operations:discover"),
        OperationRef("fns.1yur.acquire", 1, "stratbox.domains.fns_1yur.operations:ACQUIRE", "stratbox.domains.fns_1yur.operations:acquire"),
        OperationRef("fns.1yur.parse", 1, "stratbox.domains.fns_1yur.operations:PARSE", "stratbox.domains.fns_1yur.operations:parse"),
        OperationRef("fns.1yur.capture", 1, "stratbox.domains.fns_1yur.operations:CAPTURE", "stratbox.domains.fns_1yur.operations:capture"),
        OperationRef("fns.1yur.read_representation", 1, "stratbox.domains.fns_1yur.operations:READ", "stratbox.domains.fns_1yur.operations:read_representation"),
        OperationRef("fns.1yur.compare", 2, "stratbox.domains.fns_1yur.operations:COMPARE", "stratbox.domains.fns_1yur.operations:compare"),
    ),
)
