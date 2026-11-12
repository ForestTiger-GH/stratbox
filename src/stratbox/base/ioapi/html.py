"""Small HTML primitives for source discovery."""

from html.parser import HTMLParser


class LinkTargets(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            target = dict(attrs).get("href")
            if target is not None and target.strip():
                self.links.append(target.strip())


def link_targets(html: str) -> tuple[str, ...]:
    parser = LinkTargets()
    parser.feed(html)
    parser.close()
    return tuple(parser.links)
