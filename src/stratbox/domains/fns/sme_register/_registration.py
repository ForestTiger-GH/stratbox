"""Published operation references for fns_sme."""

from stratbox.core.execution.catalog import OperationRegistration, OperationRef

REGISTRATION = OperationRegistration(
    owner_id="fns.sme_register",
    operations=(
        OperationRef("fns.sme.discover", 1, 'stratbox.domains.fns.sme_register.definitions:DISCOVER', "stratbox.domains.fns.sme_register.operations:discover"),
        OperationRef("fns.sme.acquire", 1, 'stratbox.domains.fns.sme_register.definitions:ACQUIRE', "stratbox.domains.fns.sme_register.operations:acquire"),
        OperationRef("fns.sme.parse", 1, 'stratbox.domains.fns.sme_register.definitions:PARSE', "stratbox.domains.fns.sme_register.operations:parse"),
        OperationRef("fns.sme.capture", 1, 'stratbox.domains.fns.sme_register.definitions:CAPTURE', "stratbox.domains.fns.sme_register.operations:capture"),
        OperationRef("fns.sme.read_representation", 1, 'stratbox.domains.fns.sme_register.definitions:READ', "stratbox.domains.fns.sme_register.operations:read_representation"),
        OperationRef("fns.sme.compare", 2, 'stratbox.domains.fns.sme_register.definitions:COMPARE', "stratbox.domains.fns.sme_register.operations:compare"),
    ),
)
