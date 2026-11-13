"""Bounded XML decoding without DTDs or external resolution."""

from __future__ import annotations

from io import BytesIO
from typing import BinaryIO, Callable
from xml.etree import ElementTree as ET
from xml.parsers import expat

from stratbox.base.filestore import FileStore
from stratbox.base.runtime import default_filestore
from stratbox.base.ioapi.bytes import read_bounded_bytes, write_bytes
from stratbox.base.limits import BudgetMeter

MAX_XML_BYTES = 64 * 1024 * 1024
_MAX_NODES = 2_000_000
_MAX_DEPTH = 96


class XmlError(ValueError):
    pass


def inspect_xml(
    stream: BinaryIO, *, budget: BudgetMeter | None = None,
    limit: int = MAX_XML_BYTES,
    start: Callable[[str, dict[str, str]], None] | None = None,
    text_limit: int | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> None:
    """Scan bounded input by bytes and parser events, without building a tree."""
    parser = expat.ParserCreate(namespace_separator="}")
    depth = count = size = 0
    text_sizes: list[int] = []

    def unsupported(*args):
        raise XmlError("xml.dtd_forbidden")

    def opened(name, attributes):
        nonlocal depth, count
        depth += 1
        count += 1
        if depth > _MAX_DEPTH or count > _MAX_NODES or len(attributes) > 128:
            raise XmlError("xml.structure_limit")
        if text_limit is not None:
            text_sizes.append(0)
        if start is not None:
            start(name, attributes)

    def closed(_name):
        nonlocal depth
        depth -= 1
        if text_limit is not None:
            text_sizes.pop()

    def characters(value):
        if text_sizes:
            text_sizes[-1] += len(value)
            if text_sizes[-1] > text_limit:
                raise XmlError("xml.text_limit")

    parser.StartDoctypeDeclHandler = unsupported
    parser.ExternalEntityRefHandler = unsupported
    parser.StartElementHandler = opened
    parser.EndElementHandler = closed
    if text_limit is not None:
        parser.CharacterDataHandler = characters
    try:
        while True:
            if cancelled is not None and cancelled():
                raise XmlError("operation.cancelled")
            if budget is not None:
                budget.checkpoint()
            chunk = stream.read(min(65536, limit - size + 1))
            if not chunk:
                break
            size += len(chunk)
            if budget is not None:
                budget.charge("decoded_bytes", len(chunk))
            if size > limit:
                raise XmlError("xml.size_limit")
            parser.Parse(chunk, False)
        parser.Parse(b"", True)
    except expat.ExpatError:
        raise XmlError("xml.invalid") from None


def parse_xml(
    data: bytes, *, budget: BudgetMeter | None = None, limit: int = MAX_XML_BYTES
) -> ET.Element:
    inspect_xml(BytesIO(data), budget=budget, limit=limit)
    return ET.fromstring(data)


def read_root(path: str, store: FileStore | None = None) -> ET.Element:
    target = default_filestore(store)
    return parse_xml(read_bounded_bytes(path, store=target, limit=MAX_XML_BYTES))


def write_root(path: str, root: ET.Element, store: FileStore | None = None, encoding: str = "utf-8") -> None:
    bio = BytesIO()
    ET.ElementTree(root).write(bio, encoding=encoding, xml_declaration=True)
    write_bytes(path, bio.getvalue(), store=store)
