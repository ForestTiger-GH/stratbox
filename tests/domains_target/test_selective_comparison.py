"""One explicit selected scope has the same identity rules across publishers."""
from dataclasses import replace
from types import SimpleNamespace

import pytest

from stratbox.domains.fns.common.publications import SME_PUBLICATION
from stratbox.domains.fns.methods import publications as fns
from stratbox.domains.minfin.domain import DOMAIN as MINFIN
from stratbox.domains.minfin.methods import publications as minfin
from stratbox.domains.frank_rg.methods import publications as frank
from stratbox.domains.frank_rg.methods.publications import DeliverySettings
from stratbox.domains.cbr.domain import DOMAIN as CBR
from stratbox.domains.cbr.methods.actions import publications as cbr
from stratbox.domains.rosstat.methods import publications as rosstat
from stratbox.domains.rosstat.common.publications import KEP2_PUBLICATION as ROSSTAT_PUBLICATION
from stratbox.shared.data.materials import StagedMaterialRef
from stratbox.shared.data.selection import IssueQuery
from stratbox.shared.data.values import Assessment, Material, ImmutableMaterialRef, PublicationAsset, PublicationListing, request_identity


def context(**parameters):
    return SimpleNamespace(parameters=parameters, checkpoint=lambda: None)


def test_fns_typed_issue_request_preserves_read_only_post_body_in_identity():
    first = fns.prepare_request({"query": IssueQuery(mode="exact", issues=("2026-11-10",))}, SME_PUBLICATION, context())["request"]
    later = fns.prepare_request({"query": IssueQuery(mode="exact", issues=("2026-11-11",))}, SME_PUBLICATION, context())["request"]
    assert first.read_only and first.method == "POST" and first.form == {"statDate": "10.11.2026"}
    assert first.url == later.url and request_identity(first) != request_identity(later)
    index = fns.prepare_request({"query": IssueQuery(mode="exact", issues=("2026-11-10",))}, SME_PUBLICATION, context(role="index"))["request"]
    assert index.method == "GET" and index.url == SME_PUBLICATION.index_url and index.form is None


def test_minfin_selected_asset_ignores_changed_sibling_without_claiming_equal_bytes():
    record = next(iter(MINFIN.series.values()))
    settings = record.publication.settings
    selected = PublicationAsset(settings.source_id, "2026-04-01", settings.asset.asset_id,
        "https://minfin.gov.ru/selected.xlsx", "xlsx")
    sibling = replace(selected, source_id="minfin.other", asset_id="other", locator="https://minfin.gov.ru/other.xlsx")
    first = PublicationListing("minfin", (selected, sibling))
    later = replace(first, entries=(selected, replace(sibling, issue_id="2026-05-01")))
    assessed = minfin.assess({"evidence": later, "baseline": first}, settings, context())["assessment"]
    assert assessed.status == "unknown" and assessed.candidate == assessed.predecessor
    feed = minfin.assess({"evidence": later, "baseline": first}, settings, context(comparison_scope="feed"))["assessment"]
    assert feed.status == "changed" and feed.candidate != feed.predecessor
    incomplete = replace(later, assessment=Assessment("partial", ("unclassified unrelated attachment",)))
    selection = minfin.select({"listing": incomplete, "query": IssueQuery(mode="exact", issues=(selected.issue_id,))}, settings, context())
    assert selection["selection"].assessment.complete and not selection["report"].parent_assessment.complete


def test_selected_issue_scope_excludes_changed_unselected_date():
    source = SME_PUBLICATION.source_id
    first_asset = PublicationAsset(source, "2026-11-10", "statistics", SME_PUBLICATION.data_url, "json")
    other = replace(first_asset, issue_id="2026-10-10")
    first = PublicationListing("fns", (first_asset, other))
    later = replace(first, entries=(first_asset, replace(other, locator=other.locator + "?revision=2")))
    query = IssueQuery(mode="exact", issues=(first_asset.issue_id,))
    result = fns.assess({"evidence": later, "baseline": first, "query": query}, SME_PUBLICATION, context())["assessment"]
    assert result.status == "unknown" and result.candidate == result.predecessor
    with pytest.raises(ValueError, match="comparison_conflict"):
        fns.assess({"evidence": Material(b"source", source_id="minfin.other")}, SME_PUBLICATION, context())


def test_frank_selected_inventory_identity_does_not_include_unrelated_files():
    settings = DeliverySettings("frg.express.issuance")
    chosen = {"path": "/files/2026-05-01_Express market issuance.xlsx",
        "filename": "FRG. Express monitoring market issuance 2026-05-01.xlsx", "size": 10, "mtime": 1}
    # Use an actual declared publisher naming rule, preserving the frozen source scope.
    chosen["filename"] = "FRG. Экспресс-мониторинг рынка. Выдачи. 2026-05-01.xlsx"
    first = frank.scan({"index": (chosen, {"path": "/unclassified.txt", "size": 1})}, settings, context())["listing"]
    later = frank.scan({"index": (chosen, {"path": "/unclassified.txt", "size": 2})}, settings, context())["listing"]
    assert first.lineage != later.lineage
    result = frank.assess({"evidence": later, "baseline": first}, settings, context())["assessment"]
    assert result.candidate == result.predecessor and result.status == "indeterminate"


def test_missing_member_in_incomplete_index_cannot_be_certified_as_removed():
    asset = PublicationAsset(SME_PUBLICATION.source_id, "2026-11-10", "statistics", SME_PUBLICATION.data_url, "json")
    first = PublicationListing("fns", (asset,))
    partial = PublicationListing("fns", (), Assessment("partial", ("index.fragment_only",)))
    query = IssueQuery(issues=(asset.issue_id,))
    result = fns.assess({"evidence": partial, "baseline": first, "query": query}, SME_PUBLICATION, context())["assessment"]
    assert result.status == "unknown" and not result.evidence["selected_coverage"].complete


@pytest.mark.parametrize("publisher", ("cbr", "fns", "minfin", "frank", "rosstat"))
def test_exact_original_comparison_ignores_read_carrier_and_observation_metadata(publisher):
    if publisher == "cbr":
        source = CBR.series["cbr.funding.funds_all"]
        method, settings, source_id = cbr, source.publication, source.id
    elif publisher == "fns":
        method, settings, source_id = fns, SME_PUBLICATION, SME_PUBLICATION.source_id
    elif publisher == "minfin":
        source = next(iter(MINFIN.series.values()))
        method, settings, source_id = minfin, source.publication.settings, source.id
    elif publisher == "frank":
        method, settings, source_id = frank, DeliverySettings("frg.express.issuance"), "frg.express.issuance"
    else:
        source = ROSSTAT_PUBLICATION
        method, settings, source_id = rosstat, source.settings, source.id
    original = Material(b"the exact original", source_id=source_id,
        metadata={"issue_id": "2026-04-01", "observed_at": "earlier"})
    retained = ImmutableMaterialRef("objects/original", original.identity,
        metadata={"source_id": source_id, "issue_id": "2026-04-01", "observed_at": "later"})
    staged = StagedMaterialRef("stage", "provider", "session", original.identity,
        source_id=source_id, metadata={"issue_id": "2026-04-01"})
    for candidate in (retained, staged):
        result = method.assess({"evidence": candidate, "baseline": original}, settings, context())["assessment"]
        assert result.status == "unchanged" and result.basis == "exact_material_bytes"
        assert result.candidate == result.predecessor == original.identity.sha256
    changed_issue = replace(staged, metadata={"issue_id": "2026-05-01"})
    result = method.assess({"evidence": changed_issue, "baseline": original}, settings, context())["assessment"]
    assert result.status == "changed" and result.basis == "explicit_publication_coordinates"
    with pytest.raises(ValueError, match="conflict|source_mismatch"):
        method.assess({"evidence": replace(staged, source_id="another.publisher")}, settings, context())
