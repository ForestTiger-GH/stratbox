"""Published operation references for fns_sme."""

from stratbox.system.execution.registry import DomainRegistration, OperationRef

REGISTRATION = DomainRegistration(
    domain_id="fns_sme",
    operations=(
        OperationRef("fns.sme.discover", 1, "stratbox.domains.fns_sme.operations:DISCOVER", "stratbox.domains.fns_sme.operations:discover"),
        OperationRef("fns.sme.acquire", 1, "stratbox.domains.fns_sme.operations:ACQUIRE", "stratbox.domains.fns_sme.operations:acquire"),
        OperationRef("fns.sme.parse", 1, "stratbox.domains.fns_sme.operations:PARSE", "stratbox.domains.fns_sme.operations:parse"),
        OperationRef("fns.sme.capture", 1, "stratbox.domains.fns_sme.operations:CAPTURE", "stratbox.domains.fns_sme.operations:capture"),
        OperationRef("fns.sme.read_representation", 1, "stratbox.domains.fns_sme.operations:READ", "stratbox.domains.fns_sme.operations:read_representation"),
        OperationRef("fns.sme.compare", 2, "stratbox.domains.fns_sme.operations:COMPARE", "stratbox.domains.fns_sme.operations:compare"),
    ),
)
