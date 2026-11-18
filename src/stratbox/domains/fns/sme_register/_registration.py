"""Published operation references for fns_sme."""

from stratbox.core.execution.catalog import OperationRegistration, OperationRef

REGISTRATION = OperationRegistration(
    owner_id="fns.sme_register",
    operations=(
        OperationRef("fns.sme.discover", 1, "stratbox.domains.fns.sme_register.operations:DISCOVER", "stratbox.domains.fns.sme_register.operations:discover"),
        OperationRef("fns.sme.acquire", 1, "stratbox.domains.fns.sme_register.operations:ACQUIRE", "stratbox.domains.fns.sme_register.operations:acquire"),
        OperationRef("fns.sme.parse", 1, "stratbox.domains.fns.sme_register.operations:PARSE", "stratbox.domains.fns.sme_register.operations:parse"),
        OperationRef("fns.sme.capture", 1, "stratbox.domains.fns.sme_register.operations:CAPTURE", "stratbox.domains.fns.sme_register.operations:capture"),
        OperationRef("fns.sme.read_representation", 1, "stratbox.domains.fns.sme_register.operations:READ", "stratbox.domains.fns.sme_register.operations:read_representation"),
        OperationRef("fns.sme.compare", 2, "stratbox.domains.fns.sme_register.operations:COMPARE", "stratbox.domains.fns.sme_register.operations:compare"),
    ),
)
