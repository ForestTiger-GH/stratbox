"""Published operation references for frg."""

from stratbox.system.execution.registry import DomainRegistration, OperationRef

REGISTRATION = DomainRegistration(
    domain_id="frg",
    operations=(
        OperationRef("frg.prepare_archive_to_store", 2, "stratbox.domains.frg.api:STREAM_ARCHIVE", "stratbox.domains.frg.api:prepare_archive_to_store"),
        OperationRef("frg.scan", 1, "stratbox.domains.frg.api:SCAN", "stratbox.domains.frg.api:scan"),
        OperationRef("frg.plan_cleanup", 1, "stratbox.domains.frg.api:PLAN", "stratbox.domains.frg.api:plan_cleanup", "stratbox.domains.frg.machine:PLAN_CODEC"),
        OperationRef("frg.apply_cleanup", 1, "stratbox.domains.frg.api:APPLY", "stratbox.domains.frg.api:apply_cleanup"),
        OperationRef("frg.prepare_archive", 1, "stratbox.domains.frg.api:ARCHIVE", "stratbox.domains.frg.api:prepare_archive"),
    ),
)
