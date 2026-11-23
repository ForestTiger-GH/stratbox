"""Source health and source byte change are separate interpretations."""

from datetime import datetime, timezone

from stratbox.core.operations.source.checks import assess_source_check
from stratbox.core.operations.source.version_comparison import (
    CompareOriginalVersionsRequest, OriginalVersion, compare_original_versions,
)
from stratbox.domains.rosstat.publications.contracts import DiscoverRosstatRequest
from stratbox.domains.rosstat.operations.publications import discover
from stratbox.shared.evidence import SourcePayload
from stratbox.shared.identity import ByteIdentity


def test_unverified_page_is_not_authoritative():
    series = "rosstat.short_term_indicators"
    index = SourcePayload(
        b'<a href="/storage/mediabank/2026-08.xlsx">2026-08</a>',
        "text/html", series + ".index",
    )
    result = discover(DiscoverRosstatRequest(series, index))
    check = assess_source_check(
        result, checked_at_utc=datetime.now(timezone.utc),
        qualified_source_index=result.value.live_profile_verified,
    )
    assert check.state == "unverified" and not check.confirms_no_change


def test_missing_page_is_not_unchanged_original():
    series = "rosstat.short_term_indicators"
    missing = discover(DiscoverRosstatRequest(
        series, SourcePayload(b"<html>empty</html>", "text/html", series + ".index"),
    ))
    check = assess_source_check(missing, checked_at_utc=datetime.now(timezone.utc))
    assert check.state == "failed"
    source = OriginalVersion("rosstat.test", ByteIdentity.of(b"bytes"))
    comparison = compare_original_versions(
        CompareOriginalVersionsRequest(source, "unavailable")
    )
    assert comparison.value.state == "indeterminate"
    assert not check.confirms_no_change
