"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.core.limits import ExecutionBudget
from stratbox.shared.evidence import AcquiredSource
from stratbox.shared.data.representation import Representation
from stratbox.core.execution.contracts import OperationDefinition
from .contracts import BuildFormDataRequest, FormData, FormKey, FormSnapshot, FormViews, ParseFormRequest, SelectFormSourcesRequest

_TABLES = ExecutionBudget(cells=50_000_000, output_bytes=128 * 1024 * 1024)

SELECT = OperationDefinition(
    "cbr.forms.select_sources",
    1,
    "cbr-forms-source-selection-1",
    SelectFormSourcesRequest,
    tuple,
)

ACQUIRE = OperationDefinition(
    "cbr.forms.acquire",
    1,
    "cbr-forms-source-1",
    FormKey,
    AcquiredSource,
    frozenset({"http"}),
)

PARSE = OperationDefinition(
    "cbr.forms.parse", 2, "cbr-forms-physical-layout-1", ParseFormRequest, FormSnapshot,
    optional_capabilities=frozenset({"archive_decoder"}), limits=_TABLES,
)

BUILD = OperationDefinition(
    "cbr.forms.build_data",
    2,
    "cbr-forms-model-evaluation-1",
    BuildFormDataRequest,
    FormData,
    limits=_TABLES,
)

VIEWS = OperationDefinition(
    "cbr.forms.build_views", 2, "cbr-forms-views-1", FormData, FormViews, limits=_TABLES
)

RENDER = OperationDefinition(
    "cbr.forms.render_workbook", 2, "cbr-forms-xlsx-1", FormViews, Representation, limits=_TABLES
)

