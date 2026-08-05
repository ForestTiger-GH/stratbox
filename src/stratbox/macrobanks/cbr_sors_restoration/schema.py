from __future__ import annotations

import re

from stratbox.macrobanks.cbr_sors_restoration.publication import publication_interval, published_bucket

COMPONENTS = ('performing_rub', 'overdue_rub', 'performing_fx', 'overdue_fx')
TARGET_METRICS = ('debt_rub', 'debt_fx', 'debt_total', 'overdue_rub', 'overdue_fx', 'overdue_total')

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
        return 'PUBLISHED_OTHER'
    return text
