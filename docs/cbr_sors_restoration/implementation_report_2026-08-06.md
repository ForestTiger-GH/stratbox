# Внедрение поклеточного RKVS Target Engine

Дата: 2026-08-06  
Версия Strategy Box: `0.6.0`

## Цель

Перестроить SORS restoration вокруг отдельной базовой РКВС:

```text
регион × класс ОКВЭД2 × денежный компонент
```

Для каждой цели система должна пошагово добавлять связанные официальные уравнения и принимать только единственное допустимое значение.

## Реализовано

1. Каталог всех 29 920 базовых компонентных целей.
2. Постоянный quantity/relation graph и одна глобальная sparse LP.
3. Persistent affected closure без полной пересборки графа.
4. Cumulative local horizons от CELL до GLOBAL_CONNECTED.
5. Безопасная outer-approximation проекция глобальной модели.
6. Внутренняя служебная проверка единственности одной координаты.
7. Разделение exact и publication-bucket uniqueness.
8. Append-only Fact Ledger с supersession и proof trail.
9. Каскад direct fact → affected closure → соседние факты.
10. Приоритетная очередь и fixed-point orchestration.
11. Новые result grids и Excel sheets.
12. Feasibility gate: без подтверждённой глобальной совместимости факты не принимаются.
13. Crosswalk оставлен отдельным evidence layer до исправления несовместимых mapping-профилей.

## Удалено

Старый модуль `strict/planning.py`, ориентированный на глобальный batch min/max план шести производных метрик.

## Доказательный инвариант

Каждая локальная система создаётся удалением строк из глобальной модели при сохранении всех переменных выбранных строк. Следовательно, глобальное допустимое множество является подмножеством локального. Единственность цели в локальной модели является достаточным доказательством её глобальной единственности.

## Публичный API

Введены:

- `SorsCellScope`;
- `SorsCellResolutionConfig`;
- `SorsRunConfig.cell_resolution`.

Режимы: `closure`, `targets`, `priority`, `all`.

## Совместимость

Обратная совместимость со старым `SorsCertificationConfig` намеренно не сохранялась. Проектное правило — формировать сразу целевую архитектуру.

## Проверка на реальных данных 01.06.2026

Проверка выполнена на четырёх обязательных книгах Банка России из рабочего набора пользователя. Для sandbox использовался внешний тестовый адаптер к HiGHS, встроенному в SciPy; адаптер не включён в репозиторий, production-код продолжает использовать официальный `highspy`.

Фактический путь:

```text
15 874 source observations
→ 85 atomic regions
→ 88 OKVED2 classes/categories
→ 76 118 quantity nodes
→ 46 198 sum relations
→ 7 initial closure passes
→ 29 920 active RKVS component variables
→ 1 318 official sparse constraints
→ global STRICT feasibility: OPTIMAL, objective 0
```

Initial closure promoted 11 274 publication-precision component facts.

Контрольная ненулевая цель:

```text
Белгородская область × класс 01 × overdue_rub
```

Локальная система расширялась от одной переменной через региональные, окружные и национальные отношения до полного connected-компонента. На полном горизонте допустимый диапазон остался приблизительно `[0; 9 996.5]` млн руб., поэтому цель получила статус `UNRESOLVED_GLOBAL` и в Fact Ledger не была повышена. Это подтверждает ключевой safety-инвариант: движок не превращает одно произвольное допустимое решение в восстановленный факт.

`REGION_PARENT` и любые другие горизонты, не добавляющие новых строк к уже собранной cumulative-системе, теперь фиксируются в трассировке со статусом `NO_NEW_CONSTRAINTS` и не запускают повторный Solver.

## Ограничения среды проверки

- `highspy` отсутствовал в доступном package mirror; тестовый SciPy–HiGHS adapter применялся только снаружи репозитория.
- Общий smoke-import всего Strategy Box в sandbox блокируется существующим внешним пакетом `dbfread`, отсутствующим в mirror. Зависимость относится к старому домену `cbr_forms`, а не к SORS RKVS Target Engine.
