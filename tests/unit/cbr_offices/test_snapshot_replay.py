"""Portable shared-value storage preserves exact source qualification."""
from dataclasses import replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from stratbox.capabilities.catalog.domains import DomainCatalog
from stratbox.capabilities.model.targets import SeriesTarget
from stratbox.core.commands.standard import value_decode
from stratbox.domains.cbr.domain import DOMAIN
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material, SourceDataset

from .helpers import BANK, CAPTURED, OFFICIAL, TERRITORY, bank_evidence, call, compare, context, roundtrip, territorial_tables, workbook


@pytest.mark.parametrize("official", (None, OFFICIAL))
def test_portable_dataset_replay_keeps_dates_and_never_reparses_html(tmp_path, monkeypatch, official):
    material, tables, dataset = bank_evidence(official=official)
    from stratbox.domains.cbr.methods.tables.service_network.bank_offices import parser
    monkeypatch.setattr(parser, "extract_records", lambda **_: pytest.fail("Replay reparsed HTML"))
    restored = roundtrip(tmp_path / "retained.json", {"material": material, "tables": tables, "dataset": dataset})
    assert restored["dataset"] == dataset and restored["tables"] == tables
    assert restored["material"].data == material.data
    assert compare(restored["dataset"], dataset)["changes"] == ()
    assert restored["dataset"].semantics["captured_on"] == CAPTURED.isoformat()
    assert restored["dataset"].semantics["official_as_of"] == (official.isoformat() if official else None)
    assert {row["period_kind"] for row in dataset.rows} == {"as_of" if official else "capture"}


def test_shared_codec_replays_evidence_across_a_fresh_process(tmp_path):
    dataset = bank_evidence()[2]
    path = tmp_path / "office_observations.json"
    roundtrip(path, dataset)
    script = """
import json, sys
from stratbox.core.commands.standard import value_decode
dataset = value_decode({'representation': open(sys.argv[1], 'rb').read()}, None, None)['value']
print(json.dumps({'identity': dataset.identity, 'captured': dataset.semantics['captured_on'],
    'official': dataset.semantics['official_as_of'], 'periods': sorted({row['period'] for row in dataset.rows})}))
"""
    environment = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[3] / "src")}
    process = subprocess.run([sys.executable, "-B", "-c", script, str(path)], env=environment,
        check=True, text=True, capture_output=True)
    assert json.loads(process.stdout) == {"identity": dataset.identity, "captured": "2026-11-22",
        "official": "2026-11-01", "periods": ["2026-11-01"]}


def test_source_acquisition_time_is_retained_without_claiming_a_new_observation(tmp_path):
    material, tables, dataset = bank_evidence()
    observed = datetime(2026, 11, 21, 23, 30, tzinfo=timezone.utc)
    material = replace(material, metadata={"observed_at_utc": observed,
        "final_url": "https://www.cbr.ru", "provenance": "provider_reported"})
    restored = roundtrip(tmp_path / "acquisition.json", {"material": material, "dataset": dataset})
    assert restored["material"].metadata["observed_at_utc"] == observed
    assert restored["material"].metadata["provenance"] == "provider_reported"
    assert restored["material"].identity == tables.material.identity
    assert restored["dataset"].semantics["captured_on"] == "2026-11-22"


@pytest.mark.parametrize("fragment", (False, True))
def test_territory_selection_formula_unknown_fields_and_scope_survive(tmp_path, monkeypatch, fragment):
    parameters = {"national_row": 3, "last_row": 5} if fragment else {}
    tables = territorial_tables(**parameters)
    dataset = call(TERRITORY, "command.table.interpret", {"tables": tables}, as_of=OFFICIAL)["dataset"]
    assert dataset.assessment.status == "partial"
    assert set(dataset.semantics["excluded_fields"]) == {"Мобильные офисы", "Дополнительная отметка"}
    assert tables.metadata["formula_lineage"]["3"]["4"]["cache_missing"]
    assert "Новая территория 000" in {row["subject"] for row in dataset.rows}
    assert tables.metadata["column_order"] == (1, 2, 3, 4, 5, 6)
    assert tables.metadata["header_rows"] == (2,)
    assert tables.metadata["scope"] == ("selected_fragment" if fragment else "published_table")
    assert all(row["unit"] == "count" for row in dataset.rows)
    from stratbox.domains.cbr.methods.tables.service_network.territorial_offices import parser
    monkeypatch.setattr(parser, "convert_xlsx", lambda *_args, **_kwargs: pytest.fail("Replay parsed XLSX"))
    restored = roundtrip(tmp_path / "territory.json", {"tables": tables, "dataset": dataset})
    assert restored["dataset"] == dataset and restored["tables"] == tables


def test_material_csv_alone_cannot_claim_workbook_formula_and_selection_evidence():
    tables = territorial_tables(national_row=3, last_row=5)
    literal = Material(tables.metadata["csv"], "text/csv", TERRITORY)
    with pytest.raises(ValueError, match="workbook_evidence_required"):
        call(TERRITORY, "command.table.extract", {"physical": literal}, as_of=OFFICIAL)


def test_all_ambiguous_candidates_remain_visible_and_no_block_is_chosen():
    from stratbox.domains.cbr.methods.tables.service_network.territorial_offices.parser import AmbiguousBlock
    with pytest.raises(AmbiguousBlock) as failure:
        territorial_tables(data=workbook(copies=35))
    assert len(failure.value.candidates) == 35
    assert len({item[0] for item in failure.value.candidates}) == 35
    selected = territorial_tables(data=workbook(copies=35), sheet="Published observations")
    assert selected.metadata["sheet"] == "Published observations"


def test_explicit_material_period_and_source_bindings_cannot_be_contradicted():
    tables = territorial_tables()
    with pytest.raises(ValueError, match="source|evidence_required"):
        call(BANK, "command.table.interpret", {"tables": tables}, captured_on=CAPTURED, official_as_of=OFFICIAL)
    with pytest.raises(Exception, match="XLSX_REPORT_DATE_MISMATCH"):
        territorial_tables(as_of="2026-10-01")


def test_codec_rejects_unadmitted_type_locators():
    malformed = json.dumps({"type": "untrusted.module:release", "fields": {}}).encode()
    with pytest.raises(ValueError, match="type_not_admitted"):
        value_decode({"representation": malformed}, None, context())


def test_sdk_standard_document_route_keeps_both_dates():
    material = bank_evidence()[0]
    with StrategyBox(domains=DomainCatalog({"cbr": DOMAIN})) as box:
        result = box.invoke("operation.series.extract_document", inputs={"material": material},
            target=SeriesTarget(BANK), parameters={"captured_on": str(CAPTURED), "official_as_of": str(OFFICIAL)}, timeout=10)
        assert result.outcome == "succeeded", result.diagnostics
        dataset = result.output("dataset")
        assert isinstance(dataset, SourceDataset)
        assert dataset.semantics["captured_on"] == str(CAPTURED)
        assert dataset.semantics["official_as_of"] == str(OFFICIAL)
        assert all(row["period"] == str(OFFICIAL) for row in dataset.rows)
