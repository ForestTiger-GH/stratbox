"""Observed byte states and source coordinates have no component release counters."""
from dataclasses import replace

import pytest

from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material,PublicationAsset,PublicationListing,Assessment,SourceClaim
from stratbox.domains.cbr.domain import DOMAIN
from stratbox.shared.identity import ByteIdentity
from stratbox.capabilities.model.targets import SeriesTarget

SOURCE="cbr.corporate_lending.corp_debt_a"


def assessed(box,evidence,baseline=None):
    result=box.invoke("command.source.assess",inputs={"evidence":evidence,"baseline":baseline},target=SeriesTarget(SOURCE))
    assert result.outcome=="succeeded",result.diagnostics
    return result.output("assessment")


def test_first_seen_has_no_invented_prior_absence_or_release_transition():
    with StrategyBox() as box:
        result=assessed(box,Material(b"A",source_id=SOURCE))
        assert result.status=="first_seen" and result.basis=="no_baseline"
        assert result.predecessor is None and result.candidate
        assert not hasattr(result,"profile_version")


def test_a_b_a_b_observation_chain_retains_exact_confirmed_predecessor_bytes():
    a,b=Material(b"A",source_id=SOURCE),Material(b"B",source_id=SOURCE)
    with StrategyBox() as box:
        ab=assessed(box,b,a);ba=assessed(box,a,b);again=assessed(box,b,a)
        assert ab.status==ba.status==again.status=="changed"
        assert (ab.predecessor,ab.candidate)==(a.identity.sha256,b.identity.sha256)
        assert (ba.predecessor,ba.candidate)==(b.identity.sha256,a.identity.sha256)
        assert again==ab


def test_same_bytes_are_unchanged_and_unavailable_baselines_cannot_prove_no_change():
    a=Material(b"A",source_id=SOURCE)
    with StrategyBox() as box:
        assert assessed(box,a,a).status=="unchanged"
        assert assessed(box,a,{"baseline_unavailable":True}).status=="unknown"


def test_observed_listing_changes_do_not_prove_asset_bytes_or_authoritative_absence():
    item=PublicationAsset(SOURCE,"2026-08-01","main",DOMAIN.series[SOURCE].publication.locator,"xlsx")
    listing=PublicationListing("cbr",(item,),Assessment())
    missing=replace(listing,entries=(),assessment=Assessment("partial",("listing_missing",)))
    with StrategyBox() as box:
        same=assessed(box,listing,listing)
        assert same.status=="unknown" and "does_not_certify_asset_bytes" in same.findings[0]
        unavailable=assessed(box,missing,listing)
        assert unavailable.status=="unknown" and unavailable.basis=="publication_listing_incomplete"
        assert unavailable.evidence.status=="partial"


def test_same_material_has_distinct_explicit_issue_and_asset_claims():
    from stratbox.shared.data.values import IdentifiedMaterial
    material=Material(b"identical publisher bytes",source_id=SOURCE)
    a=IdentifiedMaterial(material,SourceClaim(SOURCE,"2026-08-01","main"))
    b=IdentifiedMaterial(material,SourceClaim(SOURCE,"2026-09-01","main"))
    c=IdentifiedMaterial(material,SourceClaim(SOURCE,"2026-08-01","appendix"))
    assert a.identity==b.identity==c.identity
    assert len({(value.claim.issue_id,value.claim.asset_id) for value in (a,b,c)})==3


def test_other_known_sources_cannot_become_a_comparable_baseline():
    with StrategyBox() as box:
        result=box.invoke("command.source.assess",inputs={"evidence":Material(b"A",source_id=SOURCE),
            "baseline":Material(b"A",source_id="cbr.funding.funds_all")},target=SeriesTarget(SOURCE))
        assert result.outcome=="failed" and any("source_mismatch" in str(item) for item in result.diagnostics)


def test_equal_bytes_under_distinct_publication_coordinates_do_not_mean_unchanged_issue():
    from stratbox.shared.data.values import IdentifiedMaterial
    material=Material(b"A",source_id=SOURCE)
    before=IdentifiedMaterial(material,SourceClaim(SOURCE,"2026-08-01","main"))
    after=IdentifiedMaterial(material,SourceClaim(SOURCE,"2026-09-01","main"))
    with StrategyBox() as box:
        result=assessed(box,after,before)
        assert result.status=="changed" and result.basis=="explicit_publication_coordinates"
