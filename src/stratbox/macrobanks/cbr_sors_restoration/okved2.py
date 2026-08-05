from __future__ import annotations

import re

import pandas as pd

from stratbox.registries import rosstat_okved2


def read_okved2_classes() -> pd.DataFrame:
    source = rosstat_okved2.read()
    records: list[dict[str, str]] = []
    for code in sorted({m.group(1) for value in source['code'].astype(str) if (m := re.match(r'^(\d{2})(?:\.|$)', value))}):
        hit = source[source['code'].astype(str).str.startswith(f'{code}.') | source['code'].astype(str).eq(code)]
        records.append({
            'class_code': code,
            'class_name': str(hit.iloc[0]['name']) if not hit.empty else code,
            'section_code': str(hit.iloc[0]['section']) if not hit.empty else '',
        })
    out = pd.DataFrame(records)
    if len(out) != 88:
        raise ValueError(f'Expected 88 OKVED2 classes, got {len(out)}')
    return out
