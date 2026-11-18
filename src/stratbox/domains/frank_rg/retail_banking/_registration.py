"""Published operation references for frg."""

from stratbox.core.execution.catalog import OperationRegistration, OperationRef

REGISTRATION = OperationRegistration(
    owner_id="frank_rg.retail_banking",
    operations=(
        OperationRef("frg.prepare_archive_to_store", 2, "stratbox.domains.frank_rg.retail_banking.api:STREAM_ARCHIVE", "stratbox.domains.frank_rg.retail_banking.api:prepare_archive_to_store"),
        OperationRef("frg.scan", 1, "stratbox.domains.frank_rg.retail_banking.api:SCAN", "stratbox.domains.frank_rg.retail_banking.api:scan"),
        OperationRef("frg.plan_cleanup", 1, "stratbox.domains.frank_rg.retail_banking.api:PLAN", "stratbox.domains.frank_rg.retail_banking.api:plan_cleanup", "stratbox.domains.frank_rg.retail_banking.machine:PLAN_CODEC"),
        OperationRef("frg.apply_cleanup", 1, "stratbox.domains.frank_rg.retail_banking.api:APPLY", "stratbox.domains.frank_rg.retail_banking.api:apply_cleanup"),
        OperationRef("frg.prepare_archive", 1, "stratbox.domains.frank_rg.retail_banking.api:ARCHIVE", "stratbox.domains.frank_rg.retail_banking.api:prepare_archive"),
    ),
)
