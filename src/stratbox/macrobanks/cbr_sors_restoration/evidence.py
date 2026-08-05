from __future__ import annotations

import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.metrics import source_metric


FACT_COLUMNS = [
    'as_of_date', 'geography_node_id', 'geography_name', 'geography_kind',
    'classifier_id', 'activity_code', 'activity_name', 'metric', 'value',
    'lower_bound', 'upper_bound', 'status', 'evidence_layer',
    'is_published', 'is_reconstructed', 'is_estimate', 'proof_type',
    'observation_id', 'source_series', 'source_file_actual', 'source_sheet',
    'source_row', 'source_column', 'source_sha256', 'model_run_id',
    'mapping_version', 'constraint_set_hash', 'lower_solve_id',
    'upper_solve_id', 'bridge_objective_value',
]


def published_facts(canonical_grid: pd.DataFrame) -> pd.DataFrame:
    frame = canonical_grid.copy()
    frame['metric'] = [
        source_metric(m, c)
        for m, c in zip(frame['measure'], frame['currency'], strict=True)
    ]
    frame['lower_bound'] = frame['published_lower']
    frame['upper_bound'] = frame['published_upper']
    frame['status'] = 'PUBLISHED'
    frame['evidence_layer'] = 'PUBLISHED'
    frame['is_published'] = True
    frame['is_reconstructed'] = False
    frame['is_estimate'] = False
    frame['model_run_id'] = None
    frame['mapping_version'] = None
    frame['constraint_set_hash'] = None
    frame['lower_solve_id'] = None
    frame['upper_solve_id'] = None
    frame['bridge_objective_value'] = None
    frame['proof_type'] = 'published_observation'
    return frame.reindex(columns=FACT_COLUMNS)
