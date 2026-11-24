"""Bounded source-index discovery independent of publisher identity."""
from html.parser import HTMLParser
import re
from urllib.parse import urljoin

from stratbox.core.execution.contracts import OperationFailure
from stratbox.shared.evidence import SourcePayload


def index_links(request, invocation):
    material = request["material"]
    if not isinstance(material, SourcePayload):
        raise OperationFailure("index.material_required")
    limit = request.get("max_links", 10_000)
    links = []
    class Reader(HTMLParser):
        def handle_starttag(self, tag, attrs):
            invocation.check_cancelled()
            if tag.casefold() == "a":
                href = dict(attrs).get("href")
                if href:
                    if len(links) >= limit:
                        raise OperationFailure("index.link_limit")
                    links.append(urljoin(request["base_url"], href))
    parser = Reader(convert_charrefs=True)
    parser.feed(material.data.decode(request.get("encoding", material.charset or "utf-8")))
    parser.close()
    return tuple(dict.fromkeys(links))


def index_select(request, invocation):
    """Select one declared relationship, rejecting absent or ambiguous members."""
    pattern = request["pattern"]
    if not isinstance(pattern, str) or len(pattern) > 2048:
        raise OperationFailure("index.pattern_invalid")
    selected = [url for url in request["links"] if re.search(pattern, url.rsplit("/", 1)[-1])]
    if len(selected) != 1:
        raise OperationFailure("index.member_missing" if not selected else "index.member_ambiguous")
    return selected[0]
