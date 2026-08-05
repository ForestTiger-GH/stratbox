from __future__ import annotations

import re

COMPONENTS = ('performing_rub', 'overdue_rub', 'performing_fx', 'overdue_fx')

FD_ALIASES = {
    'ЦЕНТРАЛЬНЫЙ ФЕДЕРАЛЬНЫЙ ОКРУГ': 'ЦФО',
    'СЕВЕРО-ЗАПАДНЫЙ ФЕДЕРАЛЬНЫЙ ОКРУГ': 'СЗФО',
    'ЮЖНЫЙ ФЕДЕРАЛЬНЫЙ ОКРУГ': 'ЮФО',
    'СЕВЕРО-КАВКАЗСКИЙ ФЕДЕРАЛЬНЫЙ ОКРУГ': 'СКФО',
    'ПРИВОЛЖСКИЙ ФЕДЕРАЛЬНЫЙ ОКРУГ': 'ПФО',
    'УРАЛЬСКИЙ ФЕДЕРАЛЬНЫЙ ОКРУГ': 'УФО',
    'СИБИРСКИЙ ФЕДЕРАЛЬНЫЙ ОКРУГ': 'СФО',
    'ДАЛЬНЕВОСТОЧНЫЙ ФЕДЕРАЛЬНЫЙ ОКРУГ': 'ДФО',
}

SECTION_RANGES: dict[str, tuple[tuple[int, int], ...]] = {
    'A': ((1, 3),),
    'B': ((5, 9),),
    'C': ((10, 33),),
    'D': ((35, 35),),
    'E': ((36, 39),),
    'F': ((41, 43),),
    'G': ((45, 47),),
    'H': ((49, 53),),
    'I': ((55, 56),),
    'J': ((58, 63),),
    'K': ((64, 66),),
    'L': ((68, 68),),
    'M': ((69, 75),),
    'P': ((85, 85),),
    'R': ((90, 93),),
}


def normalize_text(value: object) -> str:
    text = str(value or '').replace('\xa0', ' ').replace('ё', 'е').replace('Ё', 'Е')
    text = text.replace('–', '-').replace('—', '-')
    return re.sub(r'\s+', ' ', text).strip()


def normalize_class_code(value: object) -> str:
    text = normalize_text(value)
    match = re.match(r'^(\d{1,2})(?:\D|$)', text)
    if match:
        return f'{int(match.group(1)):02d}'
    if text.lower().startswith('проч'):
        return 'OTHER'
    return text


def section_for_class(class_code: str) -> str:
    if class_code == 'OTHER':
        return 'OTHER'
    try:
        code = int(class_code)
    except ValueError:
        return 'OTHER'
    for section, ranges in SECTION_RANGES.items():
        if any(lo <= code <= hi for lo, hi in ranges):
            return section
    return 'OTHER'


def publication_interval(value: float, step: float = 1.0) -> tuple[float, float]:
    half = step / 2.0
    return max(0.0, float(value) - half), float(value) + half


def published_bucket(lower: float, upper: float, step: float = 1.0, tol: float = 1e-9) -> float | None:
    """Return the single published value compatible with the whole hidden interval, if any."""
    if upper < lower - tol:
        return None
    # publication uses integer millions in current SORS workbooks.  A closed
    # interval is used computationally; subtracting tol from the upper end
    # preserves the intended half-open rounding bucket at exact .5 borders.
    lo_bucket = round(lower / step) * step
    hi_bucket = round(max(lower, upper - tol) / step) * step
    return lo_bucket if abs(lo_bucket - hi_bucket) <= tol else None
