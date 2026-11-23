"""CBR publication graphs with one index task per publisher page."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping

from stratbox.composition.models import OperationStep, PlanOutputRef, ScenarioDefinition, SourceSelection
from .common import network_retry, value_input


@dataclass(frozen=True, slots=True)
class CbrSelection:
    series_id: str
    issue_id: str
    format: str = "xlsx"
    asset_id: str = "main"
    url: str | None = None
    payload: object | None = None
    extract: bool = True


def multi_cbr_workflow(selections, *, indices: Mapping[str, object] | None = None,
                       scenario_id="cbr.publications.processing"):
    """Build separate source interpretations over shared physical index bytes.

    Selection order defines output order. An index mapping is keyed by the
    official page URL and enables fully offline discovery. The acquisition
    transport owns same-material singleflight; logical original identities stay
    distinct even when two source uses resolve to equal bytes.
    """
    from stratbox.domains.cbr.publications.catalog import source
    from stratbox.domains.cbr.publications.profiles import acquisition_profile
    from stratbox.domains.cbr.publications.access import HTML_TYPES, cbr_request
    selections = tuple(CbrSelection(**item) if isinstance(item, Mapping) else item for item in selections)
    if not selections or any(not isinstance(item, CbrSelection) for item in selections):
        raise ValueError("workflow.cbr_selection_required")
    indices = {} if indices is None else dict(indices)
    steps, outputs, shared_indices = [], {}, {}
    for position, item in enumerate(selections):
        card = source(item.series_id)
        if item.format not in card.formats:
            raise ValueError("cbr.publication.format_unsupported")
        prefix = "source" + str(position)
        selection = SourceSelection(item.series_id, format=item.format)
        if item.payload is not None:
            steps.append(OperationStep(prefix + "_identify", "cbr.publications.identify",
                {"material": value_input(item.payload, "source.payload", "originals")},
                {"series_id": item.series_id, "issue_id": item.issue_id,
                 "format": item.format, "asset_id": item.asset_id}, source=selection))
            original = PlanOutputRef(prefix + "_identify", "original")
            payload = PlanOutputRef(prefix + "_identify", "payload")
        else:
            profile = acquisition_profile(card.acquisition_profile)
            discover_inputs = {}
            if profile.kind not in {"fixed", "page"}:
                page = profile.default_url
                if page not in shared_indices:
                    if page in indices:
                        shared_indices[page] = value_input(indices[page], "source.payload", "originals")
                    else:
                        index_id = "index" + str(len(shared_indices))
                        steps.append(OperationStep(index_id, "source.receive_original", parameters={
                            "request": cbr_request(page, roots=(), media_types=HTML_TYPES,
                                                   limit=8 * 1024**2, deadline=60),
                            "source_id": "cbr.shared_index", "media_types": HTML_TYPES,
                        }, resources={"network": 1}, retry=network_retry()))
                        shared_indices[page] = PlanOutputRef(index_id, "source")
                discover_inputs["index"] = shared_indices[page]
            steps.append(OperationStep(prefix + "_discover", "cbr.publications.discover",
                discover_inputs, {"series_id": item.series_id}, source=selection))
            steps.append(OperationStep(prefix + "_select", "cbr.publications.select",
                {"inventory": PlanOutputRef(prefix + "_discover", "inventory")},
                {"issue_id": item.issue_id if profile.kind not in {"fixed", "page"} else None,
                 "format": item.format, "asset_id": item.asset_id, "url": item.url}, source=selection))
            steps.append(OperationStep(prefix + "_acquire", "cbr.publications.acquire",
                {"asset": PlanOutputRef(prefix + "_select", "asset")},
                {"issue_id": item.issue_id}, source=selection, resources={"network": 1}, retry=network_retry()))
            original = PlanOutputRef(prefix + "_acquire", "original")
            payload = PlanOutputRef(prefix + "_acquire", "payload")
            outputs[prefix + ".inventory"] = PlanOutputRef(prefix + "_discover", "inventory")
        outputs[prefix + ".original"] = original
        outputs[prefix + ".payload"] = payload
        if not item.extract:
            continue
        if item.series_id == "cbr.service_network.bank_offices":
            operation, inputs, parameters, port = "cbr.offices.parse", {"source": payload}, {"captured_on": date.fromisoformat(item.issue_id)}, "release"
        elif item.series_id == "cbr.service_network.territorial_offices":
            operation, inputs, parameters, port = "cbr.offices_reg.parse", {"source": payload}, {"as_of": date.fromisoformat(item.issue_id)}, "release"
        elif card.family_id == "cbr.reporting_forms":
            from stratbox.domains.cbr.tables.reporting_forms.contracts import FormKey
            code = item.series_id.rsplit(".", 1)[-1].removeprefix("f")
            operation, inputs, parameters, port = "cbr.forms.extract", {"source": payload}, {"key": FormKey(code, date.fromisoformat(item.issue_id))}, "flakes"
        elif item.series_id in {"cbr.corporate_lending.debt_0105a", "cbr.corporate_lending.issuance_0104a"}:
            debt = item.series_id.endswith("debt_0105a")
            family = "0105a" if debt else "0104a"
            filename = ("01_05_A_Debt_corp_" if debt else "01_04_A_New_loans_corp_") + date.fromisoformat(item.issue_id).strftime("%Y%m%d") + ".xlsx"
            operation, inputs, parameters, port = "cbr.industries." + family + ".parse", {"source": payload}, {"source_name": filename}, "file"
        elif item.series_id == "cbr.project_finance.escrow":
            operation, inputs, parameters, port = "cbr.escrow.parse", {"source": payload}, {"source_name": "escrow.xlsx", "as_of": date.fromisoformat(item.issue_id)}, "file"
        else:
            operation, inputs, parameters, port = "cbr.tables.extract", {"original": original}, {}, "flake"
        steps.append(OperationStep(prefix + "_extract", operation, inputs, parameters, source=selection))
        outputs[prefix + ".extract"] = PlanOutputRef(prefix + "_extract", port)
    return ScenarioDefinition(scenario_id, tuple(steps), outputs)


def cbr_workflow(series_id, *, payload=None, issue_id, format="xlsx", asset_id="main", url=None, extract=True):
    from dataclasses import replace
    value = multi_cbr_workflow((CbrSelection(series_id, issue_id, format, asset_id, url, payload, extract),))
    return replace(value, scenario_id=series_id + ".processing",
                   outputs={key.removeprefix("source0."): item for key, item in value.outputs.items()})
