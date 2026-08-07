# SORS Restoration — implementation report 2026-08-07

Версия Strategy Box: `0.8.0`  
Версия архитектуры: multi-scope publication restoration + dominance + relaxed rounding selection.

## Цель волны

Волна развивает доказательную модель 0.7 в трёх направлениях:

1. сделать практически доступным восстановление узких, но не single-bucket РКВС без ручного увеличения официального ±0.5;
2. явно использовать монотонность `overdue <= debt`;
3. подключить официальные SME и SME-IE книги как auxiliary constraint scopes для восстановления CORPORATE_TOTAL, не создавая отдельный пользовательский SME/IE restored GRID.

## Multi-scope hidden model

Один расчёт теперь содержит три скрытых куба:

```text
SME_IE <= SME <= CORPORATE_TOTAL
```

Каждый куб имеет `85 × 88 × 4` atomic component quantities. Scope включён в identity всех component/metric/publication quantities.

Published Mass Tokens строго локальны своему scope. Равные опубликованные числа разных scopes не наследуются друг в друга. Межscope-информация передаётся только hard DOMINANCE.

Solver targets и пользовательские `regional_okved2_grid/components_grid` остаются только `CORPORATE_TOTAL`; SME/SME_IE существуют как auxiliary latent variables and constraints.

## Новые официальные источники

Помимо корпоративного контура подключены:

- `01_11_Debt_sme.xlsx` — национальные SME и SME_IE totals;
- `01_11_F_Debt_sme_by_activity.xlsx` — SME × class;
- `01_11_I_Debt_ie_by_activity.xlsx` — SME_IE × class;
- `01_12_A_Loans_sme_by_fd_activity_YYYYMMDD.xlsx` — SME × FD × section;
- `01_13_F_Debt_sme_subj.xlsx` — SME × geography totals;
- `01_13_I_Debt_sme_subj.xlsx` — SME_IE × geography totals.

Для `01_12_A` используются только stock-листы задолженности/просрочки. Flow-лист `объем` в одно-периодный остаточный Solver не попадает.

На реальном комплекте 01.07.2026 получено `18 266` official source observations и `55/55` source-validation checks PASS.

## DOMINANCE

Введён generic relation type `DOMINANCE`.

Deterministic interval closure использует для `child <= parent`:

```text
upper(child) <= upper(parent)
lower(parent) >= lower(child)
```

Механизм применяется к:

- overdue/debt монотонности;
- SME_IE/SME/CORPORATE nesting;
- сопоставимым published aggregates.

Atomic scope nesting одновременно компилируется hard LP inequalities, поэтому deterministic и Solver слои имеют одну семантику.

## Реальный контрольный результат 01.07.2026

Ключевой testcase подтверждён на официальных книгах:

```text
SME      × Удмуртия × class 47 × overdue_fx = 6
SME_IE   × Удмуртия × class 47 × overdue_fx = 6
```

Оба значения возникают source-preserving inheritance внутри собственных scopes.

Далее scope dominance передаёт SME lower bound в общий рынок, а corporate региональный total Удмуртии ограничивает cell сверху. В результате:

```text
CORPORATE_TOTAL × Удмуртия × class 47 × overdue_fx = 6
```

получает `PUBLICATION_CLOSURE_IDENTIFIED` до оптимизационного выбора. В прежнем corporate-only контуре эта РКВС оставалась примерно `[0; 6.5)`.

Это целевой доказательный эффект сегментных таблиц: наружу SME/IE детализация не восстанавливается, но их разреженные официальные маржи сужают общий рынок.

## Реальный размер multi-scope graph 01.07.2026

Проверенная структура:

```text
source observations:                 18 266
atomic regions:                          85
real OKVED2 classes:                     88
latent atomic components:            89 760
all quantities:                      228 098
quantity relations:                 451 371
publication partitions:               3 962

compiled latent LP variables:         89 760
compiled Solver rows:                198 178
compiled nnz:                      1 571 680
corporate target expressions:         74 800
```

После первого multi-scope deterministic wave ledger содержит десятки тысяч publication facts; performance-critical feedback из Fact Ledger в quantity bounds поэтому переведён с per-cell `DataFrame.at` на stable quantity indices + NumPy arrays.

Профилированный 01.07 run после этой оптимизации показывал ориентировочно:

```text
source loading                ~3.1 s
quantity graph               ~11.8 s
publication graph             ~2.8 s
first full interval closure  ~11.7 s
subsequent seeded closure       ~1 s scale
```

Фактическое время sandbox нестабильно и не является SLA; цифры приведены только как regression-scale reference.

## Сильный rounding profile

Официальный ±0.5 млн для каждой source publication остаётся HARD.

Strong tier решает:

```text
tau_star = min max |A_j x - P_j|
l1_star  = min sum |A_j x - P_j| при tau <= tau_star + numerical tolerance
```

`tau_star` рассчитывается из конкретного периода; это не заданный economic tolerance.

## Relaxed rounding для накопленной target uncertainty

Широкий целевой диапазон может естественно возникать через несколько aggregates/residuals. Система не умножает ±0.5 на длину пути и не увеличивает source tolerance.

Для weak practical tier введён отдельный baseline:

```text
relaxed_l1_star = min sum |A_j x - P_j|
```

при тех же hard official source intervals, но без обязательного удержания на `tau_star`.

Для каждого допустимого publication bucket целевой corporate РКВС Solver временно накладывает bucket и заново минимизирует whole-model L1. Если один bucket существенно дешевле альтернатив и укладывается в global budget относительно `relaxed_l1_star`, он получает `ROUNDING_PREFERRED`.

`max_linf_degradation_mln=None` по умолчанию: weak tier может использовать весь законный source-rounding room. Опциональное значение добавляет cap выше strong `tau_star`.

## Защита мелких РКВС

Controlled weak selection по умолчанию имеет:

```text
allow_zero_selection = False
```

Если bucket `0` всё ещё математически возможен, weak selection target пропускает. Ноль может быть доказан deterministic, inheritance, strict min/max или strong optimal-face механизмом, но не выбирается слабой эвристикой из-за близости benchmark к нулю.

## Rounding provenance

Добавлены/используются уровни:

- `ROUNDING_OPTIMUM_IDENTIFIED`;
- `ROUNDING_PREFERRED`;
- `ROUNDING_SELECTED`;
- соответствующие closure descendants.

Assumption tier всегда наследуется, поэтому preferred/selected premise не может после deterministic closure стать strict fact.

`rounding_profiles_grid`, `summary` и audit теперь различают:

- `tau_star_mln`;
- strong `l1_star_mln`;
- `relaxed_l1_star_mln`;
- фактический `relaxed_linf_at_l1_mln` returned witness.

Relaxed witness L∞ считается по actual absolute-residual variables, а не по свободной auxiliary `tau` column.

## Производительные исправления

Multi-scope граф выявил два hot spots, которые устранены без изменения математики:

1. publication fact feedback переведён на NumPy bounds вместо десятков тысяч `DataFrame.at`;
2. Fact Ledger больше не materialize/sort полный DataFrame на каждом publication pass только ради zero-count; current facts выбираются напрямую по stable record indices.

Interval closure сохраняет persistent compiled topology и seeded waves после новых bucket bounds.

## Tests / repository checks

Финальный кодовый контур этой волны:

- `pytest -q tests/cbr_sors_restoration` → `70 passed, 1 skipped`;
- полный `pytest -q` → `94 passed, 7 skipped, 1 failed`;
- единственный общий fail — существующий `stratbox.macrobanks.cbr_forms`, потому что в sandbox отсутствует `dbfread`; зависимость объявлена в `pyproject.toml`, SORS в stack trace не участвует;
- `scripts/check_release_integrity.py` → PASS;
- `scripts/check_internal_imports.py` → все доступные модули PASS, тот же внешний `cbr_forms/dbfread` fail;
- real 01.07 fixture остаётся opt-in через `STRATBOX_SORS_REAL_20260701_DIR`.

Unit regressions отдельно проверяют:

- DOMINANCE propagation;
- scope-aware identities/tokens;
- candidate buckets для накопленного диапазона;
- запрет weak-zero selection;
- bucket competition preference;
- relaxed L∞ audit через actual residual variables;
- Fact Ledger acceptance of `ROUNDING_PREFERRED`;
- source-preserving inheritance и provenance tiers.

## Production Solver caveat текущего sandbox

Production backend — optional dependency `highspy>=1.11,<2`. В текущем sandbox `highspy` отсутствует, поэтому полный multi-scope production путь `feasibility → strict min/max → strong rounding → relaxed bucket competition` невозможно подтвердить end-to-end именно штатным persistent backend.

Fail-closed semantics сохраняется: без успешного global feasibility provisional publication facts не становятся accepted user facts. Sparse compiler, augmented rounding mathematics and selection logic покрыты unit/structural tests; deterministic multi-scope semantics проверены на официальном 01.07.2026 set.
