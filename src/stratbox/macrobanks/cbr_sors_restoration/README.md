# CBR SORS Restoration

Домен восстанавливает **регион × класс ОКВЭД2 × показатель** для общего корпоративного кредитного портфеля из пересекающихся публикаций Банка России.

Основной продукт остаётся один:

```text
CORPORATE_TOTAL × region × OKVED2 class × metric
```

Публикации по МСП и МСП–ИП используются только как дополнительные официальные ограничения скрытой модели. Детальный GRID по МСП/МСП–ИП не является целью и наружу не экспортируется.

## Две параллельные реальности

ЦБ публикует целые млн руб. Поэтому опубликованное `6` означает:

```text
published_value = 6
latent amount   ∈ [5.5; 6.5)
```

SORS Restoration одновременно хранит:

1. **publication layer** — целое значение, которое могло бы стоять в таблице ЦБ;
2. **latent layer** — непрерывную скрытую денежную сумму, совместимую с округлением всех источников.

Publication-level факт никогда автоматически не превращается в утверждение `latent x = 6`. Только `LATENT_POINT_IDENTIFIED` фиксирует вещественную точку.

## Три вложенных скрытых портфеля

Внутри одной sparse-модели существуют три скрытых куба:

```text
SME_IE <= SME <= CORPORATE_TOTAL
```

для каждой одинаковой `region × class × component`.

Каждый scope имеет собственные source observations, publication partitions и Published Mass Tokens. Совпавшее число `6` в SME и CORPORATE_TOTAL — это **два разных опубликованных объекта**. Информация между scopes переносится только hard-неравенствами вложенности, а не inheritance.

Цели Solver и пользовательский результат формируются только для `CORPORATE_TOTAL`. SME и SME_IE — auxiliary latent scopes.

## Обязательные источники

Один запуск использует десять книг/контуров:

### Общий корпоративный рынок

- `01_05_A_Debt_corp_YYYYMMDD.xlsx` — регионы × традиционная классификация;
- `01_02_C_Debt_corp_by_activity.xlsx` — РФ × классы ОКВЭД2;
- `01_03_C_Loans_corp_by_fd_activity_YYYYMMDD.xlsx` — ФО × разделы ОКВЭД2;
- `01_02_A_Debt_corp_by_activity.xlsx` — РФ × традиционная классификация.

### МСП / МСП–ИП как constraint scopes

- `01_11_Debt_sme.xlsx` — национальные итоги SME и SME_IE;
- `01_11_F_Debt_sme_by_activity.xlsx` — SME × классы ОКВЭД2;
- `01_11_I_Debt_ie_by_activity.xlsx` — SME_IE × классы ОКВЭД2;
- `01_12_A_Loans_sme_by_fd_activity_YYYYMMDD.xlsx` — SME × ФО × разделы ОКВЭД2;
- `01_13_F_Debt_sme_subj.xlsx` — SME × регионы;
- `01_13_I_Debt_sme_subj.xlsx` — SME_IE × регионы.

В `01_12_A` используются только stock-листы `задолженность` и `в т.ч. просроченная задолженность`. Лист `объем` является потоком выдач за период и в одно-периодную модель остатков не входит.

`01_05_D_Debt_subj.xlsx` остаётся опциональным историческим источником.

## Главная последовательность

```text
CBR books (CORPORATE_TOTAL + SME + SME_IE)
→ canonical multi-scope source bundle
→ source validation
→ latent quantity graph
→ publication partition graph
→ deterministic publication fixed point
    exact interval closure
    → DOMINANCE propagation
    → zero / single-bucket facts
    → source-preserving Published Mass Token inheritance
    → inherited buckets back to latent bounds
    → scope dominance SME_IE <= SME <= CORPORATE_TOTAL
    → overdue/debt dominance
    → repeat until no new facts and no new bounds
→ global latent feasibility gate
→ optimization fixed point
    strict min/max on CORPORATE_TOTAL targets
    → full deterministic fixed point
    → minimum source-rounding distortion (L∞ then L1)
    → min/max on the rounding-optimal face
    → full deterministic fixed point
    → publication-bucket competition
    → jointly validated controlled selection
    → full deterministic fixed point
→ final CORPORATE_TOTAL restored grid
→ optional conditional legacy→ОКВЭД2 crosswalk
```

Solver не запускается, пока первый deterministic fixed point не исчерпан. После любой новой Solver-promotion система снова полностью проходит deterministic fixed point.

## DOMINANCE

`DOMINANCE` — общий тип hard-неравенства скрытых денежных масс.

Внутри каждой РКВС и совместимых агрегатов используются, в частности:

```text
overdue_rub   <= debt_rub
overdue_fx    <= debt_fx
overdue_total <= debt_total

debt_rub      <= debt_total
debt_fx       <= debt_total
overdue_rub   <= overdue_total
overdue_fx    <= overdue_total
```

и между одинаковыми supports разных portfolio scopes:

```text
SME_IE <= SME <= CORPORATE_TOTAL
```

Для `A <= B` deterministic closure дешёво выполняет:

```text
upper(A) <= upper(B)
lower(B) >= lower(A)
```

На LP-уровне портфельная вложенность задаётся hard inequalities базовых непересекающихся компонентов; этого достаточно для всех агрегатов.

## Source-preserving inheritance

Inheritance не означает арифметику округлённых представителей.

Допустимо:

```text
одна официальная mass token = 6
→ в полном географическом разбиении официально локализована в Удмуртию = 6
→ в полном отраслевом разбиении официально локализована в класс 47 = 6
→ supports пересеклись в одной РКВС
→ PUBLISHED_VALUE_INHERITED = 6
```

Недопустимо:

```text
parent = 6
siblings = 0
→ неизвестный child = 6
```

из одного только вычитания опубликованных integers. Независимое округление может нарушать такое integer-тождество.

Tokens никогда не переходят между portfolio scopes. `SME → CORPORATE_TOTAL` работает только через DOMINANCE.

## Накопленная погрешность округления

У каждой **исходной** публикации сохраняется официальный интервал округления ±0.5 млн руб. при шаге публикации 1 млн. Этот source tolerance не расширяется из-за длины пути в графе.

Если целевая РКВС прошла через несколько агрегатов, её итоговый диапазон может стать, например, `[10; 12]`. Это уже результат совместного распространения всех исходных интервалов и структурной неопределённости. Система не считает `0.5 × число переходов`: одна и та же source uncertainty могла участвовать в нескольких путях, и ручное суммирование дважды посчитало бы одну погрешность.

### Minimum rounding distortion

После строгого min/max модель находит:

```text
L∞*: минимально возможное максимальное |A_j x - P_j|
L1*: минимальную суммарную |A_j x - P_j| при L∞ = L∞*
```

`L∞*` рассчитывается отдельно для каждой даты. Это не настраиваемая «допустимая ошибка РКВС» и не обязано равняться 1/3 млн.

### Bucket competition

Если на сильном minimum-rounding face у target остаётся несколько целых publication buckets, например `10, 11, 12`, включается отдельный **слабый** уровень выбора. Он специально не обязан оставаться на найденном `L∞*`: накопленная неопределённость целевой РКВС может потребовать другого распределения округлительной пыли, хотя каждая исходная цифра ЦБ всё ещё должна оставаться внутри собственного hard-интервала ±0.5 млн.

Для каждого bucket:

1. все исходные publication intervals остаются жёсткими;
2. временно накладывается bucket target;
3. минимизируется глобальный L1 по всем source residuals;
4. сравнивается цена альтернатив;
5. выбранные buckets затем ещё раз проверяются совместно одним global witness.

В качестве базы слабого уровня отдельно вычисляется `relaxed_l1_star`: минимальный глобальный L1 **без** ограничения `tau <= L∞*`. Поэтому значение `L∞*=1/3` на одной дате не превращается в скрытый вечный tolerance. При необходимости конфигурация может вернуть дополнительный cap через `max_linf_degradation_mln`, но по умолчанию он отсутствует.

Если один bucket однозначно дешевле других минимум на `min_preference_l1_gap_mln` и укладывается в глобальный L1-budget относительно `relaxed_l1_star`, он получает:

```text
ROUNDING_PREFERRED
```

То есть выбирается число, которое требует наименьшего перераспределения rounding dust во **всей** системе, а не midpoint локального диапазона.

### Защита маленьких РКВС

По умолчанию слабый controlled-selection **не имеет права выбрать target, пока bucket `0` остаётся допустимой альтернативой** (`allow_zero_selection=False`).

Ноль может быть принят строгими механизмами:

- deterministic zero / single-bucket closure;
- source-preserving inheritance;
- strict min/max;
- rounding-optimal-face identification.

Но маленькая ненулевая РКВС не превращается в 0 только потому, что один benchmark solution оказался ниже 0.5 млн.

## Доказательные уровни

Основные `evidence_method`:

- `SOURCE_PUBLISHED` — непосредственно опубликовано ЦБ;
- `LATENT_POINT_IDENTIFIED` — скрытая денежная величина доказана как точка;
- `PUBLISHED_BUCKET_IDENTIFIED` — весь строгий latent interval лежит в одном bucket;
- `PUBLISHED_VALUE_INHERITED` — исходная опубликованная mass token однозначно локализована;
- `PUBLICATION_CLOSURE_IDENTIFIED` — строгий publication-level каскад;
- `ROUNDING_OPTIMUM_IDENTIFIED` / `ROUNDING_OPTIMUM_CLOSURE` — один bucket на minimum-rounding face;
- `ROUNDING_PREFERRED` / `ROUNDING_PREFERRED_CLOSURE` — несколько buckets математически возможны, но один имеет существенно лучший глобальный rounding profile;
- `ROUNDING_SELECTED` / `ROUNDING_SELECTED_CLOSURE` — последний контролируемый совместно проверенный выбор.

Каждая latent lower/upper bound несёт `assumption_tier`. Более слабый rounding premise не может после closure превратиться в якобы strict-доказательство.

## Selection policy

```python
from stratbox.macrobanks.cbr_sors_restoration import SorsSelectionPolicy

policy = SorsSelectionPolicy(
    enabled=True,
    bucket_competition_enabled=True,
    fallback_benchmark_selection_enabled=True,
    max_candidate_buckets=5,
    max_relative_interval_width=0.25,
    max_interval_width_mln=None,      # optional emergency guard only
    min_preference_l1_gap_mln=0.01,
    allow_zero_selection=False,
    max_linf_degradation_mln=None,   # optional cap above L∞*; default uses full hard source intervals
    max_l1_degradation_mln=1.0,
    max_joint_selection_targets=25,
)
```

`max_l1_degradation_mln` относится к **суммарной глобальной source-rounding objective всего Solver** относительно `relaxed_l1_star`, а не разрешает отдельной РКВС ошибиться на 1 млн руб. `max_linf_degradation_mln=None` не расширяет интервалы источников: он лишь не заставляет слабый выбор оставаться около сильного `L∞*`; hard ±0.5 каждой публикации остаётся неизменным.

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
    sme_national_totals='01_11_Debt_sme.xlsx',
    sme_national_okved2='01_11_F_Debt_sme_by_activity.xlsx',
    sme_ie_national_okved2='01_11_I_Debt_ie_by_activity.xlsx',
    sme_federal_district_okved2='01_12_A_Loans_sme_by_fd_activity_20260701.xlsx',
    sme_regional_totals='01_13_F_Debt_sme_subj.xlsx',
    sme_ie_regional_totals='01_13_I_Debt_sme_subj.xlsx',
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

Публичный `primary_portfolio_scope` фиксирован как `CORPORATE_TOTAL`: вспомогательные SME/SME_IE scopes нельзя случайно экспортировать как самостоятельный восстановленный продукт.

Основные результаты:

```python
result.regional_okved2_grid       # только CORPORATE_TOTAL final publication grid
result.restored_facts_grid        # принятые corporate восстановленные факты
result.facts_ledger_grid          # полный audit ledger, включая auxiliary scopes
result.components_grid            # только corporate component view
result.publication_partitions_grid
result.publication_tokens_grid
result.inheritance_events_grid
result.fixed_point_passes_grid
result.target_bounds_grid
result.rounding_profiles_grid     # global + per-scope rounding diagnostics
result.selection_attempts_grid
result.solver_runs_grid
result.conflicts_grid
```

## Техническая структура

```text
portfolio.py    — реестр scopes и вложенности
sources/        — 10 source adapters + multi-scope validation
registries/     — география, ОКВЭД2, publication categories
publication/    — rounding, ledger, partitions, tokens, inheritance, fixed point
strict/         — multi-scope quantities, DOMINANCE closure, sparse compiler, feasibility
optimization/   — corporate targets, distortion, optimal face, bucket competition, selection
linear/         — persistent HiGHS session
crosswalk/      — отдельный conditional legacy→OKVED2 evidence layer
result_grid.py  — corporate-only primary publication output
export.py       — Excel audit/pivots
```

`highspy>=1.11,<2` является production Solver backend. Внутренние SciPy HiGHS bindings библиотека не использует.
