"""Source forms, semantic alignment and model selection have independent boundaries."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
from struct import pack

from stratbox.domains.cbr.operations import reporting_forms as forms
from stratbox.shared.data.observations import PeriodRef
from stratbox.shared.evidence import SourcePayload

DAY=date(2026,4,1)

def source(fields,rows):
    size=1+16*len(fields)
    header=pack("<BBBBIHH20x",3,126,4,1,len(rows),33+32*len(fields),size)
    descriptors=b"".join(pack("<11sc4xBB14x",name.encode(),b"C",16,0) for name in fields)
    values=b"".join(b" "+b"".join(value.encode().ljust(16) for value in row) for row in rows)
    return SourcePayload(header+descriptors+b"\r"+values+b"\x1a")

def ok(result):
    assert result.outcome=="succeeded",result.diagnostics
    return result.value

def parse(code,fields,rows):
    return ok(forms.parse_form(forms.ParseFormRequest(forms.FormKey(code,DAY),source(fields,rows))))


def test_default_model_selects_all_admitted_banks_and_preserves_an_explicit_subset():
    snapshot=parse("802",("REGN_GKO","STR","VSEGO"),(("1000","14","1.23"),("2000","14","9")))
    all_banks=ok(forms.build_form_data(forms.BuildFormDataRequest((snapshot,))))
    assert set(all_banks.banks.regn)=={"1000","2000"}
    selected=ok(forms.build_form_data(forms.BuildFormDataRequest((snapshot,),(forms.BankSelection("1000","Selected"),))))
    assert set(selected.banks.regn)=={"1000"}


def test_alignment_keeps_banks_and_groups_distinct_and_retains_physical_record_evidence():
    group=parse("802",("REGN_GKO","STR","VSEGO"),(("1000","14","000001.2300"),))
    bank=parse("101",("REGN","NUM_SC","IITG","PLAN","A_P"),(("1000","47422","5","A","2"),))
    batch=ok(forms.align_forms(forms.AlignFormRequest((group,bank),"forms.observations","v1")))
    by_form={dict(item.dimensions)["form"]:item for item in batch.observations if item.value_status=="reported"}
    assert by_form["802"].subject.namespace=="cbr.banking_group.registration"
    assert by_form["101"].subject.namespace=="cbr.bank.registration"
    assert by_form["802"].value==Decimal("1.2300")
    assert by_form["802"].value.as_tuple().exponent==-4
    assert by_form["802"].metric.unit=="RUB" and by_form["802"].metric.scale==Decimal(1000)
    assert "record:1/field:VSEGO" in by_form["802"].evidence_ref
    assert by_form["802"].raw_token=="000001.2300"
    assert by_form["101"].perimeter=="credit_institution"
    assert {(use.coordinate.source_id, use.coordinate.source_group_id, use.coordinate.issue_id) for use in batch.source_uses} == {
        ("cbr.reporting_forms.f101", "reported_records", DAY.isoformat()),
        ("cbr.reporting_forms.f802", "reported_records", DAY.isoformat())}


def test_flow_alignment_requires_an_explicit_interval():
    snapshot=parse("102",("REGN","CODE","SIM_ITOGO"),(("1000","11101","100"),))
    refused=forms.align_forms(forms.AlignFormRequest((snapshot,),"forms.observations","v1"))
    assert refused.outcome=="failed" and refused.diagnostics[0].code=="request.form_flow_period_required"
    period=PeriodRef("interval",start=date(2026,1,1),end=date(2026,3,31))
    admitted=ok(forms.align_forms(forms.AlignFormRequest((snapshot,),"forms.observations","v1",((DAY,period),))))
    assert admitted.observations[0].period==period
    assert admitted.observations[0].metric.quantity_kind=="flow"


def test_alignment_distinguishes_blank_zero_and_absent_optional_measure():
    snapshot=parse("802",("REGN_GKO","STR","VSEGO","KORR_P"),(("1000","14","0",""),))
    batch=ok(forms.align_forms(forms.AlignFormRequest((snapshot,),"forms.observations","v1")))
    channels={dict(item.dimensions)["measure"]:item for item in batch.observations}
    assert channels["total"].value==Decimal(0) and channels["total"].value_status=="reported"
    assert channels["consolidation_plus"].value_status=="blank"
    assert channels["consolidation_minus"].value_status=="missing"


def test_source_comparison_reads_all_members_without_a_financial_model():
    key=forms.FormKey("803",DAY)
    before=ok(forms.extract_forms(forms.ExtractFormRequest(key,source(("CODE","VALUE"),(("0001","10"),)))))
    after=ok(forms.extract_forms(forms.ExtractFormRequest(key,source(("CODE","VALUE"),(("0001","11"),)))))
    changed=ok(forms.compare_sources(forms.CompareFormFlakesRequest(after,before,"available")))
    assert changed.state=="revised" and changed.layers.facts=="changed"
    initial=ok(forms.compare_sources(forms.CompareFormFlakesRequest(before,baseline_state="confirmed_absent")))
    assert initial.state=="first_seen"
    readable=ok(forms.make_readable(after))
    assert '"0001", "11"' in readable.data.decode()


def test_unknown_discovered_form_is_retained_as_an_unsupported_candidate():
    inventory=ok(forms.discover_sources(forms.DiscoverFormsRequest(
        SourcePayload(b'<a href="/vfs/credit/forms/999-20260401.rar">source</a>',"text/html"))))
    assert inventory.sources==()
    assert inventory.unsupported_sources[0][0].key.code=="999"
    assert inventory.unsupported_sources[0][1]=="source.form_profile_unsupported"
    key=forms.FormKey("999",DAY)
    selected=forms.select_sources(forms.SelectFormSourcesRequest((key,)))
    extracted=forms.extract_forms(forms.ExtractFormRequest(key,SourcePayload(b"unadmitted")))
    for rejected in (selected,extracted):
        assert rejected.outcome=="failed"
        assert rejected.diagnostics[0].code=="source.form_profile_unsupported"


def test_integrated_observations_can_continue_after_their_own_snapshot():
    snapshot=parse("802",("REGN_GKO","STR","VSEGO"),(("1000","14","1.2300"),))
    aligned=ok(forms.align_forms(forms.AlignFormRequest((snapshot,),"logical.forms","release-1")))
    encoded=ok(forms.snapshot_observations(forms.SnapshotFormObservationsRequest(aligned,"stored.forms","version-1")))
    restored=ok(forms.restore_observations(encoded))
    assert restored==aligned


def test_normalized_calculated_and_prepared_forms_retain_source_coordinates():
    normalized = parse("802", ("REGN_GKO", "STR", "VSEGO"), (("1000", "14", "1.23"),))
    data = ok(forms.build_form_data(forms.BuildFormDataRequest((normalized,))))
    views = ok(forms.build_form_views(data))
    assert normalized.source_uses and data.source_uses == normalized.source_uses == views.source_uses
    for value, restore in ((normalized, forms.restore_normalized), (data, forms.restore_data), (views, forms.restore_views)):
        snapshot = ok(forms.snapshot_result(forms.FormResultSnapshotRequest(value, "caller.dataset", "caller.release")))
        replayed = ok(restore(snapshot))
        assert replayed.source_uses == value.source_uses
        assert {(use.coordinate.source_id, use.coordinate.issue_id) for use in replayed.source_uses} == {
            ("cbr.reporting_forms.f802", DAY.isoformat())}
