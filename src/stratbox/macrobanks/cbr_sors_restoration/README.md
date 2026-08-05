# CBR SORS restoration

Domain for strict partial identification of regional corporate debt by OKVED2 from overlapping Bank of Russia SORS tables.

The strict solver uses only published margins, publication-rounding intervals, non-negativity and explicitly proven hard mappings. Semantic or historically fitted mappings are diagnostics/priors only and never become strict facts automatically.

Core representation uses four non-overlapping components: performing RUB, overdue RUB, performing FX, overdue FX. The pipeline is: parse -> atomic geography -> deterministic interval closure -> LP feasibility -> min/max certification -> fixed point -> optional analytical benchmark.

See the project-level methodology note delivered with the implementation for the proof/status policy and limitations.
