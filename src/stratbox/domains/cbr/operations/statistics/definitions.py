"""Executable stage and port contracts for statistical workbooks and products."""

from stratbox.operations.declarations import definition as _registry_definition

from stratbox.core.limits import ExecutionBudget
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.representation import Representation
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.domains.cbr.tables.statistics.contracts import WorkbookFlake, WorkbookValidation, WorkbookComparison
from stratbox.domains.cbr.tables.statistics.snapshots import FLAKE
from stratbox.domains.cbr.integration.statistics.contracts import StatisticsDataset
from stratbox.domains.cbr.integration.statistics.snapshots import DATASET
from stratbox.domains.cbr.products.statistics.views import VIEW, StatisticsView
from . import contracts as C


EXTRACT = _registry_definition('cbr.tables.extract')
VALIDATE = _registry_definition('cbr.tables.validate')
COMPARE = _registry_definition('cbr.tables.compare')
READABLE = _registry_definition('cbr.tables.readable')
FLAKE_SNAPSHOT = _registry_definition('cbr.tables.flake_snapshot')
READ_FLAKE_SNAPSHOT = _registry_definition('cbr.tables.read_flake_snapshot')
ALIGN = _registry_definition('cbr.statistics.align')
CHANGE = _registry_definition('cbr.statistics.calculate_change')
SHARE = _registry_definition('cbr.statistics.calculate_share')
BUILD_VIEW = _registry_definition('cbr.statistics.build_view')
RENDER_VIEW = _registry_definition('cbr.statistics.render_view')
DATASET_SNAPSHOT = _registry_definition('cbr.statistics.dataset_snapshot')
READ_DATASET_SNAPSHOT = _registry_definition('cbr.statistics.read_dataset_snapshot')
VIEW_SNAPSHOT = _registry_definition('cbr.statistics.view_snapshot')
READ_VIEW_SNAPSHOT = _registry_definition('cbr.statistics.read_view_snapshot')
