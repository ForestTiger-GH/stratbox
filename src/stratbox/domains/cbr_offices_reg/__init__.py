"""Monthly Bank of Russia office releases by territory."""

from stratbox.shared.data.releases import CompareReleaseRequest, ReadReleaseRequest, ReleaseLink

from .operations import (
    ACQUIRE, CAPTURE, COMPARE, DISCOVER, PARSE, READ, DiscoverOfficesRegRequest,
    OfficesRegCandidates, ParseOfficesRegRequest,
    acquire, capture, compare, discover, parse, read_representation,
)
