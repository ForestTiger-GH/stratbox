from __future__ import annotations

import re

import pandas as pd

from stratbox.registries import rosstat_okved2

_SECTION_NAMES = {
    'A': 'Сельское, лесное хозяйство, охота, рыболовство и рыбоводство',
    'B': 'Добыча полезных ископаемых',
    'C': 'Обрабатывающие производства',
    'D': (
        'Обеспечение электрической энергией, газом и паром; '
        'кондиционирование воздуха'
    ),
    'E': (
        'Водоснабжение; водоотведение, организация сбора и утилизации '
        'отходов, деятельность по ликвидации загрязнений'
    ),
    'F': 'Строительство',
    'G': (
        'Торговля оптовая и розничная; ремонт автотранспортных средств '
        'и мотоциклов'
    ),
    'H': 'Транспортировка и хранение',
    'I': 'Деятельность гостиниц и предприятий общественного питания',
    'J': 'Деятельность в области информации и связи',
    'K': 'Деятельность финансовая и страховая',
    'L': 'Деятельность по операциям с недвижимым имуществом',
    'M': 'Деятельность профессиональная, научная и техническая',
    'N': 'Деятельность административная и сопутствующие дополнительные услуги',
    'O': (
        'Государственное управление и обеспечение военной безопасности; '
        'социальное обеспечение'
    ),
    'P': 'Образование',
    'Q': 'Деятельность в области здравоохранения и социальных услуг',
    'R': (
        'Деятельность в области культуры, спорта, организации досуга '
        'и развлечений'
    ),
    'S': 'Предоставление прочих видов услуг',
    'T': (
        'Деятельность домашних хозяйств как работодателей; недифференцированная '
        'деятельность домашних хозяйств по производству товаров и услуг '
        'для собственного потребления'
    ),
    'U': 'Деятельность экстерриториальных организаций и органов',
}

def read_okved2_classes() -> pd.DataFrame:
    source = rosstat_okved2.read().copy()
    source['code'] = source['code'].astype(str).str.strip()
    class_codes = sorted(
        {
            match.group(1)
            for value in source['code']
            if (match := re.fullmatch(r'(\d{2})', value))
            or (match := re.match(r'^(\d{2})\.', value))
        }
    )
    records: list[dict[str, object]] = []
    for order, code in enumerate(class_codes, start=1):
        exact = source[source['code'].eq(code)]
        if exact.empty:
            exact = source[source['code'].str.startswith(f'{code}.')]
        if exact.empty:
            raise ValueError(f'OKVED2 registry has no record for class {code}')
        row = exact.iloc[0]
        records.append(
            {
                'class_code': code,
                'class_name': str(row['name']),
                'class_order': order,
                'section_code': str(row['section']),
            }
        )
    out = pd.DataFrame(records)
    if len(out) != 88:
        raise ValueError(f'Expected 88 OKVED2 classes, got {len(out)}')
    section_order = {
        code: order
        for order, code in enumerate(dict.fromkeys(out['section_code'].astype(str)), start=1)
    }
    out['section_order'] = out['section_code'].map(section_order).astype(int)
    out['section_name'] = out['section_code'].map(_SECTION_NAMES)
    if out['section_name'].isna().any():
        missing = sorted(
            out.loc[out['section_name'].isna(), 'section_code'].astype(str).unique()
        )
        raise ValueError(f'Unknown OKVED2 section codes: {missing}')
    return out
