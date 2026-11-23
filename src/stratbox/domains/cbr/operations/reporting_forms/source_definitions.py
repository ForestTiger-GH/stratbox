"""Source-local extraction, normalization and portable form history contracts."""

from stratbox.operations.declarations import definition as _registry_definition


from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.snapshots import DatasetSnapshot

from stratbox.domains.cbr.tables.reporting_forms.contracts import DiscoverFormsRequest, ExtractFormRequest, FormFlakes, FormFlakeSnapshotRequest, FormInventory, FormSnapshot, FormHistoryRequest, NormalizeFormRequest, FormFlakeExport, RenderFormFlakesRequest, ReadFormFlakeExportRequest
from stratbox.domains.cbr.analytics.reporting_forms.contracts import FormData
from stratbox.domains.cbr.operations.reporting_forms.contracts import FormResultSnapshotRequest
from stratbox.domains.cbr.products.reporting_forms.contracts import FormViews
from stratbox.domains.cbr.operations.reporting_forms.definitions import _TABLES


DISCOVER = _registry_definition('cbr.forms.discover_sources')

EXTRACT = _registry_definition('cbr.forms.extract')

NORMALIZE = _registry_definition('cbr.forms.normalize')

FLAKE_SNAPSHOT = _registry_definition('cbr.forms.flake_snapshot')

RESTORE_FLAKES = _registry_definition('cbr.forms.restore_flakes')

RESULT_SNAPSHOT = _registry_definition('cbr.forms.result_snapshot')


RESTORE_NORMALIZED = _registry_definition('cbr.forms.restore_normalized')
RESTORE_DATA = _registry_definition('cbr.forms.restore_data')
RESTORE_VIEWS = _registry_definition('cbr.forms.restore_views')

HISTORY = _registry_definition('cbr.forms.build_history')

RESTORE_HISTORY = _registry_definition('cbr.forms.restore_history')

RENDER_FLAKES = _registry_definition('cbr.forms.render_flakes')

READ_FLAKE_EXPORT = _registry_definition('cbr.forms.read_flake_export')
