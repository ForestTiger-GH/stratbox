"""
xml — чтение/запись XML поверх FileStore.

По умолчанию возвращается ElementTree.Element (root).
Дальнейший разбор выполняется доменным кодом.
"""

from __future__ import annotations

from io import BytesIO
from xml.etree import ElementTree as ET

from stratbox.base.filestore.base import FileStore
from stratbox.base.ioapi.bytes import read_bytes, write_bytes


def read_root(path: str, store: FileStore | None = None) -> ET.Element:
    data = read_bytes(path, store=store)
    return ET.fromstring(data)


def write_root(path: str, root: ET.Element, store: FileStore | None = None, encoding: str = "utf-8") -> None:
    bio = BytesIO()
    ET.ElementTree(root).write(bio, encoding=encoding, xml_declaration=True)
    write_bytes(path, bio.getvalue(), store=store)