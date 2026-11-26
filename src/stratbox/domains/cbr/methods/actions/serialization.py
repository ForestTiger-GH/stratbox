"""A fixed scientific type vocabulary for versionless CBR value retention."""
from types import MappingProxyType

from stratbox.shared.data.values import SourceDataset
from stratbox.domains.cbr.common.contracts import SourceContentEvidence
from stratbox.shared.data.coverage import SnapshotCoverage
from stratbox.domains.cbr.methods.tables.corporate_lending.observations import CorporateSourceDataset, validate_source_dataset
from stratbox.domains.cbr.methods.tables.corporate_lending.debt.contracts import ParsedCbr0105ADebtCorpFile, Cbr0105ADebtCorpSheetSpec, Cbr0105ADebtCorpSourceFailure
from stratbox.domains.cbr.methods.tables.corporate_lending.issuance.contracts import ParsedIssuanceFile, IssuanceSheetSpec, IssuanceSourceFailure
from stratbox.domains.cbr.methods.tables.corporate_lending.industry.contracts import IndustrySelection, IndustrySpec, IndustryRegionSpec, IndustryValidationIssue
from stratbox.domains.cbr.methods.publications.corporate_lending.contracts import Cbr0105ADebtCorpSourceLink, IssuanceSourceLink
from stratbox.domains.cbr.methods.actions.statistics import SourceWorkbook
from stratbox.domains.cbr.methods.actions.escrow import EscrowTable
from stratbox.domains.cbr.methods.actions.workbook_comparison import CellChange, SheetLayout, SheetChange, WorkbookComparison
from stratbox.domains.cbr.methods.tables.service_network.bank_offices.parser import ScannedCell, ScannedTable, ScannedSource

_TYPES = (SnapshotCoverage, SourceContentEvidence, SourceWorkbook, EscrowTable, CorporateSourceDataset,
    ParsedCbr0105ADebtCorpFile, Cbr0105ADebtCorpSheetSpec, Cbr0105ADebtCorpSourceFailure,
    ParsedIssuanceFile, IssuanceSheetSpec, IssuanceSourceFailure, IndustrySelection,
    IndustrySpec, IndustryRegionSpec, IndustryValidationIssue, Cbr0105ADebtCorpSourceLink,
    IssuanceSourceLink, CellChange, SheetLayout, SheetChange, WorkbookComparison,
    ScannedCell, ScannedTable, ScannedSource)
ADMITTED_TYPES = MappingProxyType({item.__module__ + ":" + item.__qualname__: item for item in _TYPES})


def _validate(value):
    from stratbox.shared.data.values import TableEvidenceSet, WorkbookEvidence
    from stratbox.shared.data.workbook_cells import SheetCells
    if isinstance(value, WorkbookEvidence) or isinstance(value, TableEvidenceSet) and all(isinstance(sheet, SheetCells) for sheet in value.tables):
        from stratbox.domains.cbr.methods.actions.workbook_comparison import validate_workbook
        validate_workbook(value)
    native = value.native if isinstance(value, SourceDataset) else value
    if isinstance(native, CorporateSourceDataset):
        validate_source_dataset(native)
        if isinstance(value, SourceDataset) and value.source_id != native.series_id:
            raise ValueError("cbr.retained_source_identity_mismatch")
    elif isinstance(native, (ParsedCbr0105ADebtCorpFile, ParsedIssuanceFile)):
        from stratbox.shared.data.tables import table_identity
        seal = native.evidence
        if seal is None or seal.output != table_identity((("stream", native.df_stream),)):
            raise ValueError("cbr.retained_source_content_mismatch")
        if isinstance(value, SourceDataset) and not any(receipt.identity in value.lineage for receipt in seal.inputs):
            raise ValueError("cbr.retained_source_lineage_mismatch")
    return value


def encode(inputs, settings, context):
    _validate(inputs["value"])
    from stratbox.core.commands.serialization import encode_value
    options = {"max_bytes": context.parameters["max_bytes"]} if "max_bytes" in context.parameters else {}
    return {"representation": encode_value(inputs["value"], context=context, admitted_types=ADMITTED_TYPES, **options)}


def decode(inputs, settings, context):
    from stratbox.core.commands.serialization import decode_value
    options = {"max_materialized_bytes": context.parameters["max_materialized_bytes"]} if "max_materialized_bytes" in context.parameters else {}
    value = _validate(decode_value(inputs["representation"], context=context,
        admitted_types=ADMITTED_TYPES, **options))
    return {"value": value}
