from __future__ import annotations

import pandas as pd


PUBLISHED_OTHER_CLASSES = ('80', '84', '87', '88', '96', '97', '98', '99')
PUBLISHED_FD_SECTIONS = (
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H',
    'I', 'J', 'K', 'L', 'M', 'P', 'R',
)


def build_publication_categories(okved2_classes: pd.DataFrame) -> pd.DataFrame:
    known = set(okved2_classes['class_code'].astype(str))
    missing = sorted(set(PUBLISHED_OTHER_CLASSES) - known)
    if missing:
        raise ValueError(f'Published-other registry contains unknown classes: {missing}')
    rows: list[dict[str, object]] = []
    for row in okved2_classes.itertuples(index=False):
        class_code = str(row.class_code)
        individually = class_code not in PUBLISHED_OTHER_CLASSES
        rows.append(
            {
                'publication_level': 'NATIONAL_CLASS',
                'publication_category_code': (
                    class_code if individually else 'PUBLISHED_OTHER'
                ),
                'member_class_code': class_code,
                'is_individually_published': individually,
            }
        )
    published_sections = set(PUBLISHED_FD_SECTIONS)
    for row in okved2_classes.itertuples(index=False):
        section = str(row.section_code)
        rows.append(
            {
                'publication_level': 'FD_SECTION',
                'publication_category_code': (
                    section if section in published_sections else 'PUBLISHED_OTHER'
                ),
                'member_class_code': str(row.class_code),
                'is_individually_published': section in published_sections,
            }
        )
    return pd.DataFrame(rows)


def enrich_okved2_classes(
    okved2_classes: pd.DataFrame,
    categories: pd.DataFrame,
) -> pd.DataFrame:
    national = categories[categories['publication_level'].eq('NATIONAL_CLASS')]
    mapping = national.set_index('member_class_code')[
        ['publication_category_code', 'is_individually_published']
    ]
    out = okved2_classes.merge(
        mapping,
        left_on='class_code',
        right_index=True,
        how='left',
        validate='one_to_one',
    )
    return out.sort_values('class_order').reset_index(drop=True)
