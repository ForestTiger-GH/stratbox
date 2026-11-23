"""Source-local observation projection independent of acquisition and storage."""
from collections import Counter
from datetime import date
from decimal import Decimal
import re
from stratbox.shared.data.observations import MetricRef, Observation, PeriodRef, SubjectRef
from stratbox.shared.data.releases import csv_rows
from .representation import count_label
_MISSING = frozenset({"", "-", "–", "—"})

def _count_token(token):
    return token in _MISSING or re.fullmatch(r"[0-9]{1,18}(?:[.,]0{1,10})?", token) is not None


def _observations(data: bytes, as_of: date, *, unresolved=()) -> tuple[tuple[Observation, ...] | None, tuple[str, ...]]:
    rows = csv_rows(data)
    header = rows[0]
    territories = [
        i
        for i, name in enumerate(header[2:], 2)
        if any(
            part.casefold() in {"регион", "территория", "наименование территории"}
            for part in name.split(" / ")
        )
    ]
    if len(territories) != 1:
        return None, tuple(header[2:])
    column = territories[0]
    period = PeriodRef("as_of", as_of)
    metrics = [count_label(heading) for heading in header[column + 1:]]
    duplicates = Counter(metrics)
    fields = []
    excluded = list(header[2:column])
    for index, (heading, metric) in enumerate(zip(header[column + 1:], metrics), column + 1):
        if (metric is None or heading in unresolved or duplicates[metric] != 1
                or any(not _count_token(row[index]) for row in rows[1:])):
            excluded.append(heading)
        else:
            fields.append((index, metric))
    if not fields:
        return None, tuple(excluded)
    result = []
    for row in rows[1:]:
        territory = row[column]
        if not territory:
            return None, tuple(header[2:])
        perimeter = (
            "national"
            if "российская федерация" in territory.casefold()
            else "territorial"
        )
        for index, metric in fields:
            token = row[index]
            if token in _MISSING:
                value, status = None, ("blank" if not token else "dash")
            else:
                value, status = Decimal(token.replace(",", ".")), "reported"
            result.append(
                Observation(
                    SubjectRef("cbr.published_territory", territory),
                    MetricRef(metric, "count"),
                    period,
                    (("section", row[1]),),
                    perimeter,
                    value,
                    status,
                    f"row:{row[0]}",
                    token,
                )
            )
    return tuple(result), tuple(excluded)
