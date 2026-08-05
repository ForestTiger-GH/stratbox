# Conditional bridge

Bridge использует версионированные packaged resources:

- legacy atoms;
- membership старых узлов;
- предпочтительные переходы в классы ОКВЭД2;
- mapping manifest.

Модель хранит preferred flows явно, а fallback mass — факторизованными atom-side и class-side residual. Целевая функция минимизирует fallback mass. После optimum добавляется objective cap, и выбранные region/class/metric цели получают conditional min/max.

Strict component bounds передаются bridge. Publication-zero остаётся интервалом и не фиксируется в математическом нуле. Timeout bridge обозначается как timeout, а не как infeasibility.
