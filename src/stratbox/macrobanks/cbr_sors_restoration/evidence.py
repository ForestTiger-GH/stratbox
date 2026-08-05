from __future__ import annotations

import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.metrics import source_metric


def published_facts(canonical_grid: pd.DataFrame) -> pd.DataFrame:
    frame = canonical_grid.copy()
    frame['metric'] = [source_metric(m, c) for m, c in zip(frame['measure'], frame['currency'], strict=True)]
    frame['lower_bound'] = frame['published_lower']
    frame['upper_bound'] = frame['published_upper']
    frame['status'] = 'PUBLISHED'
    frame['evidence_layer'] = 'PUBLISHED'
    frame['is_published'] = True
    frame['is_reconstructed'] = False
    frame['model_run_id'] = None
    frame['mapping_version'] = None
    frame['proof_type'] = 'published_observation'
    keep = [
        'as_of_date', 'geography_node_id', 'geography_name', 'geography_kind',
        'classifier_id', 'activity_code', 'activity_name', 'metric', 'value',
        'lower_bound', 'upper_bound', 'status', 'evidence_layer',
        'is_published', 'is_reconstructed', 'proof_type', 'observation_id',
        'source_series', 'source_file_actual', 'source_sheet', 'source_row',
        'source_column', 'source_sha256', 'model_run_id', 'mapping_version',
    ]
    return frame.reindex(columns=keep)
