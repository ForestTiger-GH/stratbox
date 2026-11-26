"""Real standard archive topology preserves an issue and selects form-bearing DBFs."""
import pytest

from stratbox.core.formats.archives.members import zip_bytes
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material
from tests.unit.macrobanks.cbr_forms.support import character_dbf

SOURCE="cbr.reporting_forms.f802"
ISSUE="2026-04-01"


@pytest.mark.parametrize("with_companions",[False,True])
def test_full_sdk_archive_keeps_issue_context_and_selects_only_form_tables(with_companions):
    files={"PK802.dbf":character_dbf(("REGN_GKO","STR","VSEGO"),(("1000","14","10"),))}
    if with_companions:
        files.update({"F802META.dbf":character_dbf(("FSORT","FRAZD"),(("1","2"),)),
            "readme.txt":b"Publisher archive companion"})
    original=Material(zip_bytes(files),"application/zip",SOURCE,metadata={"issue_id":ISSUE})
    with StrategyBox() as box:
        result=box.invoke("operation.series.extract_archive",target=SOURCE,
            inputs={"material":original,"issue":{"issue_id":ISSUE}},
            parameters={"format":"zip","issue_id":ISSUE})
        assert result.outcome=="succeeded",result.diagnostics
        dataset=result.output("dataset")
        assert dataset.issue_id==ISSUE
        assert len(dataset.rows)==1 and dataset.rows[0]["value"]==10
        assert dataset.rows[0]["raw_token"]=="10"
        assert dataset.source_uses and dataset.source_uses[0].coordinate.issue_id==ISSUE
        assert "record=1&field=VSEGO" in dataset.rows[0]["evidence_ref"]
