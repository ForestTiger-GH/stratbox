"""Safe Minfin URL admission and bounded discovery from real page HTML.

Discovery yields *candidates*. The page's inventory completeness and economic
issue dates are unknown until independently qualified from publisher evidence.
"""
from __future__ import annotations

from hashlib import sha256
from html import unescape
from html.parser import HTMLParser
from urllib.parse import unquote, urljoin, urlsplit

from stratbox.core.network import HttpRequest, HttpsEndpoint
from stratbox.core.network.contracts import public_https_parts
from stratbox.shared.evidence import SourcePayload

from .models import Asset, PublicationIndex, SourceFamily

_HOSTS = ("minfin.gov.ru", "www.minfin.gov.ru")
_STORAGE = ("/common/upload/library/", "/upload/")
_FORM = {"xlsx", "xls", "xlsm", "csv", "zip", "pdf", "doc", "docx"}
PAGE_MIMES = frozenset({"text/html", "application/xhtml+xml"})
FILE_MIMES = frozenset({
    "application/octet-stream", "application/force-download", "application/x-binary",
    "application/zip", "application/x-zip-compressed", "application/pdf",
    "application/vnd.ms-excel", "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel.sheet.macroenabled.12",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "text/csv", "text/plain",
})


def allowed_page(url: str) -> bool:
    try:
        p = public_https_parts(url)
    except (ValueError, TypeError):
        return False
    return p.hostname in _HOSTS and p.path.startswith("/ru/") and not p.query


def allowed_file(url: str, *, extension: str | None = None) -> bool:
    try:
        p = public_https_parts(url)
        path = unquote(p.path, errors="strict")
    except (ValueError, TypeError):
        return False
    ext = path.rsplit("/", 1)[-1].rsplit(".", 1)[-1].lower()
    return (
        p.hostname in _HOSTS and any(path.startswith(root) for root in _STORAGE)
        and ext in _FORM and (extension is None or ext == extension)
        and not p.query
    )


def page_request(url: str, *, limit: int = 8 * 1024 * 1024) -> HttpRequest:
    if not allowed_page(url):
        raise ValueError("minfin.page_forbidden")
    return HttpRequest(
        "GET", url,
        tuple(HttpsEndpoint(host, urlsplit(url).path) for host in _HOSTS),
        headers={"Accept": "text/html,application/xhtml+xml"},
        deadline_seconds=60, max_response_bytes=limit,
    )


def file_request(url: str, *, limit: int, deadline: int) -> HttpRequest:
    if not allowed_file(url):
        raise ValueError("minfin.asset_url_forbidden")
    return HttpRequest(
        "GET", url,
        tuple(HttpsEndpoint(host, root, subtree=True) for host in _HOSTS for root in _STORAGE),
        headers={"Accept": "application/octet-stream,*/*"},
        deadline_seconds=deadline, max_response_bytes=limit,
    )


class _Anchors(HTMLParser):
    def __init__(self, max_links: int):
        super().__init__(convert_charrefs=True)
        self.max_links = max_links
        self.links: list[tuple[str, str]] = []
        self.current_href: str | None = None
        self.text: list[str] = []
        self.title: str = ""
        self.bad_base = False
        self.overflow = False

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag.lower() == "base":
            self.bad_base = True  # Do not allow untrusted HTML to change URL resolution.
        if tag.lower() == "a":
            self.current_href = values.get("href")
            self.text = []
            self.title = values.get("title") or ""

    def handle_data(self, data):
        if self.current_href is not None and sum(map(len, self.text)) < 4096:
            self.text.append(data[:4096])

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self.current_href is not None:
            if len(self.links) >= self.max_links:
                self.overflow = True
            else:
                self.links.append((self.current_href, (self.title.strip() or "".join(self.text).strip())[:2048]))
            self.current_href = None
            self.text = []
            self.title = ""


def discover_links(family: SourceFamily, index: SourcePayload, max_links: int = 2000) -> PublicationIndex:
    if type(max_links) is not int or not 1 <= max_links <= 5000:
        raise ValueError("minfin.index_limit_invalid")
    if index.media_type not in PAGE_MIMES or index.identity.size > 8 * 1024 * 1024:
        raise ValueError("minfin.index_invalid_media")
    if index.source_id not in {None, family.family_id + ".index"}:
        raise ValueError("minfin.index_wrong_source")
    try:
        html = index.data.decode(index.charset or "utf-8", errors="strict")
    except (UnicodeError, LookupError):
        raise ValueError("minfin.index_invalid_charset") from None
    if "\x00" in html or "\ufffd" in html:
        raise ValueError("minfin.index_invalid_charset")
    parser = _Anchors(max_links)
    parser.feed(html)
    parser.close()
    if parser.bad_base or parser.overflow:
        raise ValueError("minfin.index_untrusted_or_oversized")
    if not parser.links:
        raise ValueError("minfin.index_no_links")
    unique: dict[str, Asset] = {}
    rejected = 0
    for raw, label in parser.links:
        if not isinstance(raw, str) or len(raw) > 8192:
            rejected += 1
            continue
        url = urljoin(family.landing_url, unescape(raw.strip()))
        if not allowed_file(url):
            rejected += 1
            continue
        filename = unquote(urlsplit(url).path.rsplit("/", 1)[-1])
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext not in family.formats:
            rejected += 1
            continue
        variants = tuple(v for v in family.variants if filename.casefold().startswith(v.prefix.casefold()) and filename.casefold().endswith(v.suffix.casefold()))
        if len(variants) > 1:
            raise ValueError("minfin.index_variant_overlap")
        variant = variants[0] if variants else None
        asset_id = variant.asset_id if variant else "file_" + sha256(urlsplit(url).path.encode()).hexdigest()[:24]
        asset = Asset(family.family_id, variant.source_id if variant else family.default_source_id,
                      asset_id, url, filename, ext, label,
                      "registered_variant" if variant else "unclassified", index.identity)
        unique[url] = asset
    assets = tuple(sorted(unique.values(), key=lambda x: (x.source_id, x.filename, x.url)))
    ambiguous_ids = tuple(sorted(asset_id for asset_id in {a.asset_id for a in assets}
                                 if sum(a.asset_id == asset_id for a in assets) > 1))
    # Keep ambiguous candidates visible; require explicit URL selection to acquire.
    return PublicationIndex(family.family_id, assets, index.identity, rejected_links=rejected,
                            ambiguous_asset_ids=ambiguous_ids)


def check_asset(asset: Asset, family: SourceFamily) -> None:
    if asset.family_id != family.family_id or not allowed_file(asset.url, extension=asset.format):
        raise ValueError("minfin.asset_forbidden")
    if unquote(urlsplit(asset.url).path.rsplit("/", 1)[-1]) != asset.filename:
        raise ValueError("minfin.asset_filename_mismatch")
    if asset.format not in family.formats or asset.index_identity.size <= 0:
        raise ValueError("minfin.asset_unqualified")
    matched = tuple(v for v in family.variants if asset.filename.casefold().startswith(v.prefix.casefold()) and asset.filename.casefold().endswith(v.suffix.casefold()))
    if len(matched) > 1:
        raise ValueError("minfin.asset_ambiguous")
    expected = matched[0] if matched else None
    if asset.source_id != (expected.source_id if expected else family.default_source_id):
        raise ValueError("minfin.asset_source_mismatch")
    expected_id = expected.asset_id if expected else "file_" + sha256(urlsplit(asset.url).path.encode()).hexdigest()[:24]
    if asset.asset_id != expected_id or asset.recognition != ("registered_variant" if expected else "unclassified"):
        raise ValueError("minfin.asset_identity_mismatch")


__all__ = ("allowed_page", "allowed_file", "page_request", "file_request", "discover_links", "check_asset", "FILE_MIMES", "PAGE_MIMES")