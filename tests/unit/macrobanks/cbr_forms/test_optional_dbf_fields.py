from __future__ import annotations

from pathlib import Path

import pandas as pd

from stratbox.macrobanks.cbr_forms.common import dbf_picker, runner


def test_picker_accepts_802_dbf_without_optional_korr_gr(tmp_path: Path, monkeypatch) -> None:
    pk = tmp_path / "PK8022512.dbf"
    meta = tmp_path / "F802META.dbf"
    pk.write_bytes(b"x")
    meta.write_bytes(b"x")

    fields_by_name = {
        "PK8022512.dbf": ["REGN_GKO", "STR", "KORR_P", "KORR_M", "VSEGO"],
        "F802META.dbf": ["FSORT", "FRAZD", "FSECTION", "FSTR", "FVALUE"],
    }

    class FakeDBF:
        def __init__(self, path: str, **kwargs):
            self.field_names = fields_by_name[Path(path).name]

    monkeypatch.setattr(dbf_picker, "DBF", FakeDBF)

    chosen, field_map = dbf_picker.pick_dbf_fields(
        tmp_path,
        field_candidates={
            "REGN": ("REGN_GKO",),
            "CODE": ("STR",),
            "total": ("VSEGO",),
        },
        optional_field_candidates={
            "consolidation_plus": ("KORR_P",),
            "consolidation_minus": ("KORR_M",),
            "intragroup_adjustment": ("KORR_GR",),
        },
        prefer_stem_contains="PK802",
    )

    assert chosen.name == "PK8022512.dbf"
    assert field_map == {
        "REGN": "REGN_GKO",
        "CODE": "STR",
        "total": "VSEGO",
        "consolidation_plus": "KORR_P",
        "consolidation_minus": "KORR_M",
    }


def test_picker_reads_korr_gr_when_current_802_schema_contains_it(tmp_path: Path, monkeypatch) -> None:
    pk = tmp_path / "PK8022603.dbf"
    pk.write_bytes(b"x")

    class FakeDBF:
        def __init__(self, path: str, **kwargs):
            self.field_names = [
                "REGN_GKO",
                "STR",
                "KORR_P",
                "KORR_M",
                "KORR_GR",
                "VSEGO",
            ]

    monkeypatch.setattr(dbf_picker, "DBF", FakeDBF)

    _, field_map = dbf_picker.pick_dbf_fields(
        tmp_path,
        field_candidates={
            "REGN": ("REGN_GKO",),
            "CODE": ("STR",),
            "total": ("VSEGO",),
        },
        optional_field_candidates={
            "consolidation_plus": ("KORR_P",),
            "consolidation_minus": ("KORR_M",),
            "intragroup_adjustment": ("KORR_GR",),
        },
        prefer_stem_contains="PK802",
    )

    assert field_map["intragroup_adjustment"] == "KORR_GR"


def test_runner_fills_missing_optional_physical_columns(monkeypatch, tmp_path: Path) -> None:
    class Result:
        ok = True
        content = b"rar"

    def fake_make_workdir(prefix: str) -> str:
        work = tmp_path / "work"
        work.mkdir(parents=True, exist_ok=True)
        return str(work)

    monkeypatch.setattr(runner, "make_workdir", fake_make_workdir)
    monkeypatch.setattr(runner, "download_bytes", lambda **kwargs: Result())
    monkeypatch.setattr(runner, "_extract_rar", lambda archive_path, out_dir: out_dir.mkdir(parents=True, exist_ok=True))
    monkeypatch.setattr(
        runner,
        "pick_dbf_fields",
        lambda extracted_dir, **kwargs: (
            extracted_dir / "PK8022512.dbf",
            {
                "REGN": "REGN_GKO",
                "CODE": "STR",
                "total": "VSEGO",
                "consolidation_plus": "KORR_P",
                "consolidation_minus": "KORR_M",
            },
        ),
    )
    monkeypatch.setattr(
        runner,
        "read_dbf_columns",
        lambda path, field_map: pd.DataFrame(
            [
                {
                    "REGN": 1000,
                    "CODE": "14",
                    "total": 10,
                    "consolidation_plus": None,
                    "consolidation_minus": None,
                }
            ]
        ),
    )

    loaded = runner.run_dates_to_selected_dbf_df(
        dates=[pd.Timestamp("2026-01-01")],
        build_url=lambda date: "https://example.invalid/802.rar",
        field_candidates={
            "REGN": ("REGN_GKO",),
            "CODE": ("STR",),
            "total": ("VSEGO",),
        },
        optional_field_candidates={
            "consolidation_plus": ("KORR_P",),
            "consolidation_minus": ("KORR_M",),
            "intragroup_adjustment": ("KORR_GR",),
        },
        prefer_stem_contains="PK802",
        show_progress=False,
    )

    assert len(loaded) == 1
    _, frame = loaded[0]
    assert frame.columns.tolist() == [
        "REGN",
        "CODE",
        "total",
        "consolidation_plus",
        "consolidation_minus",
        "intragroup_adjustment",
    ]
    assert pd.isna(frame.loc[0, "intragroup_adjustment"])
