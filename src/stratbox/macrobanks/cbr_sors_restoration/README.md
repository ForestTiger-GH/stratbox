# CBR SORS Restoration

Домен восстанавливает региональную статистику корпоративного кредитного портфеля по классам ОКВЭД2 из пересекающихся публикаций Банка России.

Целевой объект — **таблица, которую ЦБ опубликовал бы в целых млн руб.**, а не неизвестные бухгалтерские суммы до рублей. При этом параллельно сохраняется latent-модель скрытых вещественных сумм, чтобы каждое восстановленное опубликованное значение оставалось совместимо с официальной точностью округления.

## Главная последовательность

```text
CBR books
→ canonical source bundle
→ latent quantity graph
→ publication partition graph
→ deterministic publication fixed point
    interval closure
    → zero / single-bucket facts
    → source-preserving value inheritance
    → inherited bucket back to latent bounds
    → repeat until no latent bound changes
→ global latent feasibility gate
→ optimization fixed point
    min/max on current feasible set
    → deterministic publication fixed point
    → minimum rounding distortion (L∞, then L1)
    → min/max on rounding-optimal face
    → deterministic publication fixed point
    → optional jointly validated narrow-bucket selection
    → deterministic publication fixed point
→ final restored grid
→ optional conditional legacy→ОКВЭД2 crosswalk
```

Ключевой принцип: publication-level факт `6` означает точное восстановленное значение `6 млн руб.`, но в latent-модели обычно возвращается как bucket `[5.5; 6.5)`, а не как `x = 6`.

## Доказательные уровни

`evidence_method` различает источник результата:

- `SOURCE_PUBLISHED` — непосредственно опубликованная величина;
- `LATENT_POINT_IDENTIFIED` — скрытая денежная величина доказана как точка;
- `PUBLISHED_BUCKET_IDENTIFIED` — официальный latent-интервал целиком лежит в одном publication bucket;
- `PUBLISHED_VALUE_INHERITED` — исходная опубликованная масса однозначно локализована по полному разбиению;
- `PUBLICATION_CLOSURE_IDENTIFIED` — следствие source-preserving publication facts;
- `ROUNDING_OPTIMUM_IDENTIFIED` / `ROUNDING_OPTIMUM_CLOSURE` — устойчиво на minimum-rounding-distortion face;
- `ROUNDING_SELECTED` / `ROUNDING_SELECTED_CLOSURE` — контролируемый последний уровень выбора узкого bucket, совместно проверенный Solver.

Каждая lower/upper latent-граница несёт `assumption_tier`, поэтому более слабое предположение никогда не превращается после арифметического closure в якобы более сильный факт.

## API

```python
from stratbox.macrobanks.cbr_sors_restoration import (
    SorsOptimizationConfig,
    SorsRunConfig,
    SorsSourceFiles,
    SorsTargetScope,
    run_sors_restoration,
)

files = SorsSourceFiles(
    regional_traditional='01_05_A_Debt_corp_20260701.xlsx',
    national_okved2='01_02_C_Debt_corp_by_activity.xlsx',
    federal_district_okved2='01_03_C_Loans_corp_by_fd_activity_20260701.xlsx',
    national_traditional='01_02_A_Debt_corp_by_activity.xlsx',
    regional_totals_history='01_05_D_Debt_subj.xlsx',
)

config = SorsRunConfig(
    as_of_date='2026-07-01',
    optimization=SorsOptimizationConfig(
        mode='targets',
        scope=SorsTargetScope(
            region_names=('г. Москва',),
            class_codes=('66',),
            metrics=('debt_rub', 'overdue_rub'),
        ),
        max_targets=50,
    ),
)

result = run_sors_restoration(files, config)
```

Основные результаты:

```python
result.regional_okved2_grid       # финальный publication-level GRID
result.restored_facts_grid        # только принятые восстановленные значения
result.facts_ledger_grid          # полный ledger фактов и supersession
result.components_grid     # latent component bounds + publication facts
result.publication_partitions_grid
result.publication_tokens_grid
result.inheritance_events_grid
result.fixed_point_passes_grid
result.target_bounds_grid
result.rounding_profiles_grid
result.selection_attempts_grid
result.solver_runs_grid
result.conflicts_grid
```

## Техническая структура

```text
sources/       — адаптеры книг ЦБ и canonical source bundle
registries/    — география, ОКВЭД2, publication categories
publication/   — rounding, ledger, partitions, inheritance, deterministic fixed point
strict/        — latent quantity graph, interval closure, sparse compiler, feasibility
optimization/  — targets, minimum rounding distortion, optimal-face proofs, selection
linear/        — HiGHS contracts/session
crosswalk/     — отдельный conditional evidence layer старой классификации
result_grid.py — финальная publication-level выдача из Fact Ledger
export.py      — Excel-аудит и pivots
```

`highspy>=1.11,<2` является production Solver backend. SciPy-внутренние bindings не используются библиотекой.
