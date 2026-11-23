from __future__ import annotations

from dataclasses import replace

import pandas as pd

from stratbox.shared.evidence import SourcePayload
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.dependencies import DEPENDENCIES
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.dependencies import dependency_manifest
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.dependencies import original_input

from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.contracts import SorsSourceBundle
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.contracts import SorsSourceInputs
from stratbox.domains.cbr.analytics.corporate_lending.sors.portfolio import PORTFOLIO_SCOPES
from stratbox.domains.cbr.analytics.corporate_lending.sors.publication import RoundingPolicy
from stratbox.domains.cbr.analytics.corporate_lending.sors.registries.okved2 import read_okved2_classes
from stratbox.domains.cbr.analytics.corporate_lending.sors.registries.publication_categories import PUBLISHED_OTHER_CLASSES
from stratbox.domains.cbr.analytics.corporate_lending.sors.registries.publication_categories import build_publication_categories
from stratbox.domains.cbr.analytics.corporate_lending.sors.registries.publication_categories import enrich_okved2_classes
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.common import source_manifest_record
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.federal_district_okved2 import parse_federal_district_okved2
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.national_okved2 import parse_national_okved2
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.national_traditional import parse_national_traditional
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.regional_totals import parse_regional_totals_history
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.regional_traditional import parse_regional_traditional
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.regional_traditional import regional_traditional_from_flake
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.sme import parse_sme_national_okved2
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.sme import parse_sme_national_totals
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.sme import parse_sme_regional_totals
from stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.validation import validate_source_bundle


def parse_source_inputs(
    files: SorsSourceInputs,
    as_of_date: str,
    publication_step: float = 1.0,
) -> SorsSourceBundle:
    """Load the complete corporate + SME + SME-IE constraint system.

    SME scopes are auxiliary latent constraint cubes.  The outward restoration
    target remains ``CORPORATE_TOTAL``; segment rows exist only to tighten it.
    """

    dependency_grid = dependency_manifest(files, as_of_date, publication_step)
    policy = RoundingPolicy(step=publication_step)
    regional_parser = parse_regional_traditional if isinstance(files.regional_traditional, SourcePayload) else regional_traditional_from_flake
    regional, geography, atomic = regional_parser(
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

    registry_inputs = []
    classes = read_okved2_classes(inputs=registry_inputs)
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

    input_frames = {
        "regional_traditional": regional, "national_traditional": national_traditional,
        "national_okved2": national_okved2, "federal_district_okved2": fd_okved2,
        "sme_national_totals": sme_national_totals, "sme_national_okved2": sme_national_okved2,
        "sme_ie_national_okved2": sme_ie_national_okved2, "sme_federal_district_okved2": sme_fd_okved2,
        "sme_regional_totals": sme_regional, "sme_ie_regional_totals": sme_ie_regional,
        "regional_totals_history": history,
    }
    manifest_rows = [
        {**source_manifest_record(item.source_series, getattr(files, item.input_name), len(input_frames[item.input_name]),
                                  required=item.required, role=item.source_role),
         "series_id": item.series_id, "method_version": item.method_version, "as_of_date": as_of_date}
        for item in DEPENDENCIES if getattr(files, item.input_name) is not None
    ]

    lineage = tuple(original_input(getattr(files, item.input_name), item.source_series)
                    for item in DEPENDENCIES if getattr(files, item.input_name) is not None) + tuple(registry_inputs)
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
        lineage=lineage,
        as_of_date=as_of_date,
        publication_step=publication_step,
        dependency_manifest_grid=dependency_grid,
    )
    validation = validate_source_bundle(bundle, raise_on_error=True)
    return replace(bundle, validation_grid=validation)
