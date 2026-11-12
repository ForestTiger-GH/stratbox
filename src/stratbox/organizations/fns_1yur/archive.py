from __future__ import annotations

import re

from .history import HistoryError


def member_name(names):
    """First part only: (1), _I, or _I_DATE; never auto-select Part II."""
    valid = [
        name
        for name in names
        if name.lower().endswith((".xls", ".xlsx"))
        and len(name) < 300
        and not name.startswith(("/", "\\"))
        and ".." not in name.replace("\\", "/").split("/")
    ]
    for pattern in (
        r"\(1\)\.xlsx?\Z",
        r"_I\.xlsx?\Z",
        r"_I_[^/\\]+\.xlsx?\Z",
    ):
        selected = [name for name in valid if re.search(pattern, name, flags=re.I)]
        if selected:
            if len(selected) != 1:
                raise HistoryError("MULTIPLE_PART_I_WORKBOOKS")
            return selected[0]
    if len(valid) == 1:
        if re.search(r"_II(?:_[^/\\]+)?\.xlsx?\Z", valid[0], flags=re.I):
            raise HistoryError("SOURCE_ONLY_PART_II_PRESENT")
        return valid[0]
    raise HistoryError("PART_I_WORKBOOK_UNRESOLVED")


from dataclasses import dataclass
from datetime import date

from stratbox.base.ioapi.archive_bytes import (
    ArchiveLimits,
    ArchiveReader,
    extract_members,
    open_zip,
)
from stratbox.data import SourcePayload
from stratbox.data.representation import XLSX

from .parser import OLE, MAX_XLS
from .source import DATE_RE

_MAX_SOURCE = 30_000_000
_WORKBOOK_LIMITS = ArchiveLimits(500, 100_000_000, 32_000_000, MAX_XLS)
_CONTAINER_LIMITS = ArchiveLimits(100, 100_000_000, 32_000_000, _MAX_SOURCE)


@dataclass(frozen=True, slots=True)
class WorkbookMember:
    payload: SourcePayload
    member: str | None
    container_format: str


def is_spreadsheet_ooxml(data: bytes) -> bool:
    if not data.startswith(b"PK\x03\x04"):
        return False
    with open_zip(
        data, ArchiveLimits(500, 100_000_000, 32_000_000, _MAX_SOURCE)
    ) as archive:
        names = set(archive.namelist())
        if any(name.casefold().endswith("/vbaproject.bin") for name in names):
            raise HistoryError("XLSX_MACROS_NOT_ALLOWED")
        return {"[Content_Types].xml", "xl/workbook.xml"}.issubset(names)


def check_workbook_xml(data: bytes) -> None:
    # Inspect bounded members before handing XML to the workbook decoder.
    with open_zip(data, _WORKBOOK_LIMITS) as archive:
        for name in archive.namelist():
            if name.casefold().endswith((".xml", ".rels")):
                xml = archive.read(name)
                if b"<!DOCTYPE" in xml.replace(b"\x00", b"").upper():
                    raise HistoryError("XLSX_DTD_UNSUPPORTED")
                if name.startswith("xl/worksheets/") and name.endswith(".xml"):
                    _check_sheet_extent(xml)


def _check_sheet_extent(xml: bytes) -> None:
    from io import BytesIO
    from xml.etree.ElementTree import iterparse

    namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    for _, element in iterparse(BytesIO(xml), events=("end",)):
        if (
            element.tag == namespace + "row"
            and not 1 <= int(element.get("r", "1")) <= 3000
        ):
            raise HistoryError("XLSX_ROW_LIMIT")
        if element.tag == namespace + "c":
            ref = element.get("r", "")
            match = re.fullmatch(r"([A-Z]{1,3})([1-9][0-9]{0,3})", ref)
            if match is None:
                raise HistoryError("XLSX_CELL_REFERENCE")
            column = 0
            for letter in match[1]:
                column = column * 26 + ord(letter) - 64
            if column > 256 or int(match[2]) > 3000:
                raise HistoryError("XLSX_CELL_LIMIT")
        element.clear()


def select_workbook(
    source: SourcePayload,
    as_of: date,
    *,
    rar_reader: ArchiveReader | None = None,
) -> WorkbookMember:
    raw = source.data
    member = None
    if raw.startswith(OLE):
        container = "standalone_xls"
    elif is_spreadsheet_ooxml(raw):
        container = "standalone_ooxml"
    elif raw.startswith((b"Rar!", b"PK\x03\x04")):
        container = "rar" if raw.startswith(b"Rar!") else "zip"
        extracted = extract_members(
            raw,
            select=lambda names: (member_name(names),),
            limits=_CONTAINER_LIMITS,
            rar_reader=rar_reader,
        )
        member, raw = next(iter(extracted.items()))
        printed = DATE_RE.search(member.rsplit("/", 1)[-1])
        if (
            printed is not None
            and date(int(printed[3]), int(printed[2]), int(printed[1])) != as_of
        ):
            raise HistoryError("SOURCE_MEMBER_DATE_MISMATCH")
    else:
        raise HistoryError("SOURCE_FORMAT_UNSUPPORTED")
    if not 0 < len(raw) <= MAX_XLS:
        raise HistoryError("XLS_MEMBER_SIZE_INVALID")
    if raw.startswith(OLE):
        mime = "application/vnd.ms-excel"
    elif is_spreadsheet_ooxml(raw):
        mime = XLSX
    else:
        raise HistoryError("XLS_MEMBER_INVALID")
    return WorkbookMember(SourcePayload(raw, mime, source.source_id), member, container)
