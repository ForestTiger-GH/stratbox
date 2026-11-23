"""Registry, discovery and original-format admission at the publisher boundary."""

from stratbox.core.registry.operations import definition as _registry_definition
from stratbox.core.limits import ExecutionBudget
from stratbox.shared.data.processing import DataContract, DataRole
from stratbox.domains.cbr.publications.contracts import DiscoverRequest, IdentifiedOriginal, IdentifyRequest, ListSourcesRequest, PublicationInventory
from stratbox.domains.cbr.publications.contracts import (AcquirePublicationRequest, AssessUpdatesRequest,
    PublicationAsset, PublicationUpdatePlan, SelectPublicationRequest)

LIMITS = ExecutionBudget(input_bytes=256 * 1024**2, output_bytes=256 * 1024**2,
                        temporary_bytes=256 * 1024**2, cells=5_000_000)
LIST = _registry_definition('cbr.publications.list_sources', 1)
DISCOVER = _registry_definition('cbr.publications.discover', 1)
IDENTIFY = _registry_definition('cbr.publications.identify', 1)

SELECT = _registry_definition('cbr.publications.select', 1)
ACQUIRE = _registry_definition('cbr.publications.acquire', 1)
ASSESS_UPDATES = _registry_definition('cbr.publications.assess_updates', 1)
