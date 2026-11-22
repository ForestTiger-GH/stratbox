"""Published operation references for frg."""

from stratbox.core.execution.catalog import OperationRegistration, OperationRef

REGISTRATION = OperationRegistration(
    owner_id="frank_rg.retail_banking",
    operations=(
        OperationRef("frg.prepare_archive_to_store", 2, 'stratbox.domains.frank_rg.retail_banking.definitions:STREAM_ARCHIVE', "stratbox.domains.frank_rg.retail_banking.api:prepare_archive_to_store"),
        OperationRef("frg.scan", 1, 'stratbox.domains.frank_rg.retail_banking.definitions:SCAN', "stratbox.domains.frank_rg.retail_banking.api:scan"),
        OperationRef("frg.plan_cleanup", 1, 'stratbox.domains.frank_rg.retail_banking.definitions:PLAN', "stratbox.domains.frank_rg.retail_banking.api:plan_cleanup", "stratbox.domains.frank_rg.retail_banking.machine:PLAN_CODEC", 'stratbox.domains.frank_rg.retail_banking.machine_contracts:PLAN_CONTRACT'),
        OperationRef("frg.apply_cleanup", 1, 'stratbox.domains.frank_rg.retail_banking.definitions:APPLY', "stratbox.domains.frank_rg.retail_banking.api:apply_cleanup"),
        OperationRef("frg.prepare_archive", 1, 'stratbox.domains.frank_rg.retail_banking.definitions:ARCHIVE', "stratbox.domains.frank_rg.retail_banking.api:prepare_archive"),
    ),
)
