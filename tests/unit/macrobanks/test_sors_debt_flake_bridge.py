"""The same regional source projection can start from XLSX or a retained flake."""
from dataclasses import replace

import pandas as pd
import pytest

from stratbox.shared.evidence import SourcePayload
from stratbox.domains.cbr.corporate_lending.industries import debt_0105a as debt
from stratbox.domains.cbr.corporate_lending.sors_restoration.dependencies import original_input
from stratbox.domains.cbr.corporate_lending.sors_restoration.publication import RoundingPolicy
from stratbox.domains.cbr.corporate_lending.sors_restoration.sources.regional_traditional import (
    parse_regional_traditional, regional_traditional_from_flake,
)

from test_cbr_industries_0105a_debt_corp import _workbook_bytes


def _parse(selection=debt.IndustrySelection()):
    content = _workbook_bytes(report_date="01.02.2019", kemerovo_name="Кемеровская область")
    parsed = debt.parse(debt.ParseIndustryRequest(SourcePayload(content),
        "01_05_A_Debt_corp_20190201.xlsx", selection=selection))
    assert parsed.outcome == "succeeded", parsed.diagnostics
    return content, parsed.value


def test_retained_debt_flake_matches_direct_sors_source_projection():
    content, parsed = _parse()
    snapshot = debt.build_flake_snapshot(debt.IndustrySnapshotRequest(parsed, "test.debt", "2019-02"))
    assert snapshot.outcome == "succeeded", snapshot.diagnostics
    restored = debt.read_flake_snapshot(debt.ReadIndustrySnapshotRequest(snapshot.value))
    assert restored.outcome == "succeeded", restored.diagnostics
    original = [receipt.identity for receipt in restored.value.evidence.inputs
                if receipt.identity.sha256 == parsed.source_sha256]
    assert len(original) == 1 and original[0].size == len(content)
    reused = original_input(restored.value, "01_05_A")
    assert reused.identity == SourcePayload(content).identity
    assert reused.source_id == parsed.source_id
    assert reused.role == "01_05_A" and reused.availability == "reference_only"
    for step in (1.0, 0.1):
        policy = RoundingPolicy(step=step)
        direct = parse_regional_traditional(SourcePayload(content, source_id=parsed.source_id), "2019-02-01", policy)
        replayed = regional_traditional_from_flake(restored.value, "2019-02-01", policy)
        for expected, actual in zip(direct, replayed, strict=True):
            pd.testing.assert_frame_equal(expected, actual)
        assert set(replayed[0]["source_sha256"].dropna()) == {parsed.source_sha256}


def test_sors_rejects_partial_edited_and_wrong_date_flakes():
    _, partial = _parse(debt.IndustrySelection(("total",)))
    with pytest.raises(ValueError, match="incomplete"):
        regional_traditional_from_flake(partial, "2019-02-01", RoundingPolicy())
    _, complete = _parse()
    with pytest.raises(ValueError, match="differs"):
        regional_traditional_from_flake(complete, "2019-03-01", RoundingPolicy())
    changed = replace(complete, df_stream=complete.df_stream.copy())
    changed.df_stream.loc[0, "value"] = 999.0
    with pytest.raises(ValueError, match="identity_mismatch"):
        regional_traditional_from_flake(changed, "2019-02-01", RoundingPolicy())
    with pytest.raises(ValueError, match="policy_invalid"):
        regional_traditional_from_flake(complete, "2019-02-01", RoundingPolicy(step=float("inf")))
