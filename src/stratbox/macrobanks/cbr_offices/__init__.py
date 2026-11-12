"""Daily Bank of Russia office observations."""

from stratbox.data.releases import CompareReleaseRequest, ReadReleaseRequest

from .contracts import AcquiredOffices, AcquireOfficesRequest, ParseOfficesRequest
from .operations import ACQUIRE, CAPTURE, COMPARE, PARSE, READ, acquire, capture, compare, parse, read_representation
