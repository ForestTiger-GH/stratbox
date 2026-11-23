"""Executable stage and port contracts for statistical workbooks and products."""

from stratbox.core.registry.operations import definition as _registry_definition

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


EXTRACT = _registry_definition('cbr.tables.extract', 1)
VALIDATE = _registry_definition('cbr.tables.validate', 1)
COMPARE = _registry_definition('cbr.tables.compare', 1)
READABLE = _registry_definition('cbr.tables.readable', 1)
FLAKE_SNAPSHOT = _registry_definition('cbr.tables.flake_snapshot', 1)
READ_FLAKE_SNAPSHOT = _registry_definition('cbr.tables.read_flake_snapshot', 1)
ALIGN = _registry_definition('cbr.statistics.align', 1)
CHANGE = _registry_definition('cbr.statistics.calculate_change', 1)
SHARE = _registry_definition('cbr.statistics.calculate_share', 1)
BUILD_VIEW = _registry_definition('cbr.statistics.build_view', 1)
RENDER_VIEW = _registry_definition('cbr.statistics.render_view', 1)
DATASET_SNAPSHOT = _registry_definition('cbr.statistics.dataset_snapshot', 1)
READ_DATASET_SNAPSHOT = _registry_definition('cbr.statistics.read_dataset_snapshot', 1)
VIEW_SNAPSHOT = _registry_definition('cbr.statistics.view_snapshot', 1)
READ_VIEW_SNAPSHOT = _registry_definition('cbr.statistics.read_view_snapshot', 1)
