"""One domain operation surface, with truthful source and stage contracts."""

from stratbox.operations.declarations import definition as _registry_definition
from stratbox.core.limits import ExecutionBudget
from stratbox.shared.data.processing import DataContract,DataRole as R
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.shared.data.workbooks import (
    WorkbookExtract,WorkbookComparison,WORKBOOK_EXTRACT,WORKBOOK_SNAPSHOT as WORKBOOK_SNAPSHOT_CONTRACT,
)
from stratbox.shared.data.documents import (
    DocumentExtract,DOCUMENT_EXTRACT,DOCUMENT_SNAPSHOT as DOCUMENT_SNAPSHOT_CONTRACT,
)
from stratbox.shared.data.views import ObservationView,OBSERVATION_VIEW,OBSERVATION_VIEW_SNAPSHOT
from stratbox.shared.data.representation import Representation
from stratbox.shared.data.observations import ObservationBatch
from ..publications.contracts import RosstatPublicationIndex,PublicationIndexDelta
from ..publications.archives import RegionalArchiveInventory
from ..tables.contracts import RosstatSourceFlake,Kep2Request
from ..tables.snapshots import FLAKE_CONTRACT,FLAKE_SNAPSHOT_CONTRACT
from ..integration.datasets import RosstatDataset,DATASET_CONTRACT,DATASET_SNAPSHOT_CONTRACT
from ..analytics.indicators import DatasetComparison
from .contracts import (
    SelectRequest,IndexComparisonRequest,ApproveIndexRequest,PhysicalRequest,PayloadRequest,MembersRequest,
    WorkbookRequest,WorkbookComparisonRequest,DocumentRequest,StructureDocumentRequest,MapCellsRequest,
    FlakeRequest,SnapshotRequest,IntegrateRequest,DatasetRequest,DatasetComparisonRequest,GrowthRequest,
    ViewRequest,PrepareViewRequest,RenderViewRequest,
)


SELECT = _registry_definition('rosstat.publications.select')
PLAN_UPDATES = _registry_definition('rosstat.publications.plan_updates')
APPROVE_INDEX = _registry_definition('rosstat.publications.review_index')
EXTRACT_WORKBOOK = _registry_definition('rosstat.tables.extract_workbook')
EXTRACT_DOCUMENT = _registry_definition('rosstat.tables.extract_document')
INSPECT_ARCHIVE = _registry_definition('rosstat.publications.inspect_archive')
EXTRACT_MEMBERS = _registry_definition('rosstat.publications.extract_members')
WORKBOOK_SNAPSHOT = _registry_definition('rosstat.tables.workbook_snapshot')
READ_WORKBOOK = _registry_definition('rosstat.tables.read_workbook')
READABLE_WORKBOOK = _registry_definition('rosstat.tables.readable_workbook')
COMPARE_WORKBOOKS = _registry_definition('rosstat.tables.compare_workbooks')
DOCUMENT_SNAPSHOT = _registry_definition('rosstat.tables.document_snapshot')
READ_DOCUMENT = _registry_definition('rosstat.tables.read_document')
READABLE_DOCUMENT = _registry_definition('rosstat.tables.readable_document')
STRUCTURE_DOCUMENT = _registry_definition('rosstat.tables.structure_document')
KEP2 = _registry_definition('rosstat.tables.extract_kep2')
MAP_CELLS = _registry_definition('rosstat.tables.map_reviewed_cells')
FLAKE_SNAPSHOT = _registry_definition('rosstat.tables.flake_snapshot')
READ_FLAKE = _registry_definition('rosstat.tables.read_flake')
READABLE_FLAKE = _registry_definition('rosstat.tables.readable_flake')
INTEGRATE = _registry_definition('rosstat.integration.integrate')
DATASET_SNAPSHOT = _registry_definition('rosstat.integration.dataset_snapshot')
READ_DATASET = _registry_definition('rosstat.integration.read_dataset')
COMPARE_DATASETS = _registry_definition('rosstat.analytics.compare_datasets')
DERIVE_GROWTH = _registry_definition('rosstat.analytics.derive_index_growth')
PREPARE_VIEW = _registry_definition('rosstat.products.prepare_view')
KEP2_MONTHLY_VIEW = _registry_definition('rosstat.products.prepare_kep2_monthly')
VIEW_SNAPSHOT = _registry_definition('rosstat.products.view_snapshot')
READ_VIEW = _registry_definition('rosstat.products.read_view')
RENDER_VIEW = _registry_definition('rosstat.products.render_view')
RENDER_KEP2_XLSX = _registry_definition('rosstat.products.render_kep2_xlsx')

from .contracts import FlakeComparisonRequest
from ..tables.comparison import FlakeComparison,FlakeValidation
VALIDATE_FLAKE = _registry_definition('rosstat.tables.validate_flake')
COMPARE_FLAKES = _registry_definition('rosstat.tables.compare_flakes')
