"""Portable results and independent flake integration for this publication family."""
from . import definitions as D
from ..common import snapshot_operations as shared
from ..common.integration import integrate, reference_period
from .snapshot_profile import TYPES
from ..debt_0105a.regions import normalize_cbr_0105a_debt_corp_regions_to_latest
from .contracts import Cbr0105ADebtCorpSourceLink, Cbr0105ADebtCorpStreamResult

FAMILY = "0105a"

def _result(original, shared):
    links = tuple(Cbr0105ADebtCorpSourceLink(item.source_id, item.source_url, item.source_name, item.report_date)
                  for item in original if item.source_url is not None)
    return Cbr0105ADebtCorpStreamResult(source_links=links, **shared)


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
