"""Source history, reading, semantic alignment, calculation and products."""

from stratbox.core.registry.operations import definition as _registry_definition

from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.shared.data.representation import Representation
from stratbox.shared.data.observations import ObservationBatch
from stratbox.shared.data.snapshots import DatasetSnapshot
from stratbox.domains.cbr.tables.service_network.history import OfficeHistoryRequest
from stratbox.domains.cbr.tables.service_network.readable import ReadableOfficesRequest
from stratbox.domains.cbr.integration.service_network.contracts import AlignOfficesRequest
from stratbox.domains.cbr.analytics.service_network.changes import OfficeChangesRequest, OfficeChanges
from stratbox.domains.cbr.products.service_network.views import OfficeViewRequest, RenderOfficeViewRequest

READABLE = _registry_definition('cbr.service_network.make_readable')
HISTORY = _registry_definition('cbr.service_network.build_history')
RESTORE_HISTORY = _registry_definition('cbr.service_network.restore_history')
ALIGN = _registry_definition('cbr.service_network.align')
CHANGES = _registry_definition('cbr.service_network.calculate_changes')
VIEW = _registry_definition('cbr.service_network.build_view')
RENDER = _registry_definition('cbr.service_network.render')
