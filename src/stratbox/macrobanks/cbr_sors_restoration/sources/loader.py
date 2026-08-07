from __future__ import annotations

from dataclasses import replace

import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import (
    SorsSourceBundle,
    SorsSourceFiles,
)
from stratbox.macrobanks.cbr_sors_restoration.portfolio import PORTFOLIO_SCOPES
from stratbox.macrobanks.cbr_sors_restoration.publication import RoundingPolicy
from stratbox.macrobanks.cbr_sors_restoration.registries.okved2 import read_okved2_classes
from stratbox.macrobanks.cbr_sors_restoration.registries.publication_categories import (
    PUBLISHED_OTHER_CLASSES,
    build_publication_categories,
    enrich_okved2_classes,
)
from stratbox.macrobanks.cbr_sors_restoration.sources.common import source_manifest_record
from stratbox.macrobanks.cbr_sors_restoration.sources.federal_district_okved2 import (
    parse_federal_district_okved2,
)
from stratbox.macrobanks.cbr_sors_restoration.sources.national_okved2 import parse_national_okved2
from stratbox.macrobanks.cbr_sors_restoration.sources.national_traditional import (
    parse_national_traditional,
)
from stratbox.macrobanks.cbr_sors_restoration.sources.regional_totals import (
    parse_regional_totals_history,
)
from stratbox.macrobanks.cbr_sors_restoration.sources.regional_traditional import (
    parse_regional_traditional,
)
from stratbox.macrobanks.cbr_sors_restoration.sources.sme import (
    parse_sme_national_okved2,
    parse_sme_national_totals,
    parse_sme_regional_totals,
)
from stratbox.macrobanks.cbr_sors_restoration.sources.validation import validate_source_bundle


def _manifest(series: str, path, rows: int, role: str) -> dict[str, object]:
    return source_manifest_record(series, path, rows, required=True, role=role)


def load_sors_sources(
    files: SorsSourceFiles,
    as_of_date: str,
    publication_step: float = 1.0,
) -> SorsSourceBundle:
    """Load the complete corporate + SME + SME-IE constraint system.

    SME scopes are auxiliary latent constraint cubes.  The outward restoration
    target remains ``CORPORATE_TOTAL``; segment rows exist only to tighten it.
    """

    policy = RoundingPolicy(step=publication_step)
    regional, geography, atomic = parse_regional_traditional(
        files.regional_traditional, as_of_date, policy
    )
    national_traditional = parse_national_traditional(
        files.national_traditional, as_of_date, policy
    )
    national_okved2 = parse_national_okved2(files.national_okved2, as_of_date, policy)
    fd_okved2 = parse_federal_district_okved2(
        files.federal_district_okved2,
        as_of_date,
        policy,
        source_series='01_03_C',
        source_role='STRICT_FD_OKVED2',
        portfolio_scope='CORPORATE_TOTAL',
    )

    for frame in (regional, national_traditional, national_okved2):
        frame['portfolio_scope'] = 'CORPORATE_TOTAL'

    sme_national_totals = parse_sme_national_totals(
        files.sme_national_totals, as_of_date, policy
    )
    sme_national_okved2 = parse_sme_national_okved2(
        files.sme_national_okved2,
        as_of_date,
        policy,
        portfolio_scope='SME',
        source_series='01_11_F',
    )
    sme_ie_national_okved2 = parse_sme_national_okved2(
        files.sme_ie_national_okved2,
        as_of_date,
        policy,
        portfolio_scope='SME_IE',
        source_series='01_11_I',
    )
    sme_fd_okved2 = parse_federal_district_okved2(
        files.sme_federal_district_okved2,
        as_of_date,
        policy,
        source_series='01_12_A',
        source_role='STRICT_FD_OKVED2_SME',
        portfolio_scope='SME',
    )
    sme_regional = parse_sme_regional_totals(
        files.sme_regional_totals,
        as_of_date,
        policy,
        geography,
        portfolio_scope='SME',
        source_series='01_13_F',
    )
    sme_ie_regional = parse_sme_regional_totals(
        files.sme_ie_regional_totals,
        as_of_date,
        policy,
        geography,
        portfolio_scope='SME_IE',
        source_series='01_13_I',
    )

    classes = read_okved2_classes()
    categories = build_publication_categories(classes)
    classes = enrich_okved2_classes(classes, categories)
    expected_other = tuple(sorted(PUBLISHED_OTHER_CLASSES))
    for series, frame in (
        ('01_02_C', national_okved2),
        ('01_11_F', sme_national_okved2),
        ('01_11_I', sme_ie_national_okved2),
    ):
        explicit = set(
            frame.loc[frame['activity_code'].str.fullmatch(r'\d{2}'), 'activity_code'].astype(str)
        )
        missing = tuple(sorted(set(classes['class_code'].astype(str)) - explicit))
        if missing != expected_other:
            raise ValueError(
                f'{series} OKVED2 publication composition changed: '
                f'expected PUBLISHED_OTHER={expected_other}, got {missing}'
            )

    history = pd.DataFrame()
    if files.regional_totals_history is not None:
        history = parse_regional_totals_history(
            files.regional_totals_history, as_of_date, policy, geography
        )
        history['portfolio_scope'] = 'CORPORATE_TOTAL'

    frames = [
        regional,
        national_traditional,
        national_okved2,
        fd_okved2,
        sme_national_totals,
        sme_national_okved2,
        sme_ie_national_okved2,
        sme_fd_okved2,
        sme_regional,
        sme_ie_regional,
    ]
    if not history.empty:
        frames.append(history)
    source_grid = pd.concat(
        [frame.dropna(axis=1, how='all') for frame in frames],
        ignore_index=True,
        sort=False,
    )
    source_grid = source_grid.sort_values(
        ['portfolio_scope', 'source_series', 'source_sheet', 'source_row', 'source_column'],
        kind='stable',
    ).reset_index(drop=True)
    scopes = tuple(sorted(set(source_grid['portfolio_scope'].astype(str))))
    if set(scopes) != set(PORTFOLIO_SCOPES):
        raise ValueError(
            f'Expected complete portfolio scopes {PORTFOLIO_SCOPES}, got {scopes}'
        )

    manifest_rows = [
        _manifest('01_05_A', files.regional_traditional, len(regional), 'STRICT_REGIONAL_TOTALS_AND_CROSSWALK_LEGACY'),
        _manifest('01_02_A', files.national_traditional, len(national_traditional), 'STRICT_NATIONAL_TOTAL_AND_CROSSWALK_LEGACY'),
        _manifest('01_02_C', files.national_okved2, len(national_okved2), 'STRICT_NATIONAL_OKVED2'),
        _manifest('01_03_C', files.federal_district_okved2, len(fd_okved2), 'STRICT_FD_OKVED2'),
        _manifest('01_11', files.sme_national_totals, len(sme_national_totals), 'STRICT_NATIONAL_SME_TOTALS'),
        _manifest('01_11_F', files.sme_national_okved2, len(sme_national_okved2), 'STRICT_NATIONAL_OKVED2_SME'),
        _manifest('01_11_I', files.sme_ie_national_okved2, len(sme_ie_national_okved2), 'STRICT_NATIONAL_OKVED2_SME_IE'),
        _manifest('01_12_A', files.sme_federal_district_okved2, len(sme_fd_okved2), 'STRICT_FD_OKVED2_SME'),
        _manifest('01_13_F', files.sme_regional_totals, len(sme_regional), 'STRICT_REGIONAL_TOTALS_SME'),
        _manifest('01_13_I', files.sme_ie_regional_totals, len(sme_ie_regional), 'STRICT_REGIONAL_TOTALS_SME_IE'),
    ]
    if files.regional_totals_history is not None:
        manifest_rows.append(
            source_manifest_record(
                '01_05_D', files.regional_totals_history, len(history),
                required=False, role='OPTIONAL_VALIDATION_AND_HISTORY'
            )
        )

    bundle = SorsSourceBundle(
        source_grid=source_grid,
        regional_traditional_grid=regional,
        national_traditional_grid=national_traditional,
        national_okved2_grid=national_okved2,
        federal_district_okved2_grid=fd_okved2,
        sme_national_totals_grid=sme_national_totals,
        sme_national_okved2_grid=sme_national_okved2,
        sme_ie_national_okved2_grid=sme_ie_national_okved2,
        sme_federal_district_okved2_grid=sme_fd_okved2,
        sme_regional_totals_grid=sme_regional,
        sme_ie_regional_totals_grid=sme_ie_regional,
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
