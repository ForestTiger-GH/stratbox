# CBR SORS Restoration 0.3.1

Домен строит одно-периодный региональный куб задолженности по классам ОКВЭД2 и строго разделяет два результата:

1. **STRICT** — значения, которые однозначно следуют только из официальных публикаций Банка России;
2. **CONDITIONAL_BRIDGE_OPTIMUM** — оценки и диапазоны, которые следуют из всех публикаций при условии глобально минимальной переклассификации между legacy-атомами и ОКВЭД2.

Условные bridge-результаты никогда не повышаются до восстановленных фактов.

## Источники

Используются все опубликованные ячейки выбранного периода:

- `01_05_A`: 96 географических узлов × 26 традиционных строк × 6 денежных метрик;
- `01_02_A`: Россия × 26 традиционных строк × 6 метрик;
- `01_02_C`: Россия × опубликованные классы/`Прочее` × 6 метрик;
- `01_03_C`: 8 федеральных округов × 16 разделов × задолженность/просрочка.

Физические имена файлов могут содержать браузерные суффиксы. Дата и логическая структура проверяются по содержимому.

## Денежные компоненты

Внутри модели используются непересекающиеся величины:

```text
performing_rub
overdue_rub
performing_fx
overdue_fx
```

Напрямую сертифицируются:

```text
debt_rub
debt_fx
debt_total
overdue_rub
overdue_fx
overdue_total
```

Листы `итого` сохраняются как самостоятельные интервальные ограничения.

## STRICT-модель

Переменная:

```text
region × OKVED2 class × monetary component
```

Ограничения:

- общие показатели всех опубликованных географических узлов;
- национальные классы ОКВЭД2;
- федеральные округа × разделы ОКВЭД2;
- неотрицательность;
- публикационные интервалы округления.

Для каждой цели решаются `min` и `max`. Только схлопнувшийся диапазон или единый публикационный bucket попадает в `facts_grid` как reconstructed fact.

## Условная atom-flow модель

Традиционная иерархия представлена 25 непересекающимися атомами. Все legacy-публикации являются жёсткими ограничениями, а не мягкими точками подгонки.

Предпочтительные atom→class связи формируются из версионированного методологического bridge. Чтобы неполнота bridge не делала реальные публикации несовместимыми, модель содержит:

- явные потоки по предпочтительным рёбрам;
- остаток legacy-атома вне предпочтительных рёбер;
- остаток нового класса, полученный вне предпочтительных рёбер;
- баланс двух остаточных масс по каждому региону и денежному компоненту.

Цель:

```text
minimize total off-preferred reclassification mass
```

После нахождения глобального минимума в модель добавляется ограничение:

```text
bridge_objective <= optimum + tolerance
```

И только затем для каждой цели выполняется настоящий `min/max` по **всему множеству глобально оптимальных решений**. Один выбранный профиль не фиксируется; singleton-shortcut отсутствует.

## Результаты

```text
canonical_grid          — все исходные публикации
facts_grid              — PUBLISHED + только STRICT reconstructed
estimates_grid          — условные bridge-точки и bridge-идентифицированные значения
bounds_grid             — strict min/max
bridge_bounds_grid      — min/max среди всех глобально оптимальных bridge-решений
bridge_diagnostics_grid — предпочтительные потоки и остаточная переклассификация
mapping_edges_grid      — полный atom/class граф и признаки preferred/fallback
constraints_grid        — все ограничения обеих моделей
conflicts_grid          — ошибки совместимости уровня модели
```

## Solver

Поддерживается только официальный `highspy`:

```bash
pip install "stratbox[sors-restoration]"
```

Внутренние SciPy/HiGHS bindings намеренно не используются: они бинарно зависят от конкретных версий NumPy/SciPy и вызывали нестабильность в Colab.

## Colab

После установки другой сборки Strategy Box под тем же runtime нужно полностью удалить старый пакет и перезапустить session. Используйте пример `examples/cbr_sors_restoration_colab.py`.

## API

```python
from stratbox.macrobanks.cbr_sors_restoration import (
    SorsRunConfig,
    SorsSourceFiles,
    SorsTargetScope,
    run_sors_restoration,
)

result = run_sors_restoration(
    SorsSourceFiles(
        regional_traditional="01_05_A_Debt_corp_20260601 (1).xlsx",
        national_traditional="01_02_A_Debt_corp_by_activity.xlsx",
        national_okved2="01_02_C_Debt_corp_by_activity.xlsx",
        fd_okved2="01_03_C_Loans_corp_by_fd_activity_20260601 (1).xlsx",
    ),
    SorsRunConfig(
        as_of_date="2026-06-01",
        target_scope=SorsTargetScope(
            region_names=("г. Москва",),
            class_codes=("16",),
            metrics=("debt_total",),
        ),
    ),
)
```

## Методологическая граница

Bridge `cbr-legacy-okved2-bridge-2026.2` остаётся `METHODOLOGY_DERIVED_CONDITIONAL`: готовая официальная денежная матрица legacy→ОКВЭД2 отсутствует. Поэтому даже точка, неизменная среди всех minimum-reclassification решений, хранится в `estimates_grid`, а не в strict facts.
