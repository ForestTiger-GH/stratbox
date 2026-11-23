"""Independent file lifecycle contracts for the shared operation catalog."""
from __future__ import annotations

from stratbox.operations.declarations import definition as _registry_definition

from stratbox.core.limits import ExecutionBudget
from stratbox.shared.data.processing import DataContract, DataRole
from ..publications.contracts import (
    AcquiredReport, AcquireRequest, AssessMaterialRequest, CaptureRequest, Catalog,
    DiscoveryRequest, InspectionRequest, Inventory, MaterialAssessment, PreparedFile,
    PrepareFileRequest, SelectionRequest, SourceIndex, UpdatePlan, UpdateRequest,
)


DISCOVER = _registry_definition('frg.discover')
INSPECT = _registry_definition('frg.inspect')
SELECT = _registry_definition('frg.select')
SCAN = _registry_definition('frg.scan')
ACQUIRE = _registry_definition('frg.acquire')
CAPTURE = _registry_definition('frg.capture')
PREPARE_FILE = _registry_definition('frg.prepare_file')
PLAN_UPDATES = _registry_definition('frg.plan_updates')
ASSESS_MATERIAL = _registry_definition('frg.assess_material')
