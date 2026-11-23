"""Portable results and independent flake integration for this publication family."""
import stratbox.domains.cbr.operations.corporate_lending.issuance.definitions as D
import stratbox.domains.cbr.operations.corporate_lending.industry.snapshot_operations as shared
from stratbox.domains.cbr.operations.corporate_lending.industry.integration import integrate
from stratbox.domains.cbr.integration.corporate_lending.industry.integration import reference_period
from stratbox.domains.cbr.operations.corporate_lending.issuance.snapshot_profile import TYPES
from stratbox.domains.cbr.integration.corporate_lending.industry.geography import normalize_cbr_0105a_debt_corp_regions_to_latest
from stratbox.domains.cbr.publications.corporate_lending.contracts import IssuanceSourceLink
from stratbox.domains.cbr.integration.corporate_lending.issuance.contracts import IssuanceStreamResult

FAMILY = "0104a"

def _result(original, shared):
    links = tuple(IssuanceSourceLink(item.source_id, item.source_url, item.source_name, item.report_date, item.reference_period)
                  for item in original if item.source_url is not None)
    return IssuanceStreamResult(source_links=links, reference_periods=tuple(reference_period(day) for day in shared["dates"]), **shared)


def integrate_flakes(request, *, context=None):
    return integrate(request, family=FAMILY, definition=D.INTEGRATE_FLAKES, types=TYPES,
        normalize_geography=normalize_cbr_0105a_debt_corp_regions_to_latest, result_factory=_result, context=context)


def build_flake_snapshot(request, *, context=None):
    return shared.build_snapshot(request, family=FAMILY, kind="flake", definition=D.FLAKE_SNAPSHOT, types=TYPES, context=context)

def read_flake_snapshot(request, *, context=None):
    return shared.read_snapshot(request, family=FAMILY, kind="flake", definition=D.READ_FLAKE_SNAPSHOT, types=TYPES, context=context)

def build_stream_snapshot(request, *, context=None):
    return shared.build_snapshot(request, family=FAMILY, kind="stream", definition=D.STREAM_SNAPSHOT, types=TYPES, context=context)

def read_stream_snapshot(request, *, context=None):
    return shared.read_snapshot(request, family=FAMILY, kind="stream", definition=D.READ_STREAM_SNAPSHOT, types=TYPES, context=context)

def build_calculation_snapshot(request, *, context=None):
    return shared.build_snapshot(request, family=FAMILY, kind="calculation", definition=D.CALCULATION_SNAPSHOT, types=TYPES, context=context)

def read_calculation_snapshot(request, *, context=None):
    return shared.read_snapshot(request, family=FAMILY, kind="calculation", definition=D.READ_CALCULATION_SNAPSHOT, types=TYPES, context=context)

def build_view_snapshot(request, *, context=None):
    return shared.build_snapshot(request, family=FAMILY, kind="view", definition=D.VIEW_SNAPSHOT, types=TYPES, context=context)

def read_view_snapshot(request, *, context=None):
    return shared.read_snapshot(request, family=FAMILY, kind="view", definition=D.READ_VIEW_SNAPSHOT, types=TYPES, context=context)
