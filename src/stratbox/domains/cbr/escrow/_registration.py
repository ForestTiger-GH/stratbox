"""Published operation references for escrow."""

from stratbox.core.execution.catalog import OperationRegistration, OperationRef

REGISTRATION = OperationRegistration(
    owner_id="cbr.escrow",
    operations=(
        OperationRef("cbr.escrow.discover", 1, 'stratbox.domains.cbr.escrow.definitions:DISCOVER', "stratbox.domains.cbr.escrow.operations:discover"),
        OperationRef("cbr.escrow.acquire", 1, 'stratbox.domains.cbr.escrow.definitions:ACQUIRE', "stratbox.domains.cbr.escrow.operations:acquire"),
        OperationRef("cbr.escrow.parse", 2, 'stratbox.domains.cbr.escrow.definitions:PARSE', "stratbox.domains.cbr.escrow.operations:parse"),
        OperationRef("cbr.escrow.build_history", 2, 'stratbox.domains.cbr.escrow.definitions:HISTORY', "stratbox.domains.cbr.escrow.operations:build_history"),
        OperationRef("cbr.escrow.build_views", 2, 'stratbox.domains.cbr.escrow.definitions:VIEWS', "stratbox.domains.cbr.escrow.operations:build_views"),
        OperationRef("cbr.escrow.render_workbook", 2, 'stratbox.domains.cbr.escrow.definitions:RENDER', "stratbox.domains.cbr.escrow.operations:render_workbook"),
    ),
)
