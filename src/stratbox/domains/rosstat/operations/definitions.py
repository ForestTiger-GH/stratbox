"""One domain operation surface, with truthful source and stage contracts."""

from stratbox.core.registry.operations import definition as _registry_definition
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


SELECT = _registry_definition('rosstat.publications.select', 1)
PLAN_UPDATES = _registry_definition('rosstat.publications.plan_updates', 1)
APPROVE_INDEX = _registry_definition('rosstat.publications.review_index', 1)
EXTRACT_WORKBOOK = _registry_definition('rosstat.tables.extract_workbook', 1)
EXTRACT_DOCUMENT = _registry_definition('rosstat.tables.extract_document', 1)
INSPECT_ARCHIVE = _registry_definition('rosstat.publications.inspect_archive', 1)
EXTRACT_MEMBERS = _registry_definition('rosstat.publications.extract_members', 1)
WORKBOOK_SNAPSHOT = _registry_definition('rosstat.tables.workbook_snapshot', 1)
READ_WORKBOOK = _registry_definition('rosstat.tables.read_workbook', 1)
READABLE_WORKBOOK = _registry_definition('rosstat.tables.readable_workbook', 1)
COMPARE_WORKBOOKS = _registry_definition('rosstat.tables.compare_workbooks', 1)
DOCUMENT_SNAPSHOT = _registry_definition('rosstat.tables.document_snapshot', 1)
READ_DOCUMENT = _registry_definition('rosstat.tables.read_document', 1)
READABLE_DOCUMENT = _registry_definition('rosstat.tables.readable_document', 1)
STRUCTURE_DOCUMENT = _registry_definition('rosstat.tables.structure_document', 1)
KEP2 = _registry_definition('rosstat.tables.extract_kep2', 1)
MAP_CELLS = _registry_definition('rosstat.tables.map_reviewed_cells', 1)
FLAKE_SNAPSHOT = _registry_definition('rosstat.tables.flake_snapshot', 1)
READ_FLAKE = _registry_definition('rosstat.tables.read_flake', 1)
READABLE_FLAKE = _registry_definition('rosstat.tables.readable_flake', 1)
INTEGRATE = _registry_definition('rosstat.integration.integrate', 1)
DATASET_SNAPSHOT = _registry_definition('rosstat.integration.dataset_snapshot', 1)
READ_DATASET = _registry_definition('rosstat.integration.read_dataset', 1)
COMPARE_DATASETS = _registry_definition('rosstat.analytics.compare_datasets', 1)
DERIVE_GROWTH = _registry_definition('rosstat.analytics.derive_index_growth', 1)
PREPARE_VIEW = _registry_definition('rosstat.products.prepare_view', 1)
KEP2_MONTHLY_VIEW = _registry_definition('rosstat.products.prepare_kep2_monthly', 1)
VIEW_SNAPSHOT = _registry_definition('rosstat.products.view_snapshot', 1)
READ_VIEW = _registry_definition('rosstat.products.read_view', 1)
RENDER_VIEW = _registry_definition('rosstat.products.render_view', 1)
RENDER_KEP2_XLSX = _registry_definition('rosstat.products.render_kep2_xlsx', 1)

from .contracts import FlakeComparisonRequest
from ..tables.comparison import FlakeComparison,FlakeValidation
VALIDATE_FLAKE = _registry_definition('rosstat.tables.validate_flake', 1)
COMPARE_FLAKES = _registry_definition('rosstat.tables.compare_flakes', 1)
