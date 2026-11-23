"""Source-local extraction, normalization and portable form history contracts."""

from stratbox.core.registry.operations import definition as _registry_definition


from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import DatasetSnapshot

from stratbox.domains.cbr.tables.reporting_forms.contracts import DiscoverFormsRequest, ExtractFormRequest, FormFlakes, FormFlakeSnapshotRequest, FormInventory, FormSnapshot, FormHistoryRequest, NormalizeFormRequest, FormFlakeExport, RenderFormFlakesRequest, ReadFormFlakeExportRequest
from stratbox.domains.cbr.analytics.reporting_forms.contracts import FormData
from stratbox.domains.cbr.operations.reporting_forms.contracts import FormResultSnapshotRequest
from stratbox.domains.cbr.products.reporting_forms.contracts import FormViews
from stratbox.domains.cbr.operations.reporting_forms.definitions import _TABLES


DISCOVER = _registry_definition('cbr.forms.discover_sources', 1)

EXTRACT = _registry_definition('cbr.forms.extract', 1)

NORMALIZE = _registry_definition('cbr.forms.normalize', 1)

FLAKE_SNAPSHOT = _registry_definition('cbr.forms.flake_snapshot', 1)

RESTORE_FLAKES = _registry_definition('cbr.forms.restore_flakes', 1)

RESULT_SNAPSHOT = _registry_definition('cbr.forms.result_snapshot', 1)


RESTORE_NORMALIZED = _registry_definition('cbr.forms.restore_normalized', 1)
RESTORE_DATA = _registry_definition('cbr.forms.restore_data', 1)
RESTORE_VIEWS = _registry_definition('cbr.forms.restore_views', 1)

HISTORY = _registry_definition('cbr.forms.build_history', 1)

RESTORE_HISTORY = _registry_definition('cbr.forms.restore_history', 1)

RENDER_FLAKES = _registry_definition('cbr.forms.render_flakes', 1)

READ_FLAKE_EXPORT = _registry_definition('cbr.forms.read_flake_export', 1)
