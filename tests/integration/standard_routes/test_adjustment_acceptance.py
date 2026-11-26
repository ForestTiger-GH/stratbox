"""A successful provider call cannot substitute an arbitrary value for an adjustment."""
import pytest

from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import TimeSeries


@pytest.mark.parametrize("bad_result",["not an adjustment",None,{}, {"values":()}])
def test_malformed_numerical_provider_output_is_not_accepted(bad_result):
    class Provider:
        def adjust(self,series,**kwargs):
            return bad_result
        def diagnose(self,adjustment,**kwargs):
            return {}
    series=TimeSeries({"metric":"reviewed.amount"},("2026-01","2026-02"),(1,2),"RUB","monthly","stock")
    with StrategyBox(providers={"seasonal_adjustment":Provider()}) as box:
        result=box.invoke("operation.timeseries.adjust",inputs={"series":series})
        assert result.outcome=="failed"
        assert not result.outputs
        assert any("adjustment" in str(item) or "acceptance" in str(item) for item in result.diagnostics)
