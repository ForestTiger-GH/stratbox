"""Typed operation definitions, independent of executable handlers."""

from __future__ import annotations

from stratbox.core.registry.operations import definition as _registry_definition

from stratbox.core.limits import ExecutionBudget
from stratbox.shared.evidence import AcquiredSource
from stratbox.shared.data.representation import Representation
from stratbox.domains.cbr.analytics.reporting_forms.contracts import BuildFormDataRequest, FormData
from stratbox.domains.cbr.tables.reporting_forms.contracts import FormKey, FormSnapshot, ParseFormRequest, SelectFormSourcesRequest
from stratbox.domains.cbr.products.reporting_forms.contracts import FormViews

from stratbox.shared.data.processing import DataContract, DataRole

_TABLES = ExecutionBudget(cells=50_000_000, output_bytes=128 * 1024 * 1024)

SELECT = _registry_definition('cbr.forms.select_sources', 1)

ACQUIRE = _registry_definition('cbr.forms.acquire', 1)

PARSE = _registry_definition('cbr.forms.parse', 2)

BUILD = _registry_definition('cbr.forms.build_data', 2)

VIEWS = _registry_definition('cbr.forms.build_views', 2)

RENDER = _registry_definition('cbr.forms.render_workbook', 2)
