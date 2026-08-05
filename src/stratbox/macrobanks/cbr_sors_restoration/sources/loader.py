from __future__ import annotations

from dataclasses import replace

import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import (
    SorsSourceBundle,
    SorsSourceFiles,
)
from stratbox.macrobanks.cbr_sors_restoration.publication import RoundingPolicy
from stratbox.macrobanks.cbr_sors_restoration.registries.okved2 import (
    read_okved2_classes,
)
from stratbox.macrobanks.cbr_sors_restoration.registries.publication_categories import (
    PUBLISHED_OTHER_CLASSES,
    build_publication_categories,
    enrich_okved2_classes,
)
from stratbox.macrobanks.cbr_sors_restoration.sources.common import (
    source_manifest_record,
)
from stratbox.macrobanks.cbr_sors_restoration.sources.federal_district_okved2 import (
    parse_federal_district_okved2,
)
from stratbox.macrobanks.cbr_sors_restoration.sources.national_okved2 import (
    parse_national_okved2,
)
from stratbox.macrobanks.cbr_sors_restoration.sources.national_traditional import (
    parse_national_traditional,
)
from stratbox.macrobanks.cbr_sors_restoration.sources.regional_totals import (
    parse_regional_totals_history,
)
from stratbox.macrobanks.cbr_sors_restoration.sources.regional_traditional import (
    parse_regional_traditional,
)
from stratbox.macrobanks.cbr_sors_restoration.sources.validation import (
    validate_source_bundle,
)


def load_sors_sources(
    files: SorsSourceFiles,
    as_of_date: str,
    publication_step: float = 1.0,
) -> SorsSourceBundle:
    policy = RoundingPolicy(step=publication_step)
    regional, geography, atomic = parse_regional_traditional(
        files.regional_traditional,
        as_of_date,
        policy,
    )
    national_traditional = parse_national_traditional(
        files.national_traditional,
        as_of_date,
        policy,
    )
    national_okved2 = parse_national_okved2(
        files.national_okved2,
        as_of_date,
        policy,
    )
    fd_okved2 = parse_federal_district_okved2(
        files.federal_district_okved2,
        as_of_date,
        policy,
    )
    classes = read_okved2_classes()
    categories = build_publication_categories(classes)
    classes = enrich_okved2_classes(classes, categories)

    explicit = set(
        national_okved2.loc[
            national_okved2['activity_code'].str.fullmatch(r'\d{2}'),
            'activity_code',
        ].astype(str)
    )
    missing = tuple(sorted(set(classes['class_code'].astype(str)) - explicit))
    if missing != tuple(sorted(PUBLISHED_OTHER_CLASSES)):
        raise ValueError(
            'National OKVED2 publication composition changed: '
            f'expected PUBLISHED_OTHER={PUBLISHED_OTHER_CLASSES}, got {missing}'
        )

    history = pd.DataFrame()
    if files.regional_totals_history is not None:
        history = parse_regional_totals_history(
            files.regional_totals_history,
            as_of_date,
            policy,
            geography,
        )

    frames = [regional, national_traditional, national_okved2, fd_okved2]
    if not history.empty:
        frames.append(history)
    source_grid = pd.concat(
        [frame.dropna(axis=1, how='all') for frame in frames],
        ignore_index=True,
        sort=False,
    )
    source_grid = source_grid.sort_values(
        ['source_series', 'source_sheet', 'source_row', 'source_column'],
        kind='stable',
    ).reset_index(drop=True)

    manifest_rows = [
        source_manifest_record(
            '01_05_A',
            files.regional_traditional,
            len(regional),
            required=True,
            role='STRICT_REGIONAL_TOTALS_AND_BRIDGE_LEGACY',
        ),
        source_manifest_record(
            '01_02_A',
            files.national_traditional,
            len(national_traditional),
            required=True,
            role='STRICT_NATIONAL_TOTAL_AND_BRIDGE_LEGACY',
        ),
        source_manifest_record(
            '01_02_C',
            files.national_okved2,
            len(national_okved2),
            required=True,
            role='STRICT_NATIONAL_OKVED2',
        ),
        source_manifest_record(
            '01_03_C',
            files.federal_district_okved2,
            len(fd_okved2),
            required=True,
            role='STRICT_FD_OKVED2',
        ),
    ]
    if files.regional_totals_history is not None:
        manifest_rows.append(
            source_manifest_record(
                '01_05_D',
                files.regional_totals_history,
                len(history),
                required=False,
                role='OPTIONAL_VALIDATION_AND_HISTORY',
            )
        )
    bundle = SorsSourceBundle(
        source_grid=source_grid,
        regional_traditional_grid=regional,
        national_traditional_grid=national_traditional,
        national_okved2_grid=national_okved2,
        federal_district_okved2_grid=fd_okved2,
        regional_totals_history_grid=history,
        geography_nodes_grid=geography,
        atomic_regions_grid=atomic,
        okved2_classes_grid=classes,
        publication_categories_grid=categories,
        observation_bindings_grid=pd.DataFrame(),
        source_manifest_grid=pd.DataFrame(manifest_rows),
        validation_grid=pd.DataFrame(),
    )
    validation = validate_source_bundle(bundle, raise_on_error=True)
    return replace(bundle, validation_grid=validation)
