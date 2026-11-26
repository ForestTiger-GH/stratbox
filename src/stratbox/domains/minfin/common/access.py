"""Shared official fiscal publication addresses and access facts."""
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit


@dataclass(frozen=True)
class AccessSettings:
    id: str = "minfin.public_statistics"
    hosts: frozenset[str] = frozenset({"minfin.gov.ru", "www.minfin.gov.ru"})
    index_bytes: int = 8 * 1024 * 1024
    asset_bytes: int = 64 * 1024 * 1024


ACCESS = AccessSettings()
FEDERAL_INDEX = "https://minfin.gov.ru/ru/statistics/fedbud/execute/"
CONSOLIDATED_INDEX = "https://minfin.gov.ru/ru/statistics/conbud/execute"
REGIONAL_INDEX = "https://minfin.gov.ru/ru/statistics/subbud/execute"
FUND_INDEX = "https://minfin.gov.ru/ru/perfomance/nationalwealthfund/statistics/"


def allowed_url(url, *, asset=False):
    try:
        parts = urlsplit(url)
        path = unquote(parts.path, errors="strict")
    except (TypeError, ValueError, UnicodeError):
        return False
    if (parts.scheme != "https" or parts.hostname not in ACCESS.hosts or parts.username
            or parts.password or parts.query or parts.fragment or ".." in path.split("/")):
        return False
    if asset:
        return path.startswith(("/common/upload/library/", "/upload/")) and path.rsplit(".", 1)[-1].casefold() in {
            "xlsx", "xls", "xlsm", "csv", "zip", "pdf", "doc", "docx"}
    return path.startswith("/ru/")
