"""Published operation references for escrow."""

from stratbox.system.execution.registry import DomainRegistration, OperationRef

REGISTRATION = DomainRegistration(
    domain_id="escrow",
    operations=(
        OperationRef("cbr.escrow.discover", 1, "stratbox.domains.escrow.operations:DISCOVER", "stratbox.domains.escrow.operations:discover"),
        OperationRef("cbr.escrow.acquire", 1, "stratbox.domains.escrow.operations:ACQUIRE", "stratbox.domains.escrow.operations:acquire"),
        OperationRef("cbr.escrow.parse", 2, "stratbox.domains.escrow.operations:PARSE", "stratbox.domains.escrow.operations:parse"),
        OperationRef("cbr.escrow.build_history", 2, "stratbox.domains.escrow.operations:HISTORY", "stratbox.domains.escrow.operations:build_history"),
        OperationRef("cbr.escrow.build_views", 2, "stratbox.domains.escrow.operations:VIEWS", "stratbox.domains.escrow.operations:build_views"),
        OperationRef("cbr.escrow.render_workbook", 2, "stratbox.domains.escrow.operations:RENDER", "stratbox.domains.escrow.operations:render_workbook"),
    ),
)
