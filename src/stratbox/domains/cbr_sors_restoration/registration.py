"""Published operation references for cbr_sors_restoration."""

from stratbox.system.execution.registry import DomainRegistration, OperationRef

REGISTRATION = DomainRegistration(
    domain_id="cbr_sors_restoration",
    operations=(
        OperationRef("cbr.sors.read_source_files", 1, "stratbox.domains.cbr_sors_restoration.api:READ", "stratbox.domains.cbr_sors_restoration.api:read_source_files"),
        OperationRef("cbr.sors.load_sources", 3, "stratbox.domains.cbr_sors_restoration.api:LOAD", "stratbox.domains.cbr_sors_restoration.api:load_sources"),
        OperationRef("cbr.sors.restore", 3, "stratbox.domains.cbr_sors_restoration.api:RESTORE", "stratbox.domains.cbr_sors_restoration.api:restore"),
        OperationRef("cbr.sors.crosswalk", 2, "stratbox.domains.cbr_sors_restoration.api:CROSSWALK", "stratbox.domains.cbr_sors_restoration.api:run_crosswalk"),
        OperationRef("cbr.sors.build_pivot", 2, "stratbox.domains.cbr_sors_restoration.api:PIVOT", "stratbox.domains.cbr_sors_restoration.api:build_pivot"),
        OperationRef("cbr.sors.render_workbook", 2, "stratbox.domains.cbr_sors_restoration.api:RENDER", "stratbox.domains.cbr_sors_restoration.api:render_workbook"),
    ),
)
