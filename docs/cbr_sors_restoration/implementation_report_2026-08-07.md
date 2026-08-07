# SORS Restoration — implementation report 2026-08-07

Версия Strategy Box: `0.7.0`  
Версия архитектуры: deterministic publication fixed point + rounding-aware optimization.

## Что внедрено

Рефактор меняет не величину публикационного допуска, а саму постановку восстановления.
Скрытая денежная величина (`latent`) и восстанавливаемое целочисленное значение
официальной публикации (`publication`) теперь являются двумя разными уровнями.

Реализовано:

- отдельный пакет `publication/`;
- сохранение исходного published representative и source lineage внутри quantity graph;
- first-class `portfolio_scope` (`CORPORATE_TOTAL` в текущем контуре);
- complete/disjoint publication partition graph;
- `PublishedMassToken` с region/class support;
- source-preserving value inheritance;
- самостоятельный deterministic fixed point
  `interval closure ↔ publication facts ↔ token inheritance ↔ publication-bucket bounds`;
- жёсткий запрет перехода к Solver, если deterministic fixed point не сошёлся;
- assumption tiers для lower/upper bounds и propagation через residual arithmetic;
- защита от provenance laundering: слабый published/rounding premise не становится
  latent-exact фактом только из-за последующего interval closure;
- unified target catalog для шести пользовательских `region × class × metric` и
  четырёх внутренних component targets;
- отдельный `optimization/` layer;
- strict min/max как самый сильный Solver-tier;
- minimum L∞ rounding distortion, затем L1 refinement;
- min/max на rounding-optimal face;
- optional controlled narrow-range selection через common-witness connected batches;
- полный deterministic publication fixed point после каждой новой Solver-promotion;
- повторный global latent-feasibility gate после publication cascades внутри optimization;
- Fact-Ledger-driven final result grid;
- отдельные audit surfaces для partitions, tokens, inheritance, promotions,
  optimization rounds, target bounds, rounding profiles и selection attempts;
- старый cell-resolution monolith и устаревшие compatibility contracts удалены.

## Критическое правило inheritance

Inheritance **не** является арифметикой над округлёнными числами.

Из:

```text
parent = 6
sibling A = 0
sibling B = 0
unknown child = ?
```

запрещено автоматически выводить `unknown child = 6`.

Published Mass Token локализуется через complete/disjoint same-metric partition только
если:

1. один child уже имеет установленный publication fact, равный тому же `v`;
2. каждый sibling уже имеет установленный publication-zero;
3. локализация относится к тому же token/source mass;
4. независимые локализации токена пересекают support;
5. новое `region × class × metric = v` возникает только при singleton support.

Поэтому кейс типа «Россия=6 → Удмуртия=6, остальные регионы=0» и независимо
«Россия=6 → класс 47=6, остальные классы=0» корректно локализует одну и ту же
видимую массу в `Удмуртия × 47`, а `parent=6 + zeros` без matching child ничего не
легализует.

Наследованный `6` накладывает на latent quantity publication bucket `[5.5; 6.5)`,
а не точку `x=6`.

## Реальная проверка на официальных книгах 01.07.2026

Проверка выполнена на переданном пользователем комплекте Банка России.
МСП/ИП-книги в базовый corporate cube этой волны намеренно не включались.

```text
source rows (с 01_05_D):             16 450
atomic regions:                          85
real OKVED2 classes:                     88
quantities:                          76 118
relations:                           46 198
observation bindings:                 1 324

publication partitions:               1 414
  LATENT_TARGETS:                     1 318
  PUBLISHED_HIERARCHY:                   96
positive source mass tokens:          1 119
inheritance localization events:          6
positive inherited region×class facts:    0

deterministic status:             FIXED_POINT
publication fixed-point outer passes:     1
atomic-component publication-zero:   11 370
region×class×metric publication-zero:11 370
source published aggregate facts:     1 318

latent Solver variables:             29 920
official publication constraints:     1 318
dynamic region×class metric rows:    44 880
total Solver rows:                   46 198
metric/component targets:            74 800
```

Это содержательно ожидаемый результат для общего corporate cube: токены действительно
локализуются в некоторых официальных разбиениях, но ни один положительный support не
схлопывается до одной регионально-отраслевой клетки. Механизм поэтому не создаёт
ненулевые факты искусственно. Известный пример `Удмуртия × 47 = 6` относится к
разреженному МСП-кубу; МСП пока не примешивается к основному corporate Solver.

На текущем sandbox фактическое время последнего реального прогона было примерно:

```text
Excel/source loading:          19.5 s
quantity graph:                 3.5 s
publication graph:              0.7 s
deterministic fixed point:      5.2 s
strict model compilation:       2.3 s
Solver-bound refresh:           0.1 s
full public API (no highspy):  ~33.0 s
```

Это диагностические измерения конкретного окружения, а не performance SLA.

Для независимой проверки каскадной устойчивости тот же deterministic engine прогнан
на 01.06.2026:

```text
source rows:                         15 874
publication partitions:              1 414
deterministic status:            FIXED_POINT
deterministic bound updates:       154 680
atomic-component publication-zero:  11 274
region×class×metric publication-zero:11 274
positive inherited region×class facts: 0
positive source mass tokens:         1 122
inheritance localization events:         5
```

Таким образом, усиление publication hierarchy сохранило ранее проверенные июньские
11 274 нуля и июльские 11 370 нулей; новый inheritance не создаёт положительные
corporate-факты там, где support источника реально не локализуется до одной РКВС.

## Tests / repository checks

На финальной кодовой версии перед сборкой patch-архива:

- `pytest -q tests/cbr_sors_restoration` → `60 passed`;
- полный `pytest -q` → `84 passed, 6 skipped, 1 failed`;
- единственный общий fail — существующий `stratbox.macrobanks.cbr_forms`, потому что
  в sandbox отсутствует внешняя зависимость `dbfread`; SORS-код в stack trace этого
  сбоя не участвует;
- real/performance integration tests остаются opt-in через внешний каталог книг;
- synthetic cascade regression проверяет цепочку
  `inherited bucket → latent bound → новый publication-zero → новая token localization`;
- отдельный regression запрещает ложное правило `parent=v + zero siblings → child=v`;
- pass-limit regression проверяет, что незавершённый deterministic cycle блокирует
  переход к Solver;
- публичный `run_sors_restoration()` повторно прогнан на полном 01.07.2026:
  deterministic status=`FIXED_POINT`, затем штатно возвращён `SOLVER_UNAVAILABLE` из-за
  отсутствующего production `highspy`; 24 058 provisional current facts остались в
  ledger для аудита, а в primary surface принято ровно 0 facts без feasibility gate;
- rounding-distortion toy model независимо проверяется через SciPy/HiGHS test backend
  и воспроизводит L∞ optimum `1/3 млн руб.` для publication representatives `6`, `5`
  и агрегата `10`.

## Production Solver caveat текущего sandbox

Production backend библиотеки — `highspy>=1.11,<2`. В текущем sandbox `highspy`
отсутствует, поэтому полный production путь
`strict min/max → L∞/L1 → optimal face → controlled selection` нельзя было прогнать
end-to-end именно через штатный persistent backend.

Код сохраняет явную семантику `SOLVER_UNAVAILABLE`; provisional deterministic facts
без успешного global feasibility gate не получают финальный accepted status. Solver
математика и augmented distortion model покрыты unit tests, а deterministic часть
проверена на полном официальном срезе 01.07.2026.
