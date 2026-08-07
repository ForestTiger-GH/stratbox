# Методология SORS restoration

## 1. Два объекта вместо одного

Для каждой РКВС существует latent-величина `x` — скрытая денежная сумма, и publication-величина `p` — целое число млн руб., которое было бы опубликовано ЦБ.

При шаге публикации 1 млн руб. официальное `p=6` задаёт latent bucket приблизительно `[5.5; 6.5)`. Поэтому `p=6` может быть восстановлено точно, даже когда `x` не является точкой.

## 2. Latent quantity graph

Внутренний куб использует 85 атомарных регионов, 88 реальных классов ОКВЭД2 и четыре непересекающихся компонента:

```text
performing_rub
overdue_rub
performing_fx
overdue_fx
```

Шесть пользовательских метрик (`debt_rub`, `overdue_rub`, `debt_fx`, `overdue_fx`, `debt_total`, `overdue_total`) являются линейными quantity nodes над компонентами.

Официальные 01_05_A, 01_02_C, 01_03_C и 01_02_A задают интервальные агрегаты. `01_05_D` остаётся validation/history source и не сужает основной официальный четырехкнижный контур.

## 3. Deterministic Publication Fixed Point

До любого оптимизационного поиска выполняется самостоятельный цикл.

### 3.1 Interval closure

Для точного latent-отношения `parent = sum(children)` распространяются границы:

```text
parent.lower >= sum(child.lower)
parent.upper <= sum(child.upper)
child.upper <= parent.upper - sum(other.lower)
child.lower >= parent.lower - sum(other.upper)
```

Неотрицательность и открытость publication endpoints сохраняются.

Complete/disjoint publication hierarchy дополнительно компилируется в exact **latent** relations между опубликованными агрегатами. Например, скрытый национальный итог точно равен сумме скрытых региональных итогов, хотя их independently rounded representatives могут давать `6 + 5 = 11` при опубликованном parent `10`. Поэтому grouped residuals участвуют в дешёвом closure, но integers публикации никогда не вычитаются как точные бухгалтерские суммы.

### 3.2 Promotion publication buckets

Если текущий latent interval целиком округляется в один integer bucket, создаётся publication fact. В частности, `[0; 0.31] → 0` является точным publication-zero.

### 3.3 Source-preserving inheritance

Inheritance не является вычитанием округлённых чисел. Поэтому `parent=v` плюс нулевые siblings **недостаточны**: неизвестному ребёнку запрещено просто присвоить `v`. Система создаёт Published Mass Token из уже установленного положительного publication fact. Через полное непересекающееся разбиение токен локализуется только когда один child **уже имеет точный publication fact с тем же `v`**, а каждый sibling имеет точный publication-zero. Несколько независимых локализаций одного токена (например Россия→Удмуртия и Россия→класс 47) пересекают его region/class support; новая РКВС получает `v` лишь когда support становится одной region×class cell.

Metric algebra (`debt = performing + overdue`) намеренно исключена из inheritance: независимое округление не позволяет считать гипотетический `performing` равным опубликованному `debt` только потому, что `overdue` публикуется как ноль.

### 3.4 Возврат publication fact в latent layer

Обычный publication fact `p` накладывает bucket `interval(p)`. Только `LATENT_POINT_IDENTIFIED` имеет право фиксировать latent variable как точку.

После bucket tightening снова запускается interval closure. Цикл заканчивается только тогда, когда новые publication facts/inheritance больше не изменяют latent bounds. Само появление нового факта, уже полностью следующего из текущих bounds, повторного latent-прохода не требует. `max_fixed_point_passes` является только аварийным fuse: достижение лимита останавливает run с ошибкой и **не разрешает** переходить к Solver с частично замкнутым deterministic state.

## 4. Evidence provenance

Каждый endpoint имеет `lower_assumption_tier` / `upper_assumption_tier`:

- tier 0 — только официальные latent constraints;
- tier 1 — source-preserving publication inheritance и его следствия;
- tier 2 — minimum-rounding-distortion optimal face и его следствия;
- tier 3 — controlled rounding selection и его следствия.

При суммах/остатках результат получает максимальный tier использованных premises. Это предотвращает provenance laundering: факт, выведенный из inherited `6`, не может после closure автоматически стать tier-0 strict fact.

## 5. Global feasibility gate

После первого deterministic fixed point выполняется полная latent feasibility LP. До успешного gate все publication facts считаются provisional. При конфликте результат не выпускается как accepted data.

После Solver-волн, породивших новые deterministic publication facts, latent feasibility перепроверяется. Если reconstructed buckets делают весь latent-контур несовместимым, run получает `PUBLICATION_FEASIBILITY_CONFLICT`.

## 6. Optimization fixed point

### Tier A — min/max

Для перспективной region×class×metric (и при необходимости component) решаются `min` и `max` на текущем feasible set. Targets являются общими linear expressions, поэтому пользовательская метрика может быть идентифицирована даже при вариативных внутренних компонентах.

Новые bounds/facts немедленно возвращаются в полный deterministic publication fixed point.

Каждая пользовательская метрика присутствует в Solver как стабильная dynamic linear row. Поэтому publication bucket, найденный между Solver-волнами, после refresh ограничивает именно сумму соответствующих latent components; одних независимых column bounds для этого недостаточно.

### Tier B — Minimum Rounding Distortion

Официальные ±0.5 не расширяются. Внутри них ищется latent solution, максимально близкое к исходным integer representatives ЦБ.

Сначала минимизируется:

```text
τ = max_j |A_j x - P_j|
```

затем при `τ <= τ* + ε`:

```text
sum_j |A_j x - P_j|
```

Тем самым rounding dust распределяется в свободных областях модели вместо искусственного блокирования узких РКВС.

### Tier C — optimal-face certification

После фиксации L∞/L1 optimum для каждого target снова считаются min/max. Если весь optimal-face range лежит в одном publication bucket, создаётся `ROUNDING_OPTIMUM_IDENTIFIED`.

### Tier D — controlled joint selection

Последний уровень применяется только при включённом `SorsSelectionPolicy`. По умолчанию кандидат обязан быть узким одновременно в абсолютном и относительном смысле: width не более `3 млн руб.` и не более `1%` выбранного publication bucket (оба порога конфигурируемы). Поэтому допуск «несколько миллионов» не превращается в разрешение грубо выбирать маленькие значения. Узкие targets получают bucket по одному общему L1-optimal benchmark. Сам benchmark является общим глобально допустимым witness для всех выбранных buckets. Кандидаты сначала группируются по связанным Solver-компонентам, затем для вычислительной управляемости большие группы проверяются ограниченными joint batches на **одном и том же исходном optimal face**. Принятый batch никогда не становится premise для проверки следующего; общий benchmark уже является совместным witness. Поэтому batching не превращается в жадную цепочку «сначала A, затем благодаря A — B». После promotion deterministic cascade дополнительно проходит общий latent-feasibility gate.

Каждая принятая группа снова запускает deterministic publication fixed point.

## 7. Fixed point всего расчёта

После любого нового Solver/publication факта Tier A получает шанс снова, потому что более слабый publication fact способен открыть более сильный вывод для соседней РКВС. Расчёт заканчивается, когда полный optimization round не создаёт новых accepted publication facts. `max_fixed_point_rounds` является только аварийным fuse: если лимит достигнут при продолжающемся каскаде, run завершается `SorsOptimizationFixedPointLimitError`, а частично замкнутое состояние не выдаётся как финальный результат.

## 8. Crosswalk

Legacy→ОКВЭД2 остаётся отдельным conditional evidence layer после official publication fixed point. Он не может повышать собственные assumptions до official facts и не смешивается с основной source-preserving цепочкой.
