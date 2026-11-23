"""Independent file lifecycle contracts for the shared operation catalog."""
from __future__ import annotations

from stratbox.core.registry.operations import definition as _registry_definition

from stratbox.core.limits import ExecutionBudget
from stratbox.shared.data.processing import DataContract, DataRole
from ..publications.contracts import (
    AcquiredReport, AcquireRequest, AssessMaterialRequest, CaptureRequest, Catalog,
    DiscoveryRequest, InspectionRequest, Inventory, MaterialAssessment, PreparedFile,
    PrepareFileRequest, SelectionRequest, SourceIndex, UpdatePlan, UpdateRequest,
)


DISCOVER = _registry_definition('frg.discover', 1)
INSPECT = _registry_definition('frg.inspect', 1)
SELECT = _registry_definition('frg.select', 1)
SCAN = _registry_definition('frg.scan', 1)
ACQUIRE = _registry_definition('frg.acquire', 1)
CAPTURE = _registry_definition('frg.capture', 1)
PREPARE_FILE = _registry_definition('frg.prepare_file', 1)
PLAN_UPDATES = _registry_definition('frg.plan_updates', 1)
ASSESS_MATERIAL = _registry_definition('frg.assess_material', 1)
