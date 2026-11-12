"""Recognize the published bank-by-territory table and preserve its layout."""

from __future__ import annotations

from html.parser import HTMLParser
import re


CSV_PREFIX = ("source_row", "section_label")


SOURCE_IDENTITIES = ("регион", "наименованиеко", "рег№ко")


MAX_HTML = 10 * 1024 * 1024


MAX_CSV = 10 * 1024 * 1024


MAX_NODES = 180_000


MAX_ROWS = 30_000


MAX_CELLS = 150_000


KNOWN_CONTEXT = (
    "Порядок следования федеральных округов задан в соответствии с "
    "Общероссийским классификатором экономических регионов (ОКЭР)."
)


class CaptureError(Exception):
    """A named, non-recoverable failure. No publishing follows this exception."""


def fail(code: str) -> None:
    raise CaptureError(code)


def clean_text(value: str) -> str:
    # Layout whitespace only; preserve all substantive characters, punctuation and digits.
    value = re.sub(r"\s+", " ", value).strip()
    if any((ord(c) < 32 or 127 <= ord(c) <= 159) for c in value) or "\ufffd" in value:
        fail("SOURCE_CONTROL_CHARACTER")
    return value


class Cell:
    def __init__(self, tag: str, attrs: dict[str, str]):
        self.tag = tag
        self.attrs = attrs
        self.fragments: list[str] = []
        self.colspan = self._span("colspan")
        self.rowspan = self._span("rowspan")

    def _span(self, key: str) -> int:
        raw = self.attrs.get(key, "1")
        if not re.fullmatch(r"[0-9]{1,3}", raw):
            fail("SOURCE_SPAN_INVALID")
        n = int(raw)
        if not 1 <= n <= 40:
            fail("SOURCE_SPAN_INVALID")
        return n

    @property
    def text(self) -> str:
        return clean_text("".join(self.fragments))


class Table:
    def __init__(self):
        self.rows: list[list[Cell]] = []
        self.row: list[Cell] | None = None
        self.cell: Cell | None = None
        self.in_header = False
        self.header_rows: set[int] = set()


class SourceScanner(HTMLParser):
    """Finite, non-executing table scanner (not a browser or script evaluator)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables: list[Table] = []
        self.table: Table | None = None
        self.outside_text: list[str] = []
        self.ignored_depth = 0
        self.nodes = 0
        self.cells = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        self.nodes += 1
        if self.nodes > MAX_NODES:
            fail("SOURCE_DOM_LIMIT")
        if tag in ("script", "style", "template", "noscript") and self.table is None:
            self.ignored_depth += 1
        if tag == "table":
            if self.table is not None:
                fail("SOURCE_NESTED_TABLE")
            self.table = Table()
        if self.table is None:
            return
        if tag == "thead":
            self.table.in_header = True
        elif tag == "tr":
            if self.table.row is not None:
                fail("SOURCE_TR_UNCLOSED")
            self.table.row = []
        elif tag in ("td", "th"):
            if self.table.row is None or self.table.cell is not None:
                fail("SOURCE_CELL_STRUCTURE")
            attrs_dict = {k: v or "" for k, v in attrs}
            self.table.cell = Cell(tag, attrs_dict)
            self.cells += 1
            if self.cells > MAX_CELLS:
                fail("SOURCE_CELL_LIMIT")
        elif tag == "br" and self.table.cell is not None:
            self.table.cell.fragments.append(" ")

    def handle_data(self, data: str):
        if self.table is not None:
            if self.table.cell is not None:
                self.table.cell.fragments.append(data)
        elif data.strip() and self.ignored_depth == 0:
            self.outside_text.append(data)

    def handle_endtag(self, tag: str):
        if self.table is None:
            if (
                tag in ("script", "style", "template", "noscript")
                and self.ignored_depth
            ):
                self.ignored_depth -= 1
            return
        if tag in ("td", "th"):
            if self.table.cell is None or self.table.cell.tag != tag:
                fail("SOURCE_CELL_UNCLOSED")
            assert self.table.row is not None
            self.table.row.append(self.table.cell)
            self.table.cell = None
        elif tag == "tr":
            if self.table.row is None or self.table.cell is not None:
                fail("SOURCE_TR_INVALID")
            if len(self.table.rows) >= MAX_ROWS:
                fail("SOURCE_ROW_LIMIT")
            self.table.rows.append(self.table.row)
            if self.table.in_header:
                self.table.header_rows.add(len(self.table.rows))
            self.table.row = None
        elif tag == "thead":
            self.table.in_header = False
        elif tag == "table":
            if self.table.cell is not None or self.table.row is not None:
                fail("SOURCE_TABLE_UNCLOSED")
            self.tables.append(self.table)
            self.table = None

    def close(self):
        super().close()
        if self.table is not None:
            fail("SOURCE_TABLE_UNCLOSED")


def expanded_grid(rows: list[list[Cell]], width: int | None = None) -> list[list[Cell]]:
    pending: dict[int, tuple[Cell, int]] = {}
    result: list[list[Cell]] = []
    for row in rows:
        assigned: dict[int, Cell] = {}
        next_pending: dict[int, tuple[Cell, int]] = {}
        for index, (cell, remaining) in pending.items():
            assigned[index] = cell
            if remaining > 1:
                next_pending[index] = (cell, remaining - 1)
        col = 0
        for cell in row:
            while col in assigned:
                col += 1
            for i in range(col, col + cell.colspan):
                if i in assigned or i >= 40:
                    fail("SOURCE_SPAN_OVERLAP")
                assigned[i] = cell
                if cell.rowspan > 1:
                    next_pending[i] = (cell, cell.rowspan - 1)
            col += cell.colspan
        if not assigned:
            fail("SOURCE_EMPTY_ROW")
        n = max(assigned) + 1
        if set(assigned) != set(range(n)) or (width is not None and n != width):
            fail("SOURCE_GRID_MISALIGNMENT")
        result.append([assigned[i] for i in range(n)])
        pending = next_pending
    if pending:
        fail("SOURCE_ROWSPAN_OVERRUN")
    return result


def header_identity(text: str) -> str:
    return re.sub(r"\s+", "", text).casefold().replace("ё", "е").replace(".", "")


def identify_header(table: Table) -> tuple[int, list[str]] | None:
    # Try the first one to four physical rows; multi-level headers use distinct hierarchy.
    for n in range(1, min(4, len(table.rows)) + 1):
        try:
            grid = expanded_grid(table.rows[:n])
        except CaptureError:
            continue
        if any(len(r) != len(grid[-1]) for r in grid):
            continue
        names: list[str] = []
        for col in range(len(grid[-1])):
            parts: list[str] = []
            for row in grid:
                value = row[col].text
                if value and (not parts or parts[-1] != value):
                    parts.append(value)
            names.append(" / ".join(parts))
        keys = [header_identity(x) for x in names]
        basic = ("регион", "наименованиеко", "рег№ко")
        if len(names) < 4 or keys[:3] != list(basic):
            continue
        if any(not v for v in names[3:]):
            fail("SOURCE_HEADER_AMBIGUOUS")
        # Never include an actual data row in the identified header.
        if any(not any(c.tag == "th" for c in row) for row in table.rows[:n]) and n > 1:
            continue
        return n, names
    return None


def extract_records(html: str) -> tuple[list[tuple[str, ...]], int]:
    parser = SourceScanner()
    try:
        parser.feed(html)
        parser.close()
    except (ValueError, RecursionError):
        fail("SOURCE_DOM_INVALID")
    note = clean_text(" ".join(parser.outside_text))
    if KNOWN_CONTEXT not in note:
        fail("SOURCE_CONTEXT_CHANGED")
    candidates = [
        (t, h) for t in parser.tables if (h := identify_header(t)) is not None
    ]
    if len(candidates) != 1:
        fail("SOURCE_TABLE_AMBIGUOUS")
    table, (header_count, header) = candidates[0]
    width = len(header)
    if table.header_rows and set(range(1, header_count + 1)) != table.header_rows:
        fail("SOURCE_HEADER_LAYOUT_CHANGED")
    # Column names must not collapse the identity or duplicate distinct indicators.
    if len({header_identity(x) for x in header[3:]}) != width - 3:
        fail("SOURCE_HEADER_DUPLICATE")
    rows = table.rows[header_count:]
    # Data may have rowspan, so expand all data physical rows as a single grid.
    # Section rows are a separate structural type and never inherit rowspan.
    current_section = ""
    # Source column headings are retained, including any multi-level hierarchy.
    # Only two traceability fields are prepended to the original wide table.
    extracted: list[tuple[str, ...]] = [CSV_PREFIX + tuple(header)]
    data_rows = 0
    pending_rows: list[tuple[int, list[Cell]]] = []

    def flush():
        nonlocal data_rows, pending_rows
        if not pending_rows:
            return
        if not current_section:
            fail("SOURCE_SECTION_MISSING")
        grid = expanded_grid([r for _, r in pending_rows], width)
        for (row_index, _), cells in zip(pending_rows, grid):
            if any(not cells[i].text for i in range(3)):
                fail("SOURCE_IDENTIFIER_MISSING")
            data_rows += 1
            extracted.append(
                (str(row_index), current_section, *(cell.text for cell in cells))
            )
        pending_rows = []

    for physical_index, cells in enumerate(rows, header_count + 1):
        if not cells:
            fail("SOURCE_EMPTY_ROW")
        # Only territorial section labels may occupy a whole merged source row.
        # Reject unexplained full-width notes/totals rather than silently dropping them.
        if len(cells) == 1 and cells[0].colspan >= width and cells[0].rowspan == 1:
            label = cells[0].text
            if (
                label
                and label != "-"
                and not label.casefold().endswith("федеральный округ")
            ):
                fail("SOURCE_SECTION_UNRECOGNIZED")
            flush()
            if label:
                current_section = label
            # An empty structural separator does not erase the preceding label.
            continue
        if any(c.colspan != 1 for c in cells):
            shape = "-".join(str(c.colspan) for c in cells)
            fail(f"SOURCE_DATA_COLSPAN_AMBIGUOUS_ROW_{physical_index}_SHAPE_{shape}")
        pending_rows.append((physical_index, cells))
    flush()
    if data_rows == 0 or len(extracted) != data_rows + 1:
        fail("SOURCE_INCOMPLETE")
    return extracted, data_rows
