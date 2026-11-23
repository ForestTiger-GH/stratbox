"""Source captures, alignment, count changes and retained products remain independent."""
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path
from io import BytesIO

from openpyxl import load_workbook
from stratbox.domains.cbr.operations import service_network as network
from stratbox.domains.cbr.operations.service_network import bank_offices as daily
from stratbox.shared.data.releases import CompareReleaseRequest
from stratbox.shared.data.observations import SubjectRef
from stratbox.shared.data.observation_snapshots import observation_snapshot
from stratbox.shared.evidence import SourcePayload
from stratbox.core.storage.datasets import operations as datasets
from stratbox.core.storage.datasets.files import FileDatasetStore
from stratbox.core.storage.filestore.local import LocalFileStore

HTML=Path(__file__).resolve().parents[2]/"fixtures/universal_core/offices-basic.html"
FIRST=date(2026,11,22)
SECOND=date(2026,11,23)
OFFICIAL=date(2026,11,1)

def ok(result):
    assert result.outcome=="succeeded",result.diagnostics
    return result.value

def release(captured=FIRST,official=OFFICIAL):
    return ok(daily.parse(daily.ParseOfficesRequest(SourcePayload(HTML.read_bytes()),captured,official)))

def roundtrip(tmp_path,snapshot):
    store=FileDatasetStore(LocalFileStore(str(tmp_path)),"datasets",provider_id="files",scope_id="test")
    saved=ok(datasets.write_snapshot(datasets.WriteSnapshotRequest(snapshot),store=store))
    reopened=FileDatasetStore(LocalFileStore(str(tmp_path)),"datasets",provider_id="files",scope_id="test")
    return ok(datasets.read_snapshot(datasets.ReadSnapshotRequest(saved.reference),store=reopened))


def test_later_capture_is_not_a_new_publisher_issue():
    before=release();after=release(SECOND)
    same=ok(daily.compare(CompareReleaseRequest(after,before)))
    assert same.state=="unchanged"
    new=release(SECOND,date(2026,12,1))
    changed=ok(daily.compare(CompareReleaseRequest(new,before)))
    assert changed.state=="new_release"
    assert changed.reason=="comparison.official_reference_date_changed"


def test_two_official_issues_captured_the_same_day_remain_distinct_releases():
    before=release();after=release(FIRST,date(2026,12,1))
    compared=ok(daily.compare(CompareReleaseRequest(after,before)))
    assert compared.state=="new_release"
    assert compared.reason=="comparison.official_reference_date_changed"


def test_same_official_issue_keeps_coverage_guards_across_capture_dates():
    import re
    before=release()
    html=re.sub(r"<tr><td>Новый регион.*?</tr>","",HTML.read_text())
    after=ok(daily.parse(daily.ParseOfficesRequest(SourcePayload(html.encode()),SECOND,OFFICIAL)))
    compared=ok(daily.compare(CompareReleaseRequest(after,before)))
    assert compared.state=="indeterminate"
    assert compared.reason=="comparison.coverage_dropped"


def test_unknown_official_date_compares_capture_content_at_its_actual_layer():
    before=release(official=None);after=release(SECOND,None)
    same=ok(daily.compare(CompareReleaseRequest(after,before)))
    assert same.state=="unchanged"
    assert same.reason=="comparison.capture_bytes_unchanged_official_date_unknown"


def test_history_replay_keeps_two_captures_of_the_same_official_state(tmp_path):
    before,after=release(),release(SECOND)
    encoded=ok(network.build_source_history(network.OfficeHistoryRequest((after,before),"office.captures","v1")))
    loaded=roundtrip(tmp_path,encoded)
    restored=ok(network.restore_history(loaded))
    assert restored==(before,after)
    assert all(item.source_details["official_as_of"]==OFFICIAL for item in restored)


def test_alignment_requires_explicit_geography_and_preserves_source_identity():
    source=release();first=source.batch.observations[0]
    refused=network.align_offices(network.AlignOfficesRequest(source,"offices.aligned","v1",require_geography=True))
    assert refused.outcome=="failed" and refused.diagnostics[0].code=="source.office_geography_unresolved"
    labels=sorted({dict(item.dimensions)["region"] for item in source.batch.observations})
    mappings=tuple(network.OfficeRegionMapping(label,"region."+str(i),"geography.edition.1") for i,label in enumerate(labels))
    subjects=(network.OfficeSubjectMapping(first.subject,SubjectRef("bank.canonical","bank-1"),"banks.edition.1"),)
    batch=ok(network.align_offices(network.AlignOfficesRequest(source,"offices.aligned","v1",subjects,mappings,require_geography=True)))
    mapped=next(item for item in batch.observations if item.subject.id=="bank-1")
    assert dict(mapped.dimensions)["source_subject_id"]==first.subject.id
    assert dict(mapped.dimensions)["geography_edition"]=="geography.edition.1"
    assert mapped.metric.quantity_kind=="count"


def test_count_changes_keep_unmatched_coverage_and_render_retained_prepared_views(tmp_path):
    baseline=ok(network.align_offices(network.AlignOfficesRequest(release(),"offices.aligned","old")))
    numeric=next(index for index,item in enumerate(baseline.observations) if item.value_status=="reported")
    observations=list(baseline.observations)
    original=observations[numeric]
    observations[numeric]=replace(original,value=original.value+2)
    candidate=replace(baseline,release_id="new",observations=tuple(observations))
    changes=ok(network.calculate_changes(network.OfficeChangesRequest(baseline,candidate,"offices.delta","v1")))
    assert changes.matched_cells==len(observations)
    assert changes.baseline_only==changes.candidate_only==0
    dependencies={item.role:item.identity for item in changes.batch.lineage}
    assert dependencies["baseline_observations"]==observation_snapshot(baseline).identity
    assert dependencies["candidate_observations"]==observation_snapshot(candidate).identity
    assert any(item.value==2 and item.value_status=="derived" for item in changes.batch.observations)
    view=ok(network.build_view(network.OfficeViewRequest(changes.batch,"offices.view","v1")))
    assert any(item.role=="view_observations" and item.identity==observation_snapshot(changes.batch).identity
               for item in view.manifest.inputs)
    loaded=roundtrip(tmp_path,view)
    rendered=ok(network.render(network.RenderOfficeViewRequest(loaded)))
    book=load_workbook(BytesIO(rendered.data),data_only=True)
    assert book.sheetnames==["Office counts"]
    assert book.active.max_row==len(observations)+1
    book.close()
    csv=ok(network.render(network.RenderOfficeViewRequest(loaded,"csv")))
    assert b"derived" in csv.data


def test_readable_native_html_preserves_all_original_bytes():
    payload=SourcePayload(HTML.read_bytes(),"text/html")
    readable=ok(network.make_readable(network.ReadableOfficesRequest(payload,"bank_offices")))
    assert readable.data==payload.data
    assert readable.media_type=="text/html"


def test_readable_invalid_source_is_a_qualified_source_failure():
    for family in ("bank_offices", "territorial_offices"):
        result=network.make_readable(network.ReadableOfficesRequest(SourcePayload(b"invalid"),family))
        assert result.outcome=="failed"
        assert result.diagnostics[0].code.startswith("source.")


def test_aligned_observations_have_a_retained_boundary_independent_of_source_release(tmp_path):
    batch=ok(network.align_offices(network.AlignOfficesRequest(release(),"logical.offices","release-1")))
    encoded=ok(network.snapshot_observations(network.SnapshotOfficeObservationsRequest(batch,"stored.offices","version-1")))
    restored=ok(network.restore_observations(roundtrip(tmp_path,encoded)))
    assert restored==batch
    view=ok(network.build_view(network.OfficeViewRequest(restored,"office.view","version-1")))
    assert ok(network.render(network.RenderOfficeViewRequest(view,"csv"))).data
