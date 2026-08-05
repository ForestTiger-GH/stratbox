from __future__ import annotations

import re

COMPONENTS = (
    'performing_rub',
    'overdue_rub',
    'performing_fx',
    'overdue_fx',
)
TARGET_METRICS = (
    'debt_rub',
    'debt_fx',
    'debt_total',
    'overdue_rub',
    'overdue_fx',
    'overdue_total',
)

FD_REGISTRY = (
    ('ЦФО', 'ЦЕНТРАЛЬНЫЙ ФЕДЕРАЛЬНЫЙ ОКРУГ', 1),
    ('СЗФО', 'СЕВЕРО-ЗАПАДНЫЙ ФЕДЕРАЛЬНЫЙ ОКРУГ', 2),
    ('ЮФО', 'ЮЖНЫЙ ФЕДЕРАЛЬНЫЙ ОКРУГ', 3),
    ('СКФО', 'СЕВЕРО-КАВКАЗСКИЙ ФЕДЕРАЛЬНЫЙ ОКРУГ', 4),
    ('ПФО', 'ПРИВОЛЖСКИЙ ФЕДЕРАЛЬНЫЙ ОКРУГ', 5),
    ('УФО', 'УРАЛЬСКИЙ ФЕДЕРАЛЬНЫЙ ОКРУГ', 6),
    ('СФО', 'СИБИРСКИЙ ФЕДЕРАЛЬНЫЙ ОКРУГ', 7),
    ('ДФО', 'ДАЛЬНЕВОСТОЧНЫЙ ФЕДЕРАЛЬНЫЙ ОКРУГ', 8),
)
FD_NAME_TO_CODE = {name: code for code, name, _ in FD_REGISTRY}
FD_CODE_TO_NAME = {code: name for code, name, _ in FD_REGISTRY}
FD_ORDER = {code: order for code, _, order in FD_REGISTRY}


def normalize_text(value: object) -> str:
    text = str(value or '').replace('\xa0', ' ').replace('ё', 'е').replace('Ё', 'Е')
    text = text.replace('–', '-').replace('—', '-')
    return re.sub(r'\s+', ' ', text).strip()


def normalize_key(value: object) -> str:
    return normalize_text(value).casefold().strip(' .,:;')


def normalize_class_code(value: object) -> str:
    text = normalize_text(value)
    match = re.match(r'^(\d{1,2})(?:\D|$)', text)
    if match:
        return f'{int(match.group(1)):02d}'
    if text.lower().startswith('проч'):
        return 'PUBLISHED_OTHER'
    return text
