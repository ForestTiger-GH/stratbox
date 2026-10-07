# Strategy Box × MADAR: целевая эпистемическая и смысловая архитектура

**Дата:** 2026-10-07  
**Контур:** Strategy Box, вторая ветка исследований  
**Статус:** Research / Development Input; не спецификация реализации и не миграционный план  
**Цель:** определить, каким должен быть **целевой Strategy Box**, если рассматривать всё его текущее состояние — код, интерфейс, исследования и текущие архитектурные решения — как переходный материал, а в качестве основной методологической рамки использовать актуальную линию MADAR, свежие Stage-3 consolidation-input исследования, исторический корпус MADAR, шесть `mandat-*` репозиториев и `MADAR-supplements`.

---

# 0. Executive conclusion

## 0.1. Главный вывод

Целевой Strategy Box следует проектировать не как приложение для запуска аналитических функций и не как оболочку над наборами данных.

Наиболее точная целевая формула:

> **Strategy Box — эпистемически управляемая аналитическая рабочая среда, в которой источники, наблюдения, определения, модели, аналитические выводы, прогнозы, гипотезы, оценки, решения, артефакты и действия остаются различимыми, связаны прослеживаемыми основаниями и не приобретают более сильный смысл без отдельного основания.**

Иными словами, главный объект Strategy Box — не файл, не DataFrame, не сценарий и даже не аналитический отчёт.

Главным объектом становится **квалифицированный смысловой переход**:

```text
источник
→ зафиксированная публикация / snapshot
→ наблюдение
→ семантически определённое измерение
→ утверждение
→ основание / warrant
→ преобразование / модель / вывод
→ квалифицированный аналитический результат
→ допустимая степень reliance
→ рекомендация / решение
→ commitment
→ действие / эффект
→ последующее наблюдение
→ переоценка / обучение
```

Это **не обязательный линейный pipeline**. Реальная работа образует сеть переходов. Важен смысл каждой связи и запрет на молчаливое усиление статуса.

Самая опасная ошибка для Strategy Box будущего:

```text
что-то было получено
→ значит это данные
→ значит это факт
→ значит это вывод
→ значит этому можно доверять
→ значит это можно использовать
→ значит это решение
→ значит действие разрешено
```

MADAR последовательно показывает, что каждый такой переход может быть неверным даже при технически исправной системе.

---

## 0.2. Что это меняет относительно сегодняшнего Strategy Box

Текущее устройство уже содержит несколько правильных зачатков:

- отделение domain/core от пользовательской поверхности;
- `source → raw → canonical → validation → derived → artifact`;
- структурированные результаты в части доменов;
- provenance/evidence в наиболее зрелых вычислительных подсистемах;
- операции, сценарии, кейсы, события, логи и артефакты;
- AppDock-managed runtime;
- отдельные surface и execution concerns.

Но это следует считать **переходным прототипом**, а не архитектурой, которую требуется сохранить.

Главная проблема текущей картины — категории в основном организованы вокруг:

```text
data pipeline
+
operation/scenario execution
+
files/artifacts/logs
```

Целевая система должна быть организована вокруг:

```text
meaning
+
epistemic status
+
qualified relations
+
Work semantics
+
Authority
+
currentness
+
reliance
```

Технические pipeline, сценарии и интерфейсы становятся реализациями этой семантики.

---

## 0.3. Самые важные инварианты целевого Strategy Box

### Инвариант 1. Source ≠ fact

То, что Банк России, Росстат, банк, компания или другой источник что-то опубликовал, надёжно устанавливает прежде всего факт публикации определённого содержания.

Это ещё не автоматически:

- истинность описываемого состояния мира;
- корректность нашей интерпретации;
- сопоставимость с другим источником;
- достаточность для причинного вывода;
- актуальность для сегодняшнего решения.

### Инвариант 2. Data ≠ observation ≠ evidence ≠ claim

Значение в таблице может быть:

- исходной записью;
- наблюдением;
- нормализованным представлением;
- расчётным значением;
- оценкой;
- восстановленной величиной;
- модельным output;
- входом в evidence argument.

Эти роли нельзя определять форматом файла или именем столбца.

### Инвариант 3. Canonical ≠ true

`canonical` означает каноническое внутреннее представление Strategy Box для определённой семантики.

Оно не означает:

```text
это окончательная истина о мире
```

Canonical representation может быть корректной нормализацией опубликованной величины, внутренне принятой классификацией, версионированным bridge между определениями или текущей рабочей интерпретацией. Её authority ограничена именно этим.

### Инвариант 4. Transformation ≠ evidence

Нормализация, агрегация, пересчёт валют, сведение групп, реконструкция, оптимизация, суммаризация и визуализация сами по себе не добавляют доказательную силу.

Новая доказательная сила появляется только там, где есть отдельный валидный inferential bridge.

### Инвариант 5. Model output ≠ fact about the world

Нужно сохранять различие:

```text
модель
≠ запуск модели
≠ output запуска
≠ утверждение, построенное на output
≠ разрешение использовать это утверждение
```

Это особенно важно для реконструкций, forecasting, normalization, scenario analysis, derived indicators и causal interpretations.

### Инвариант 6. Analysis ≠ Decision

Даже превосходный анализ не получает Decision Authority.

Нужно различать:

```text
Analytical Result
Recommendation
Decision
Commitment
Execution
Observed Outcome
```

Успешный исход не переписывает ex-ante качество решения. Плохой исход не доказывает, что решение было плохим при известной тогда информации.

### Инвариант 7. Evaluation ≠ acceptance ≠ permission

Положительная проверка означает только то, что устанавливает её критерий и evidence.

Она не должна молча превращаться в принятие результата, публикацию, risk acceptance, разрешение на изменение или разрешение на исполнение.

### Инвариант 8. Artifact ≠ Result

Excel, Markdown, график, JSON, ZIP, PDF и UI-карточка — носители и представления.

Смысловой Result существует независимо от конкретного carrier там, где это materially важно.

```text
аналитический вывод
→ Excel-представление
→ Markdown-представление
→ графическое представление
```

Excel не становится владельцем вывода.

### Инвариант 9. Log ≠ Work state ≠ Knowledge

Лог сообщает, что процесс или код зафиксировал определённое событие.

Он не является полным состоянием Work, текущей истиной продукта, автоматически доказательством внешнего эффекта или current knowledge owner.

### Инвариант 10. Historical truth ≠ current reliance

Старый расчёт, прогноз, источник или Evaluation Result может оставаться полностью корректным историческим объектом.

Но его поддержка текущего утверждения может ослабнуть из-за новой публикации, нового definition, изменения классификатора, model version, perimeter, условий, появления defeater или изменения intended use.

Значит Strategy Box должен уметь сохранить историю **без молчаливого объявления её текущей**.

### Инвариант 11. UNKNOWN — нормальный результат

`UNKNOWN` нельзя принудительно превращать в `0`, `False`, отсутствие строки, ошибку, наиболее вероятный вариант, «не найдено» или «не применимо».

Нужно различать там, где это materially важно:

```text
unknown
ambiguous
inconsistent
contested
stale
unavailable
not-applicable
not-observed
not-reported
not-evaluated
```

Это не означает, что нужен один гигантский enum.

### Инвариант 12. Representation не имеет права усиливать смысл

Таблица, график, короткий тезис, tooltip, Excel-стиль, цвет, sorting, ranking, notification или AI-summary не должны превращать оценку в факт, recommendation в Decision, отсутствие evidence в ноль, unknown в normal, visual salience в priority, скрывать condition/exception, усиливать уверенность или менять Authority.

Это один из главных прямых мостов от `MADAR-supplements` к интерфейсу Strategy Box.

---

# 1. Исследовательская рамка

## 1.1. Базовая оговорка Strategy Box

В рамках этой работы:

> **всё текущее состояние Strategy Box, включая текущий код и уже проведённые исследования второй ветки, считается переходным.**

Следовательно:

- существующая архитектура не является ограничением;
- обратная совместимость не является целью;
- текущие названия сущностей не получают приоритет;
- существующие папки не считаются будущими semantic owners;
- текущий UX может быть полностью переосмыслен;
- текущие Research выводы используются как evidence и design input, а не как норматив.

Иначе исследование получилось бы сравнением текущего продукта с MADAR, а не проектированием целевого Strategy Box.

## 1.2. Иерархия использованных источников

### Актуальная архитектурная рамка MADAR

Использованы:

- `_mw/consolidation/STATE.md`;
- `_mw/consolidation/BASELINE.md`;
- `_mw/consolidation/ARCHITECTURE.md`;
- `_mw/consolidation/PROCESS.md`;
- `_mw/research/05_consolidation-input-research/README.md`;
- `_mw/consolidation/notes/MADAR_Consolidation_Sequence_and_Target_Directory_Architecture_2026-10-01.md`.

На момент исследования MADAR находится на Stage 3: формируются consolidation-input Research Results перед будущим полным Science consolidation и нормативным сведением.

Даже свежие выводы ниже трактуются как сильные Development Inputs, но не как уже принятый новый нормативный MADAR.

### Свежие consolidation-input исследования

Подробно использованы:

- A1 — Constitution and Boundaries of a General Engineering Method;
- A2 — Engineering Object Method: Boundaries, Identity, Composition and Evolution;
- A3 — Commissioned Work, Execution, Effects, Results, Acceptance and Closure;
- A4 — Participation Contracts, Authority and Adaptive Work Programs;
- A5 — Durable Work State, Artifact Ownership, Workspaces, Recovery and Handoff;
- A6 — Engineering Knowledge: Claims, Grounds, Uncertainty, Validity and Reliance;
- A7 — Reconciliative Knowledge Synthesis, Provenance, Lifecycle and Learning;
- A8 — Semantic Relations, Bidirectional Applicability and Governed Resolution;
- B1 — Goals, Values, Requirements, Decisions and Commitments;
- B2 — Meaning, Representation, Models, Measurement and Comparability;
- B3 — Structure, Composition, State, Time, Causality and Effects;
- B4 — Evidence, Assurance, Independence, Freshness and Bounded Reliance.

B5 (`Authority, участие и взаимодействие`) на момент наблюдаемого репозиторного среза ещё не присутствовал как завершённый durable Result. Его текущая исследовательская линия поэтому учитывается только как **provisional frontier**, прежде всего в части:

- `Actor ≠ Role ≠ Authority`;
- message ≠ Question/Decision/Evidence;
- delivery ≠ acceptance;
- participant state ≠ Work truth;
- distributed participants do not create distributed truth owners.

Будущие B6–B9 также ещё требуют окончательной Stage-3 консолидации: human/organization; change/continuity/recovery; risk/trust/protected interests; proportionality/method economics.

### Исторический корпус MADAR

Свежие A/B исследования уже выполнили огромную работу по сведению старого корпуса, но согласно самой процедуре MADAR их нельзя считать заменой оригиналам.

Дополнительно учитывалась поздняя системная линия исторических Research, прежде всего темы:

- semantic granularity;
- typed relations;
- universal scope / specialist federation;
- heterogeneous obligations and composition;
- semantic resolution and meaning preservation;
- bounded working context;
- resource-bounded deliberation;
- Activity Methods;
- composable Work / MADARAII;
- Dispatcher;
- Jester / challenge;
- machine-readable context;
- hierarchical semantic architecture;
- Roles / Skills / Work separation;
- Science / current knowledge / source accounting;
- rationale, provenance, historical intent;
- Work state and recovery;
- protective redundancy and distributed enforcement.

Здесь важен не номер старого исследования, а накопленная линия аргументации.

### Шесть `mandat-*` репозиториев

Исследованы integration-ready knowledge Products:

1. `mandat-analytics`;
2. `mandat-forecast`;
3. `mandat-programming`;
4. `mandat-communication`;
5. `mandat-evaluation-challenge`;
6. `mandat-strategy-decision`.

Их ценность для Strategy Box особенно высока, потому что они уже проверяют, как общая архитектура MADAR работает внутри конкретных профессиональных областей.

### `MADAR-supplements`

Использованы три ветви:

- `01-thinking`;
- `02-coding`;
- `03-communicating`.

Особенно важны финальные lossless-disposition исследования от 2 октября, где подробно исследованы hypothesis discovery, directional hypothesis support, conditional worlds, robust action, low-entropy interfaces, temporal priority, governed adaptive interfaces, communication as joint action, epistemic communication и representation/modality selection.

### Текущий Strategy Box

Использованы актуальные исследования `stratbox` core, `stratbox-windows`, AppDock как внешней управляющей платформы и закрытого окруженческого capability-контура только как доказательства необходимости нейтральной extension boundary.

Конкретное устройство закрытого окруженческого слоя **не переносится** в публичную целевую архитектуру и в настоящем документе не раскрывается.

---

# 2. MADAR нельзя копировать в структуру программы

Плохой вариант:

```text
stratbox/
  eom/
  ewm/
  ekm/
  concerns/
  activities/
  guidance/
  madaraii/
```

Такой дизайн внешне похож на MADAR, но почти наверняка создаст дублирование смыслов, инфраструктурный фреймворк ради фреймворка, лишние сущности, тяжёлые record schemas и смешение метода разработки и продукта.

MADAR задаёт:

```text
семантические различия
+
границы допустимых переходов
+
отношения владения
+
условия reliance
+
Work semantics
```

Strategy Box должен реализовать **только те программные сущности, у которых есть реальный consumer, lifecycle и failure class**.

> **MADAR для Strategy Box — не module taxonomy, а semantic constitution.**

---

# 3. Целевая природа Strategy Box

## 3.1. От data tool к epistemic workspace

Сегодня естественно описать Strategy Box как:

```text
источники
→ данные
→ расчёты
→ Excel
```

Целевая система должна описываться иначе:

```text
внешняя реальность / внешний authority
        ↓
source publications
        ↓
versioned source snapshots
        ↓
qualified observations
        ↓
defined constructs / measures
        ↓
claims and analytical questions
        ↓
evidence + assumptions + models + inference
        ↓
qualified knowledge results
        ↓
evaluation / challenge / reliance
        ↓
decision / strategy / action
        ↓
effects / new observations / learning
```

В каждом переходе важна семантика.

## 3.2. Четыре одновременно существующих порядка

Это analytical views, не обязательно физические подсистемы.

### Object order

Что существует или рассматривается: банк, группа, сектор, экономика, показатель, классификатор, publication, dataset, forecast, decision, strategy, Work, artifact.

### Epistemic order

Что Strategy Box знает или утверждает: observation, reported claim, analytical claim, hypothesis, model output, derived claim, forecast, evaluation result, contradiction, uncertainty, current synthesis.

### Work order

Что сейчас делается: Commission, Work, attempt, activity, operation, question, blocker, result, acceptance, closure, handoff, reopen.

### Authority/effect order

Что кто вправе устанавливать или изменять: source Authority, semantic owner, Decision Authority, publication Authority, execution permission, commitment, external effect, acceptance.

Большинство опасных архитектурных ошибок возникает, когда система превращает один порядок в другой автоматически.

---

# 4. Эпистемический позвоночник Strategy Box

## 4.1. Conceptual spine

```text
SOURCE
  │
  ▼
SOURCE SNAPSHOT / VINTAGE
  │
  ▼
OBSERVATION
  │
  ├─────────────► DEFINITION / CONSTRUCT / MEASURE
  │
  ▼
CLAIM
  │
  ├─────────────► ASSUMPTIONS / CONDITIONS
  ├─────────────► EVIDENCE / GROUNDS
  ├─────────────► MODEL / TRANSFORMATION
  ├─────────────► ALTERNATIVES / DEFEATERS
  │
  ▼
INFERENCE
  │
  ▼
QUALIFIED RESULT
  │
  ├─────────────► UNCERTAINTY
  ├─────────────► CURRENTNESS
  ├─────────────► APPLICABILITY
  └─────────────► RELIANCE BOUNDARY
  │
  ▼
DECISION INPUT
  │
  ▼
DECISION / COMMITMENT
  │
  ▼
ACTION / EFFECT
  │
  ▼
NEW OBSERVATION
  │
  ▼
RE-EVALUATION / LEARNING
```

Это не одна обязательная последовательность. Исходная публикация может сразу стать observation; Research может закончиться unresolved hypothesis; Forecast может выпускаться без Decision; Evaluation может остановить дальнейший reliance; Decision может опираться на несколько Results; Communication может быть отдельной projection поверх любого result.

## 4.2. Почему claim должен стать центральной смысловой единицей

A6 показывает: evidence нельзя оценивать «вообще».

Один и тот же источник поддерживает один claim, противоречит другому и ничего не говорит о третьем.

Поэтому Strategy Box не должен ограничиваться:

```text
file.source_quality = "high"
dataset.verified = True
```

Правильный вопрос:

> **что именно этот объект поддерживает, при каких условиях, через какой inferential bridge и для какого reliance?**

Это не означает обязательную отдельную database row для каждого предложения. Durable identity оправдана, когда есть реальная потребность в ссылке, независимом изменении, повторном использовании, assurance или отдельном contested lifecycle.

---

# 5. Семантика источника

## 5.1. SourceDescriptor и SourceSnapshot — разные смыслы

### SourceDescriptor

Стабильная идентичность источника или серии публикаций:

- authority;
- source family;
- declared construct;
- publication channel;
- expected cadence;
- expected schema family.

### SourceSnapshot

Конкретно полученное состояние:

- exact source;
- retrieval time;
- publication/release time;
- effective period;
- content identity/hash where useful;
- source version;
- schema version;
- storage location;
- retrieval result;
- known limitations.

Их нельзя смешивать.

## 5.2. Authority источника

Authority всегда scope-bound.

Официальный источник может быть authoritative относительно:

```text
«именно это значение опубликовано официально»
```

Но этот статус не устанавливает автоматически:

```text
«это безусловно истинная величина мира»
«эта величина сопоставима с показателем другого источника»
«это объясняет причину изменения»
«этот показатель пригоден для нашего решения»
```

Это одна из важнейших границ для банковской и макроэкономической аналитики.

---

# 6. Observation layer

## 6.1. Наблюдение должно иметь определённый смысл

Материально важные dimensions могут включать:

- Subject;
- construct/measure;
- value;
- unit;
- perimeter;
- period;
- temporal role;
- source/vintage;
- classification/version;
- reported/derived status;
- missingness semantics.

Не каждый объект требует всех metadata в отдельном record. Но если различие влияет на downstream inference, оно должно быть recoverable.

## 6.2. Raw и canonical

```text
Raw Source Snapshot
→ immutable source-bound representation

Canonical Observation
→ semantic normalization for an explicit internal construct

Derived Observation
→ value created by a declared transformation
```

При этом:

```text
canonical ≠ original
derived ≠ reported
normalized ≠ corrected truth
```

---

# 7. Meaning, constructs and measurements

## 7.1. Показатель должен иметь identity

Для серьёзной аналитики число без определения почти бессмысленно.

Strategy Box нужен слой определения `Measure / Construct`, который способен связывать:

- название;
- смысл;
- perimeter;
- formula/definition;
- unit;
- temporal semantics;
- source authority;
- classification basis;
- version/effective interval;
- comparable constructs;
- known breaks.

## 7.2. Банк и группа — не одно

Для банковского домена особенно важны:

```text
банк
банковская группа
финансовая группа
бренд
эмитент
юридическое лицо
консолидированная группа
```

То же относится к:

```text
IFRS
RAS
prudential reporting
statistical reporting
management view
normalized internal view
```

Система должна позволять явно строить bridge, а не считать одинаковые labels эквивалентными.

## 7.3. Comparability as relation

Вместо:

```text
series_a.comparable = True
```

нужна семантика:

```text
A comparable to B
FOR claim/use U
UNDER bridge X
WITH limitations L
```

Bridge может быть простым — unit/currency/date conversion — или сложным: IFRS ↔ RAS, changed regulatory form, classifier crosswalk, group reconstruction, methodological break.

---

# 8. Time и vintage как фундамент

Для Strategy Box один `timestamp` концептуально недостаточен.

В зависимости от объекта могут иметь значение:

- period described;
- event time;
- source publication time;
- information availability time;
- retrieval time;
- effective interval;
- registry version time;
- forecast origin;
- forecast horizon;
- decision time;
- observation time;
- artifact generation time.

Это особенно важно для прогнозов, historical backtests, regulatory data, revisions, financial reporting, event analysis, currentness и source monitoring.

---

# 9. Модель Knowledge

## 9.1. Current Knowledge ≠ Research History

A7 даёт прямую подсказку:

```text
Research History
≠
Current Maintained Knowledge
```

Research History сохраняет вопросы, hypotheses, sources, exploratory analysis, rejected alternatives, dead ends, uncertainty, historical reasoning basis.

Current Knowledge содержит текущее reconciled understanding, действующие definitions, qualified claims, material contradictions, limitations и links to sources/historical basis.

Если для понимания сегодняшнего вывода пользователь обязан перечитывать 30 старых исследований, current knowledge layer провален.

## 9.2. Синтез — отдельная эпистемическая операция

Суммаризация нескольких файлов ≠ synthesis.

Synthesis должен учитывать semantic overlap, shared lineage, duplicated evidence, contradictions, different populations/perimeters, source dependence, changed definitions, stronger/weaker claims, historical vs current applicability и unresolved residue.

## 9.3. Повторение не увеличивает evidence автоматически

Особенно важно в AI-assisted среде:

```text
одна исходная идея
→ Research A
→ summary A
→ report B
→ AI answer C
→ another report D
```

не создаёт пять независимых подтверждений.

Strategy Box должен сохранять lineage достаточно, чтобы derivative documents не считались независимыми evidence sources.

---

# 10. Claim model

## 10.1. Claim не должен иметь один «confidence status»

Epistemic qualification многомерна.

У material claim могут быть независимо:

- claim kind;
- modality;
- scope;
- conditions;
- support state;
- uncertainty;
- contestation;
- applicability;
- currentness;
- permitted reliance.

Нежелательная универсальная модель:

```text
confidence = 0.83
```

Число может быть оправдано в конкретной вероятностной модели. Оно не заменяет остальные distinctions.

## 10.2. Claim kinds

Полезные смысловые роли:

- reported;
- descriptive;
- comparative;
- explanatory;
- causal;
- predictive;
- conditional;
- counterfactual;
- evaluative;
- normative;
- recommendation;
- decision statement.

Это не обязательно закрытый enum. Главная цель — исключить silent promotion.

---

# 11. Hypotheses и unresolved worlds

`MADAR-supplements/01-thinking` особенно хорошо расширяет Strategy Box.

## 11.1. Hypothesis ≠ belief

Система должна позволять Hypothesis существовать без необходимости принять её, отклонить, дать вероятность или выбрать победителя.

## 11.2. Observation → Hypothesis Space

Полезный semantic operation:

```text
Observation
→ plausible hypothesis space
```

Выход — не diagnosis, не final explanation, не Decision.

## 11.3. Directional hypothesis support

Легитимна задача:

> построить максимально сильную честную аргументацию в пользу H.

Это не означает принятие H.

```text
search posture
≠
epistemic status
```

Очень важный принцип для AI-аналитики.

## 11.4. Conditional world

Strategy Box должен поддерживать:

```text
IF H
THEN consequences C
```

без скрытого:

```text
P(H) is high
H is true
```

Scenario analysis должен оставаться conditional world.

## 11.5. Robust action under unresolved hypotheses

Решение иногда возможно до разрешения истины:

```text
H1 / H2 / H3 remain unresolved
+
protected constraints
+
reversibility
+
regret
+
triggers
→ robust action / adaptive policy
```

Выбранная политика не подтверждает H1.

---

# 12. Analysis Activity в Strategy Box

`mandat-analytics` даёт почти готовый semantic contract.

## 12.1. Аналитический вопрос

До вычисления следует bind:

- question;
- Subject;
- perimeter;
- period;
- intended use;
- material reliance.

## 12.2. Primary Analytical Result + Analytical Basis

Сильная модель:

```text
Primary Analytical Result
+
Analytical Basis
```

Result — ответ потребителю.

Basis включает ровно столько, сколько необходимо для понимания и challenge:

- definitions;
- observations;
- transformations;
- assumptions;
- sources;
- alternatives;
- uncertainty;
- specialist dependencies;
- limitations.

Basis не обязан быть отдельным файлом.

## 12.3. Reusable analytical operations

### Comparison

```text
same label
≠
same meaning
```

### Normalization / reconciliation

Главный риск:

```text
adjusted view
→ silently becomes source truth
```

### Decomposition

Главный риск:

```text
contribution
→ narrated as cause
```

### Explanation

Главный риск:

```text
association / timing / plausible story
→ causal explanation
```

Эти distinctions стоит сделать фундаментальной частью core semantics.

---

# 13. Research / Inquiry

Strategy Box естественно должен поддерживать Research как отдельный bounded Work class.

Research возникает, когда:

```text
knowledge gap
+
existing knowledge insufficient for intended reliance
```

Research Result должен содержать exact question, investigated source universe, methodology at useful depth, findings, claims, alternatives, uncertainty, unresolved residue, reopen triggers и relation to current Knowledge.

Research completion ≠ Product/Knowledge admission.

---

# 14. Forecasting

## 14.1. Forecast ≠ Scenario ≠ Plan ≠ Target

Strategy Box должен различать:

```text
Forecast
Scenario
Stress Path
Baseline Projection
Counterfactual
Target
Plan
Strategy
Decision/Policy
Warning
Signpost
Model Output
```

Пользовательская поверхность может отображать их похоже, но смысл должен оставаться разным.

## 14.2. Forecast Candidate и Forecast Vintage

```text
Forecast Candidate
→ authorized issuance
→ Forecast Vintage
```

Если issuance имеет историческую или reliance ценность, Vintage должен быть immutable.

Обновление:

```text
не overwrite
а
successor / update / correction / withdrawal
```

## 14.3. Ex-ante information state

Исторический прогноз должен быть связан с тем, что было реально доступно на момент issuance:

- data vintages;
- reports;
- model version;
- model weights/training state where material;
- retrieval corpus;
- tools;
- external mutable sources.

Промпт «представь, что сегодня 2024» не создаёт historical information integrity.

## 14.4. Accuracy ≠ Forecasting correctness

Семантически корректный Forecast может не реализоваться.

Случайно точное число может быть получено через плохую forecasting procedure.

Strategy Box должен поддерживать оба вида оценки отдельно.

---

# 15. Evaluation and Challenge

## 15.1. Evaluation Result — bounded object

Evaluation должен отвечать:

```text
что оценивалось?
по какому критерию?
кто/что устанавливает criterion?
какое evidence?
какой conclusion?
какие limitations?
какая uncertainty?
для какого reliance?
насколько result current?
```

## 15.2. Evaluation cannot widen upstream reliance

Если Evaluation B использует Evaluation A, B не может просто расширить scope A.

Нужно либо сохранить его reliance envelope, либо отдельно построить bridge и additional evidence.

## 15.3. Challenge

Challenge — defeater-seeking operation.

```text
Challenge Finding
≠
Established Defect
≠
Decision
≠
automatic repair instruction
```

Strategy Box может поддерживать embedded challenge и standalone red-team/Jester Work.

---

# 16. Strategy and Decision

Название Strategy Box особенно логично довести до полноценного семантического слоя Strategy/Decision.

## 16.1. Knowledge, values and Authority

Нужно принципиально различать:

```text
evidence / analysis / forecast
values / preferences / objectives / constraints
recommendation
Authority
Decision
Commitment
Execution
Observed Outcome
```

Ни один слой не может молча захватывать следующий.

## 16.2. Decision

Decision:

> authorized resolution of a material open choice relative to bounded subject, information state and Authority context.

Возможные legitimate resolutions: act, do not act, wait, investigate, stage, delegate, adopt policy, preserve option, prohibit, terminate, supersede.

## 16.3. Decision lineage

Материальное решение должно связываться с information vintage, relevant analyses, forecasts, assumptions, criteria, Authority и unresolved uncertainty.

Последующий outcome не должен переписывать historical Decision.

## 16.4. Strategy

Strategy оправдана как persistent coordination object, когда решения materially coupled через scarce resources, path dependence, commitments, preserved options, adaptive actors, common theory of effect, sequencing и review/adaptation.

Нужно различать:

```text
Intended Strategy
Enacted Strategy
Realized Strategy
Retrospective Narrative
```

---

# 17. Work semantics вместо scenario-centric ядра

## 17.1. Текущий `Case` — полезный прототип, но не целевая единица

Целевая единица:

```text
Work
```

Work не равен одному scenario, actor session, task, thread, process или файлу.

Work определяется purpose, bounded result, scope, obligations, Authority и disposition.

## 17.2. Различие уровней

### Primitive / machine operation

Технически исполнимая capability:

```text
fetch
parse
normalize
calculate
export
write
compare
```

### Activity enactment

Смысловая трансформация:

```text
analysis
forecasting
evaluation
communication
research
```

### Work Definition

Повторяемый bounded job с самостоятельным Result contract.

### Work Instance

Конкретно commissioned работа.

### Program

Композиция Works с условиями transition, pause, branch, reopen и stop.

## 17.3. Что тогда происходит с scenarios

`Scenario` можно сохранить как UX-термин.

Но semantic owner должен быть яснее:

```text
Scenario UI
→ projection of Work Definition / Program
```

Сценарий не должен становиться универсальным владельцем domain meaning, Knowledge, Authority или currentness.

---

# 18. Work state

A3/A5 дают сильную целевую модель.

Work может требовать durable facts о:

- Commission;
- Work identity;
- attempts;
- input bindings;
- method/config;
- object baseline;
- participation;
- progress/checkpoint;
- actions/effects;
- questions/blockers;
- Result;
- verification;
- acceptance;
- residual obligations.

Work state **ссылается** на external/domain truth, а не присваивает его.

## 18.1. Нельзя иметь один универсальный status

Полезно различать при необходимости:

```text
commission status
execution status
effect knowledge
result disposition
dependency/readiness
participation
currency
retention/access
```

Например:

```text
execution = finished
effect = unknown
result = produced
acceptance = pending
```

— абсолютно нормальная комбинация.

---

# 19. Recovery и continuation

Цель recovery:

> восстановить достаточную позицию для безопасного продолжения, а не восстановить сознание прошлого исполнителя.

После перезапуска или смены исполнителя новый actor должен понять:

- что было commissioned;
- что уже произошло;
- что могло произойти;
- что подтверждено;
- какие Result существуют;
- какие Decisions действуют;
- что неизвестно;
- что запрещено повторять;
- какие действия разрешены;
- где нужен revalidation.

Это намного сильнее, чем последние N сообщений чата.

---

# 20. Участники и Authority

## 20.1. Actor ≠ Role ≠ Skill ≠ Authority

Strategy Box будущего не должен предполагать, что пользователь-владелец файла имеет Decision Authority, analyst имеет Authority принять recommendation, AI имеет Authority потому что умеет выполнить action, автор Result вправе accept, reviewer автоматически независим.

## 20.2. Participation contract

Участие лучше моделировать как bounded relation:

```text
actor
+
Work
+
allowed contribution
+
authority
+
scope/time
+
handoff/revocation
```

а не жёстким каталогом ролей.

## 20.3. Presence — projection, не owner

Online/offline status полезен UX.

Он не доказывает доступность, принятие ответственности, прочтение, понимание или Authority.

---
# 21. Questions, messages and interaction

Свежая линия B5 и `03-communicating` подсказывает важное различие:

```text
message
≠
Question
≠
Decision
≠
Finding
≠
Evidence
≠
Assignment
≠
Commitment
```

Message — carrier / interaction act.

Если в чате пользователь пишет «используем РСБУ» и это реально изменяет governing basis Work, такое решение не должно жить только как строка transcript. Должен существовать соответствующий semantic object или durable Work-state transition.

---

# 22. Communication as Joint Action

## 22.1. Delivery ≠ understanding

Отправленное сообщение не доказывает:

- receipt;
- understanding;
- agreement;
- acceptance;
- commitment;
- execution.

## 22.2. Dynamic interaction state

Для сложной работы могут быть material:

- current Question;
- shared assumptions;
- acknowledged constraints;
- unresolved disagreement;
- accepted Decision;
- pending handoff;
- repair needed.

Transcript — evidence/history взаимодействия. Он не обязан быть canonical interaction state.

## 22.3. Repair

Исправить сообщение недостаточно, если старый смысл уже повлиял на Decision, artifact, Work, another actor или publication.

Repair — state transition с impact propagation.

---

# 23. Representation and modality

## 23.1. Представление выбирается под consumer job

Одно и то же знание может быть лучше представлено как:

- prose;
- table;
- chart;
- timeline;
- causal graph;
- hierarchy;
- matrix;
- map;
- UI state;
- alert.

Выбор representation — функциональный инженерный выбор.

## 23.2. Fidelity и usability — разные вопросы

Representation может быть source-faithful, но practically unusable.

И наоборот: удобное представление может скрывать critical condition.

Целевая система должна поддерживать обе проверки.

## 23.3. Low-entropy interface

Минимализм интерфейса желателен, если он уменьшает cognitive load.

Но:

```text
minimal surface
≠
minimal semantics
```

UI может скрывать детали механики. Он не может скрыть distinction, если от неё зависит допустимое действие, Authority, safety, reversibility, recovery, uncertainty или meaning Result.

---

# 24. Temporal Priority

Интерфейс Strategy Box не должен путать:

```text
priority
urgency
salience
readiness
importance
risk
Authority
```

Красный цвет — representation. Он не создаёт priority.

Notification — channel. Она не создаёт obligation.

Порядок в списке — view. Он не должен становиться policy без явного основания.

---

# 25. Governed adaptive interfaces

Персонализация и adaptive UI полезны, но эпистемически опасны.

Типовая ошибка:

```text
system infers preference
→ changes available choices
→ observes user behavior under changed choices
→ interprets behavior as confirmation of original preference
```

Это feedback-induced evidence bias.

Поэтому adaptive UI должен:

- сохранять provenance adaptation;
- различать inferred vs expressed preference;
- иметь protected semantics;
- иметь user override;
- не менять Authority;
- не скрывать available critical actions;
- допускать reset/recovery;
- не превращать behaviour after intervention в независимое validation evidence.

---

# 26. Artifacts

## 26.1. Artifact role

Artifact — durable representation или materialized output.

Типы могут включать dataset, workbook, chart, report, snapshot, package, model output, publication.

Но `kind` по расширению файла недостаточен.

## 26.2. Artifact provenance

Для material artifacts полезно восстанавливать:

```text
Artifact
← Result
← Transformation / Work
← Inputs
← SourceSnapshots / Knowledge
```

И в обратную сторону:

```text
SourceSnapshot
→ dependent observations
→ derived Results
→ dependent Artifacts
```

Это создаёт основу для impact analysis.

## 26.3. Artifact currentness

Старый Excel не должен физически исчезать при новом источнике.

Вместо этого его relation может измениться:

```text
historical artifact
currentness = stale / superseded / needs revalidation
```

если это materially важно.

---

# 27. Логи и observability

Недавние исследования observability Strategy Box хорошо стыкуются с MADAR, если провести границы.

## 27.1. Три вида observability

### Runtime observability

- process state;
- resource state;
- exceptions;
- worker/job;
- host/node;
- logs.

### Work observability

- Work status;
- current stage;
- blocked;
- waiting;
- last established Result;
- unknown effect;
- pending acceptance.

### Epistemic observability

- what is claimed;
- why;
- evidence;
- uncertainty;
- contradicting evidence;
- currentness;
- reliance limit.

Ни один из этих уровней не заменяет другой.

## 27.2. Ошибка как evidence, а не truth owner

Exception/log entry сообщает:

```text
software observed / reported failure X
```

Это может быть сильным evidence для operational diagnosis.

Но единичный stack trace не является автоматически root cause.

---

# 28. Freshness и dependency impact

Это одна из наиболее ценных возможностей будущего Strategy Box.

## 28.1. Источник обновился

Не следует автоматически:

```text
overwrite old result
```

Целевая последовательность:

```text
new SourceSnapshot
→ compare semantic/source identity
→ detect changed inputs
→ traverse material dependencies
→ qualify affected Results
→ current / possibly stale / needs revalidation
→ propose bounded successor Work
```

## 28.2. Registry update

Если обновился банк registry, ОКВЭД, geography, accounting definition или form schema, Strategy Box должен понимать, какие результаты реально зависят от этого asset.

Не нужно полностью пересчитывать всё только потому, что изменился один справочник.

Это A7/A8/B4 в программной форме.

---

# 29. Registries как versioned semantic assets

Сегодня registry легко воспринимать как bundled lookup table.

Целевая модель сильнее.

Registry asset должен иметь, где material:

- identity;
- source authority;
- source vintage;
- effective interval;
- schema/version;
- transformation version;
- lineage;
- currentness.

Registry update — semantic change event, а не просто replacement файла.

---

# 30. SORS как ранний прототип EKM

Текущая SORS-подсистема уже намного ближе к целевой эпистемической архитектуре, чем обычные ETL-домены.

Она различает:

- published observations;
- latent quantities;
- constraints;
- evidence tiers;
- provenance;
- inference;
- optimization;
- conflicts;
- audit grids.

Это нужно воспринимать не как шаблон сложности для каждого domain, а как доказательство принципа:

> **derived value должен сохранять способ, степень и границы своего установления.**

## 30.1. Главное future requirement

В UI и артефактах нельзя позволять:

```text
restored value
→ looks indistinguishable from official reported value
```

Минимально должно быть recoverable:

- source status;
- restoration method;
- evidence tier;
- uncertainty/bounds where relevant;
- dependencies;
- model/config identity;
- currentness.

---

# 31. Mapping текущих доменов `stratbox` в target semantics

## 31.1. `cbr_file_collector`

Текущая роль — raw preservation.

Целевая:

```text
SourceDescriptor
→ SourceFetch
→ SourceSnapshot
→ source validation
→ provenance/currentness
```

Collector не обязан знать analytical meaning всех downstream datasets.

## 31.2. `cbr_forms`

```text
physical source
→ parsed physical representation
→ semantic observations
→ definitions / Indicator identity
→ validation
→ canonical observations
→ views/artifacts
```

Excel остаётся projection.

## 31.3. `cbr_industries`

Подходит как Analysis domain:

```text
sources
→ observations
→ semantic normalization
→ derived analytical transformation
→ Analytical Result
→ views
```

Geography и classification должны иметь versioned semantic ownership.

## 31.4. `escrow`

Сильный кандидат для первого полного epistemic pipeline:

```text
official monthly publications
→ immutable snapshots
→ observations
→ series identity
→ historical reconciliation
→ current view
→ workbook projection
```

## 31.5. `frg`

Сегодня это в основном file operational stage.

Целевая роль:

```text
source/file work preparation
```

Пока parser/semantic layer отсутствует, FRG не должен изображать knowledge domain.

## 31.6. Registries

Переход:

```text
bundled resource
→ versioned semantic reference asset
```

---

# 32. Целевая архитектура `stratbox`

Ниже — **candidate software architecture**, а не механическое отражение MADAR.

```text
stratbox
│
├── base/
│   ├── storage
│   ├── network
│   ├── runtime contracts
│   ├── diagnostics
│   └── extension protocols
│
├── semantics/
│   ├── identity
│   ├── time
│   ├── units
│   ├── definitions
│   ├── classifications
│   └── relations
│
├── sources/
│   ├── descriptors
│   ├── snapshots
│   ├── fetching
│   ├── validation
│   └── source provenance
│
├── observations/
│   ├── contracts
│   ├── normalization
│   ├── missingness
│   └── lineage
│
├── knowledge/
│   ├── claims
│   ├── grounds
│   ├── assumptions
│   ├── hypotheses
│   ├── uncertainty
│   ├── defeaters
│   ├── currentness
│   └── reliance
│
├── activities/
│   ├── research
│   ├── analysis
│   ├── forecasting
│   ├── evaluation
│   └── domain-specific transformations
│
├── registries/
│   └── versioned reference assets
│
├── domains/
│   └── banking / macro / CBR ...
│
├── artifacts/
│   ├── projections
│   ├── lineage
│   └── exporters
│
└── operations/
    ├── descriptors
    └── registry
```

Это направление, а не обязательное точное дерево.

Если `knowledge/claims` не имеет достаточного реального lifecycle, его можно реализовать легче. Главный критерий — семантическое владение, а не симметрия каталогов.

---

# 33. Чего `stratbox` не должен владеть

Core не должен становиться владельцем:

- desktop state;
- UI navigation;
- window preferences;
- AppDock node lifecycle;
- user presence;
- remote transport;
- final Decision Authority;
- organization-specific permissions;
- user identity;
- communication acceptance;
- arbitrary workflow orchestration.

Он должен предоставлять нейтральные contracts, semantic results и domain operations.

---

# 34. Закрытый окруженческий capability layer

Публичный core должен знать только нейтральные extension contracts.

Окруженческие реализации могут предоставлять storage, authentication/secrets, network policy, presentation presets и другие environment capabilities.

Но публичный Strategy Box не должен знать конкретное устройство такого слоя.

С точки зрения MADAR:

```text
capability
≠
Authority
≠
domain truth
```

То, что runtime умеет что-то сделать, не означает, что Work разрешает это делать.

---

# 35. Целевая архитектура `stratbox-windows`

## 35.1. Windows — presentation/application surface, не semantic owner

Главное правило:

```text
UI displays / queries / requests transitions
but does not own domain truth
```

## 35.2. Platform-neutral shared application semantics

С учётом будущего Android особенно важно сохранить универсальными:

- Work model;
- Program model;
- Question/Decision interaction models;
- Result projection;
- knowledge projection;
- artifact projection;
- evaluation/reliance views;
- operation/work parameter semantics;
- navigation semantics;
- currentness/status semantics;
- authority/action availability;
- notifications as projections;
- AppDock client contracts.

Qt должен остаться adapter/rendering layer.

---

# 36. Как должна измениться IA пользовательской поверхности

Сегодняшние:

- Проводник;
- Сценарии;
- Каскады;
- Фоновые;
- Участники;
- Поручения

полезны как переходный прототип, но они преимущественно execution-centric.

В будущем логичнее проектировать IA вокруг смыслов.

Возможный candidate:

```text
Работа
Данные
Знания
Решения
Артефакты
Система
```

или другой UX, но semantic capabilities должны включать эти области.

Этот список не следует считать final navigation.

---

# 37. Knowledge Inspector

Один из наиболее сильных потенциальных UX Strategy Box.

Для material Result пользователь должен иметь возможность быстро ответить:

### Что это?

- observation?
- reported value?
- derived metric?
- analytical claim?
- forecast?
- evaluation?
- decision?

### О чём это?

- Subject;
- perimeter;
- period;
- definition.

### Откуда?

- source;
- snapshot;
- vintage.

### Как получено?

- transformation;
- model;
- assumptions.

### Почему этому можно доверять?

- grounds;
- relevant evidence;
- validation/evaluation.

### Что неизвестно?

- uncertainty;
- alternatives;
- contradictions.

### Актуально ли сейчас?

- currentness;
- affected dependencies.

### Для чего допустимо использовать?

- reliance boundary.

Это гораздо важнее очередной технической вкладки `metadata`.

---

# 38. Case Inspector → Work Inspector

Текущий case inspector естественно может эволюционировать в Work Inspector:

- Commission;
- current Work state;
- current question;
- inputs;
- Results;
- evidence;
- Decisions;
- participants;
- unresolved effects;
- artifacts;
- logs;
- residual obligations;
- reopen triggers.

Logs и artifacts становятся вкладками Work, но не самой Work.

---

# 39. Data Explorer → Semantic Data Explorer

Файловый проводник полезен, но аналитическая система должна уметь показывать:

- source;
- dataset;
- observation series;
- definition;
- vintage;
- transformations;
- dependent Results.

Путь к файлу — один из locators, а не semantic identity.

---

# 40. Background processes как epistemic automation

Вместо списка pseudo-daemons:

```text
monitor source
refresh cache
check workspace
```

целевой background layer может делать:

```text
observe external change
→ create new snapshot
→ detect semantic delta
→ identify impacted knowledge/results
→ classify currentness
→ create proposed successor/revalidation Work
→ notify accountable user
```

Это превращает background processing в knowledge-maintenance систему.

---

# 41. Monitoring vs Strategy adaptation

Наблюдение само по себе не делает Strategy adaptive.

Чтобы monitoring был частью adaptive Strategy:

```text
signal
→ interpreted signpost
→ reaches accountable owner
→ authorized policy / trigger
→ possible Decision/commitment change
```

Без этой цепочки monitoring — просто observation.

---

# 42. Settings через MADAR

Настройки особенно хорошо показывают разницу между presentation и semantics.

## 42.1. Presentation preference

Например:

- theme;
- accent;
- density;
- font;
- default panel;
- animation.

Не меняет epistemic meaning.

## 42.2. Workspace default

Например:

- default output path;
- default representation;
- default export format.

Может влиять на realization, но не должен молча менять analytic claim.

## 42.3. Semantic parameter

Например:

- perimeter;
- reporting standard;
- currency basis;
- classifier version;
- selected transformation;
- treatment of missing values.

Это уже **не обычная настройка UI**.

Если значение меняет Result meaning, оно должно быть частью Work/Result provenance.

## 42.4. Authority policy

Например:

- кто может publish;
- кто может approve;
- кто может run destructive Work.

Это отдельный access/Authority concern. Его нельзя прятать среди personal settings.

---

# 43. Communication and publishing

## 43.1. Publication как projection

Отчёт или презентация:

```text
Knowledge / Result
→ Communication transformation
→ Publication Artifact
```

Publication не становится owner upstream meaning.

## 43.2. Protected properties

При публикации могут быть material:

- claim strength;
- uncertainty;
- source;
- period;
- scope;
- conditions;
- causal status;
- recommendation vs Decision;
- currentness;
- assurance status.

## 43.3. File authorship

Авторство файла полезно как provenance.

Но нужно различать:

- creator;
- analyst;
- owner of source meaning;
- issuer;
- approver;
- publisher.

Поле `author` не должно заменять эти роли.

---

# 44. Excel

Excel должен стать projection engine над semantics, а не терминальной точкой pipeline.

Пользователь может выбрать style, number format, layout, chart palette.

Но workbook metadata желательно уметь связывать с:

- Work;
- Result;
- source vintages;
- generated-at;
- core version;
- semantic config;
- provenance manifest.

Для material reports это позволяет восстановить basis.

---

# 45. AI в Strategy Box

AI особенно опасен там, где fluent output скрывает status transitions.

Правильная модель:

```text
AI actor
→ receives bounded context
→ can query semantic owners
→ proposes Work / Result / Claim / Action
→ cannot self-grant Authority
→ cannot self-accept Result
→ leaves provenance
```

## 45.1. AI context

Context должен быть:

```text
operation-relative
+
bounded
+
re-enterable
```

Не весь workspace.

Но omission-safe: governing constraints, material unknowns, current owner, relevant decisions и reliance limitations не должны исчезать ради экономии токенов.

## 45.2. Private chain of thought не нужен

Strategy Box должен сохранять claims, premises, evidence, decisions, public rationale, alternatives и limitations.

Ему не нужно хранить скрытую внутреннюю reasoning trace модели.

---

# 46. AppDock boundary

AppDock естественно владеет:

- installation;
- managed environment;
- node;
- launch;
- host;
- remote execution transport;
- runtime health;
- platform capabilities;
- platform recovery;
- application lifecycle.

Strategy Box владеет:

- domain meaning;
- Work semantics;
- Knowledge;
- analytical Results;
- Forecasts;
- Evaluation;
- Decision-support semantics;
- Strategy Box currentness and provenance.

## 46.1. Критическая граница

```text
AppDock execution success
≠
Strategy Box Work success
```

И наоборот:

```text
Strategy Box analytical Result established
≠
AppDock action/remote effect necessarily completed
```

Нужна явная boundary contract.

---

# 47. Machine-readable слой — позже смысла

Не следует начинать с JSON schema, graph database, universal metadata, ontology или hundreds of status fields.

Правильный порядок:

```text
manual semantic distinctions
→ real user cases
→ stabilized owners
→ stable relations
→ only then schemas/indexes/automation
```

Strategy Box может использовать dataclasses/Pydantic/JSON раньше для engineering convenience. Но machine shape не должен определять meaning задним числом.

---

# 48. Что не следует превращать в универсальные сущности

Даже если concepts полезны, не обязательно создавать класс/таблицу для каждого:

- Claim;
- Ground;
- Warrant;
- Defeater;
- Hypothesis;
- Question;
- Assumption;
- Relation;
- Acceptance;
- Currentness;
- Reliance.

Критерий materialization:

```text
есть ли независимая ссылка?
есть ли отдельный lifecycle?
нужно ли отдельно менять?
нужно ли отдельно переиспользовать?
нужно ли assurance?
есть ли отдельный consumer?
```

Если нет — значение может оставаться частью typed Result.

---

# 49. Чего нельзя делать

## File-centric truth

Плохо:

```text
latest.xlsx = truth
```

## Latest wins

Новая версия не автоматически правильнее, сопоставима, заменяет историю или применима ко всем старым Result.

## Green means true

Зелёный status может означать execution succeeded, validation passed, accepted, current или published. Эти meanings нельзя сливать.

## One confidence score

Особенно вреден для аналитических систем.

## One universal status enum

`DONE` не говорит: effect confirmed? Result accepted? artifact persisted? currentness okay? residual obligation exists?

## One provenance field

`source = cbr.ru` недостаточно для reproducibility.

## One timestamp

Недостаточно для publication/vintage/ex-ante/currentness.

## One “official” flag

Officiality itself is scope-bound Authority.

## Auto-promote Research to Knowledge

Research Result остаётся Research Result до reconciliation/admission.

## Auto-promote Evaluation to Decision

Evaluation informs Authority. Она её не заменяет.

## Auto-recompute and overwrite

История и vintages должны сохраняться.

## UI owns state

UI projection не должна становиться semantic source.

---

# 50. Роли шести `mandat-*` в целевом Strategy Box

| Repository | Главный вклад в Strategy Box |
|---|---|
| `mandat-analytics` | Analysis Result/Basis, semantic comparability, normalization, decomposition vs explanation, Research/Inquiry |
| `mandat-forecast` | Forecast semantics, vintages, ex-ante integrity, uncertainty honesty, forecast/plan/scenario firewalls |
| `mandat-programming` | obligation/mechanism/evidence separation, implementation/runtime identity, reproducibility, realization fidelity |
| `mandat-communication` | recipient-facing fidelity, communicative force, projection/currentness, delivery vs understanding/effect |
| `mandat-evaluation-challenge` | bounded Evaluation Result, criterion/evidence/reliance, challenge/defeaters, assurance ceilings |
| `mandat-strategy-decision` | goals/values/Authority, Decision/commitment/execution distinction, Strategy lineage, robust/adaptive choice |

Ни один из этих Product не надо копировать целиком в Strategy Box.

Их роль — дать semantic contracts соответствующим capabilities.

---
# 51. Роль `MADAR-supplements`

## 51.1. `01-thinking`

Особенно полезно для:

- hypothesis-space construction;
- hypothesis support;
- conditional reasoning;
- robust action;
- preserving UNKNOWN;
- decision without counterfeit certainty.

Главные смысловые ограничения:

```text
candidate hypothesis ≠ diagnosis
pro-H construction ≠ accepted belief
conditional consequence ≠ probability
robust policy ≠ truth of one world
```

Именно эти distinction classes стоит защищать в исследовательских и сценарных функциях Strategy Box.

## 51.2. `02-coding`

Особенно полезно для:

- interface semantics;
- UI as projection;
- minimal/low-entropy interfaces;
- temporal priority;
- adaptive interface governance;
- state/effect visibility.

Его главный вывод для Strategy Box:

> интерфейс нельзя проектировать как отдельную параллельную семантическую вертикаль. Он должен отображать EOM/EWM/EKM/Authority/Work distinctions, а не создавать свои версии truth/state/priority.

## 51.3. `03-communicating`

Особенно полезно для:

- epistemic communication;
- representation selection;
- joint action;
- grounding;
- repair;
- currentness;
- authored transformation fidelity.

Ключевая формула:

```text
owned meaning
→ protected epistemic projection
→ task-fit representation
→ realization
→ delivery
→ evidence of understanding/acceptance
→ commitment where authorized
→ downstream action
→ repair / re-grounding if state changes
```

Эта цепочка крайне полезна для будущих чатов, отчётов, AI-summary и multi-user Strategy Box.

---

# 52. Core semantic relations Strategy Box должен уметь выражать

Не обязательно одним graph database.

Но meaning должен быть способен различить relation families вроде:

```text
derived-from
supports
contradicts
qualifies
specializes
normalizes
compares-to
depends-on
uses-definition
uses-vintage
supersedes
corrects
evaluates
challenges
accepted-for
produced-by
issued-by
represented-by
communicated-as
informs
decided-by
committed-by
observed-after
claimed-caused
```

Relation type определяет допустимые inference.

Нельзя считать все ссылки транзитивными.

Например:

```text
A derived-from B
B derived-from C
```

может давать lineage до C, но не гарантирует semantic equivalence A и C.

А:

```text
Evidence E supports Claim C1
```

ничего не говорит автоматически о Claim C2.

---

# 53. Currentness engine

Целевая currentness — не Boolean.

Для material Result система должна уметь устанавливать:

- historical identity intact;
- source dependencies;
- affected dependency changed?;
- semantic change?;
- still applicable?;
- requires revalidation?;
- superseded?;
- contradicted?;
- unchanged support?

Это может быть calculated projection, а не manually stored flag.

Особенно важно не смешивать:

```text
newer
current
applicable
authoritative
better
```

---

# 54. Knowledge graph без графовой религии

Strategy Box почти неизбежно получит graph-like semantics.

Преимущество graph view:

- lineage;
- impact;
- evidence;
- source/result navigation;
- contradiction;
- currentness.

Но canonical semantic owner может оставаться:

- typed domain objects;
- relational database;
- files;
- generated indexes.

Главное — relation meaning.

Наличие Neo4j, RDF или graph database не делает систему эпистемически корректной.

---

# 55. Epistemic UX

Целевой UX должен помогать человеку различать:

```text
что известно
что сообщено источником
что выведено
что предположено
что спорно
что устарело
что неизвестно
что принято
что разрешено
```

Это важнее, чем показывать пользователю больше технических metadata.

## 55.1. Визуальная осторожность

Не следует превращать uncertainty в декоративные badges без смысла.

Например:

```text
Verified
```

слишком неопределённо.

Нужно иметь возможность ответить:

```text
что именно verified?
по какому criterion?
по какому evidence?
для какого reliance?
когда?
```

---

# 56. Работа с ошибками

Error model должен сохранять semantic difference:

```text
not found
permission denied
unavailable
invalid data
unsupported
partial failure
unknown effect
validation failed
inconsistent
stale
```

Ошибка транспорта не должна выглядеть как:

```text
[] / zero / False
```

Это технический вопрос, но напрямую эпистемический: система иначе сообщает ложное состояние знания.

---

# 57. Partial results

Analysis/Research/Work может завершаться:

- complete;
- partial but valid;
- inconclusive;
- blocked;
- no admissible result;
- unknown effect;
- transferred;
- abandoned with residual obligation.

Partial Result должен явно показывать свою boundary.

Нельзя заставлять каждую Work либо быть `SUCCESS`, либо `FAILED`.

---

# 58. Acceptance

Acceptance — qualified relation:

```text
Actor/Authority
accepts
exact Result/version
for use U
under criteria C
under conditions K
```

Acceptance не устанавливает:

- world truth;
- implementation effect;
- permanent validity;
- universal reuse.

Accepted Result может позднее стать stale без того, чтобы исторический акт acceptance перестал существовать.

---

# 59. Provenance

## 59.1. Provenance нельзя сводить к source URL

Для material Result может быть нужна цепочка:

```text
source snapshot
→ parser version
→ semantic mapping
→ registry versions
→ transformation/model
→ parameters
→ result
→ artifact
```

## 59.2. Provenance != validity

Идеальный lineage может воспроизводить ошибку идеально.

Поэтому:

```text
provenance
+
validity
```

разные concerns.

---

# 60. Reproducibility

Для аналитики полезно сохранять reproducibility manifest:

- core version;
- operation/work identity;
- source snapshot IDs/hashes;
- registry versions;
- parameters;
- model version;
- environment identity where materially relevant;
- resulting semantic Result identity;
- artifact identity.

Но:

```text
reproducibility ≠ correctness
```

Повторяемо получить неправильный ответ возможно очень надёжно.

---

# 61. Banking-specific implications

## 61.1. IFRS vs RAS

Система должна считать bridge explicit.

Нельзя:

```text
одинаковый русский label
→ comparable
```

## 61.2. Bank vs Group

Обязательна perimeter semantics.

## 61.3. Published vs normalized

В интерфейсе и Excel:

```text
reported
normalized
derived
estimated
restored
```

должны оставаться recoverable.

## 61.4. Revisions

Период может иметь:

- initial publication;
- revised publication;
- reconstructed internal view.

Historical analysis должен быть способен использовать exact vintage.

---

# 62. Macro-specific implications

Для макроэкономических рядов особенно важны:

- seasonality;
- revisions;
- real-time vintage;
- classification changes;
- price/current vs constant terms;
- index base;
- chain linking;
- geography;
- observation vs estimate;
- nowcast vs forecast.

Strategy Box target должен иметь достаточно semantics, чтобы эти differences не жили только в комментариях к Excel.

---

# 63. Current Science / Knowledge layer в приложении

Не нужно копировать MADAR `science/` как каталог.

Но продукту нужен эквивалент функции:

> maintained reconciled knowledge, независимое от historical research-папки.

Например для банка:

```text
Current Bank Knowledge
```

может объединять:

- current financial state;
- current definitions;
- current analytical claims;
- forecast objects;
- unresolved issues;
- current decision context;
- source/currentness map.

Это намного сильнее «папки с последними Excel».

---

# 64. Knowledge objects и files

Физические файлы нужны.

Но primary lookup future Strategy Box должен отвечать:

```text
найди последний текущий Forecast по объекту X
найди вывод о NIM банка
покажи основание
покажи использованный source vintage
что изменилось?
какие claims устарели?
```

а не только:

```text
в какой папке лежит xlsx?
```

---

# 65. Workspaces

Workspace — access/organization environment.

Он не становится owner:

- Product truth;
- Knowledge;
- Authority;
- source truth.

Он может содержать projections этих объектов.

---

# 66. Data root

Data root в AppDock/Strategy Box — physical binding.

Semantically:

```text
storage location
≠
dataset identity
```

Перемещение workspace не должно менять semantic identity материала.

---

# 67. Universal client model для Windows/Android

Из `stratbox-windows` будущий `stratbox-android` должен наследовать прежде всего **semantic projection layer**, а не копию desktop widget architecture.

Shared:

- WorkProjection;
- KnowledgeProjection;
- ClaimProjection;
- ResultProjection;
- ArtifactProjection;
- DecisionProjection;
- SourceProjection;
- CurrentnessProjection;
- ActionAvailability;
- notifications/attention semantics.

Platform-specific:

- widgets;
- layouts;
- file picker;
- OS share;
- desktop explorer;
- mobile notification;
- Android storage integration.

---

# 68. Attention и mobile

Mobile особенно усиливает Temporal Priority issue.

Push notification должна появляться потому, что:

```text
material event
+
actionable or time-relevant
+
recipient has relevant responsibility
+
appropriate channel
```

а не потому что backend умеет посылать push.

---

# 69. AppDock remote execution

Для remote node:

```text
Strategy Box Work request
→ AppDock execution capability
→ runtime acknowledgement
→ effect/result evidence
→ Strategy Box Work state
```

Нельзя:

```text
HTTP 200 / process exit 0
→ domain Work accepted
```

---

# 70. Destructive actions

MADAR хорошо поддерживает pattern:

```text
plan
→ inspect
→ authorize
→ execute
→ observe/reconcile effect
```

Особенно для:

- delete;
- overwrite;
- move;
- publish;
- external write;
- commitment;
- bulk refresh.

Current FRG plan/apply — хороший ранний пример.

---

# 71. Changes и impact

B7 ещё требует полного fresh consolidation, но target already clear enough.

Change object should trigger:

```text
what semantics changed?
which Results depended on it?
which reliance remains valid?
which Work must re-open?
```

Не каждый change требует full recomputation.

---

# 72. Risk / trust / protected interests

B8 ещё впереди, поэтому Strategy Box не стоит сейчас изобретать универсальный Risk Engine.

Достаточно architecture-ready boundaries:

- protected operations;
- data sensitivity;
- publication Authority;
- external-effect controls;
- specialist regulatory/legal bindings;
- high-consequence assurance depth.

---

# 73. Proportionality

B9 станет особенно важным для продукта.

Цель — не maximum metadata.

Цель:

```text
sufficient epistemic assurance
at acceptable end-to-end cost
```

Для trivial calculation не нужен knowledge graph.

Для major strategic forecast может быть нужен exact vintage, challenge, Evaluation и Decision record.

---

# 74. Что должно быть лёгким

MADAR-compatible Strategy Box не должен быть тяжёлым пользователю.

Большая часть semantics может вычисляться/подставляться автоматически.

Пользователь должен вводить только то, что:

- неизвестно системе;
- materially affects meaning;
- требует human Authority;
- требует interpretation.

Это принципиально: эпистемическая строгость не должна означать бюрократию.

---

# 75. Progressive disclosure

UI должен показывать:

```text
короткий Result
```

с возможностью раскрыть:

```text
Basis
Sources
Uncertainty
Provenance
Relations
Evaluation
```

Это лучший способ совместить low entropy и deep inspectability.

---

# 76. Semantic defaults

Defaults допустимы, если:

- scope известен;
- они видимы;
- versioned where material;
- override intentional;
- downstream Result сохраняет применённый default.

Нельзя, чтобы default незаметно становился factual assertion.

---

# 77. Derived views

Generated index, dashboard, chart, pivot, search result, chat summary:

```text
derived projection
```

По возможности rebuildable.

Если derived view содержит новый curatorial judgment, эта часть уже требует owner.

---

# 78. Search

Поиск в Strategy Box должен различать:

- lexical match;
- semantic relevance;
- current owner;
- historical occurrence;
- source evidence;
- derived repetition.

Search ranking не должен превращаться в evidence ranking.

---

# 79. Source monitoring

Мониторинг publication может стать first-class Work:

```text
Check Source Change
```

Result:

- no new snapshot;
- new snapshot no material semantic change;
- material change;
- source unavailable;
- schema changed;
- requires review.

Это сильнее простого `download latest`.

---

# 80. Research closure

Research может закрыться, когда:

- declared question sufficiently answered;
- source/search boundary explicit;
- residual unknown explicit;
- downstream disposition clear;
- further effort unlikely materially change answer without new evidence.

`Ничего больше не нашёл` не является универсальной completeness proof.

---

# 81. Jester / red-team для Strategy Box

Jester полезен не как постоянная роль, а как challenge mode.

Для Strategy Box особенно полезны provocations:

- где derived показан как reported?
- где UI color усиливает claim?
- где stale result выглядит current?
- где same label hides different perimeter?
- где retry может duplicate external effect?
- где source agreement has shared lineage?
- где acceptance confused with validation?
- где forecast condition confused with probability?
- где normalized metric became source truth?
- где report omitted decisive caveat?
- где exact computation hides invalid construct?
- где current dataset was rebuilt with later knowledge for an ex-ante task?
- где participant message silently changed Authority?
- где background refresh silently overwrote a historical Result?

---

# 82. Архитектурная карта MADAR → Strategy Box

| MADAR owner | Strategy Box manifestation |
|---|---|
| Constitution | system invariants: no semantic laundering, bounded Authority, explicit owners, qualified effects |
| EOM | Subject identity, boundaries, state, lifecycle, dataset/model/work objects |
| EWM | Work, Commission, Result, acceptance, effects, closure, durable state |
| EKM | Claim, grounds, inference, uncertainty, defeaters, reliance, knowledge lifecycle |
| Meaning/representation concerns | raw/canonical/derived, artifacts, UI projections, exports |
| Measurement/models | indicators, construct definitions, model/run/output, comparability |
| Structure/state/time/effects | versioning, composition, transitions, vintages, remote effects |
| Evidence/assurance | validation, Evaluation, challenge, freshness, whole-result claims |
| Goals/values/decisions | analysis-to-decision boundary, Decision/Strategy objects |
| Authority/participation | actors, permissions, acceptance, interaction |
| Human factors | progressive disclosure, attention, operability, realistic control |
| Change/recovery | impact, revalidation, resume, stale state |
| Risk/protected interests | high-consequence controls, specialist boundaries |
| Proportionality | metadata/assurance depth by consequence |
| Activities | Research, Analysis, Forecasting, Evaluation, Communication, Decision support, Operation |
| Guidance | domain techniques and UX/application heuristics |
| Packs | banking/macro/company/reporting specialized deltas |
| Skills | professional compositions, not permissions |
| MADARAII | reusable bounded Work definitions |
| Dispatcher | choose relevant Work/Activity/Pack/context |
| Automation | execute stabilized semantic contracts |

---

# 83. Target user journeys

## 83.1. «Сравни два банка»

```text
Work commissioned
→ resolve bank/group identities
→ resolve measures
→ resolve perimeter/period
→ bind source vintages
→ compare via explicit bridges
→ Analytical Result + Basis
→ artifact projection
```

If IFRS/RAS mismatch is material:

```text
Result cannot silently compare
→ bridge / limitation / UNKNOWN
```

## 83.2. «Почему вырос показатель?»

```text
observation
→ decomposition
→ candidate explanations
→ evidence discrimination
→ bounded explanation
```

Decomposition alone cannot answer causal “why”.

## 83.3. «Что будет дальше?»

System first classifies requested future form:

- Forecast?
- Scenario?
- Stress?
- conditional consequence?
- Target?

Then applies correct semantics.

## 83.4. «Какое решение принять?»

```text
Decision question
→ values/objectives/constraints
→ alternatives
→ Analysis/Forecast/Evaluation
→ unresolved uncertainty
→ recommendation
→ Authority
→ Decision
→ commitment
→ signposts/review
```

The system may stop at recommendation if Authority is outside Strategy Box.

## 83.5. «Обнови данные»

```text
check sources
→ new snapshots
→ semantic delta
→ impacted results
→ refresh/revalidation plan
→ execute allowed subset
→ preserve history
```

Это намного богаче, чем «download latest and overwrite».

---

# 84. Что сохранить из текущего продукта

Хотя всё считается переходным, несколько patterns стоит сохранить conceptually.

## 84.1. Core / surface separation

Сильное решение.

## 84.2. FileStore/runtime abstractions

Сильная boundary idea, при условии строгой error semantics.

## 84.3. Raw preservation

Критически важно.

## 84.4. Typed Request/Result

Нужно расширять.

## 84.5. SORS provenance/evidence

Очень сильный local precedent.

## 84.6. Case/event/artifact links

Полезны как Work/runtime layer после semantic normalization.

## 84.7. AppDock Activation/Node boundary

Сильная platform boundary.

## 84.8. Platform-neutral presentation semantics

Ключ к Windows/Android.

---

# 85. Что нужно радикально переосмыслить

## 85.1. Operation-first public model

Недостаточен.

## 85.2. Scenario as central product object

Слишком execution-centric.

## 85.3. Artifact as result

Нужно отделить semantic Result.

## 85.4. JSON history as durable truth

Годится как ранняя implementation, но semantic owners должны быть определены независимо.

## 85.5. Background processes as separate subsystem

Лучше строить поверх Work/Program semantics.

## 85.6. Presence/assignment as collaboration truth

Только projections/participation relations.

---

# 86. Предлагаемая последовательность дальнейшей разработки

## Phase A — Semantic baseline

Сначала зафиксировать в отдельном target architecture research:

- semantic invariants;
- Subject/Source/Observation/Claim/Result distinctions;
- Work/Result/Artifact distinctions;
- Forecast/Scenario/Decision distinctions;
- currentness;
- provenance;
- Authority boundaries.

Без реализации.

## Phase B — Minimal epistemic contracts in core

Добавить только real-consumer contracts:

- SourceSnapshot;
- Observation identity;
- Measure/Definition;
- provenance;
- Result/Basis;
- temporal/vintage identity;
- missingness/UNKNOWN semantics.

## Phase C — Migrate existing domains

Первый приоритет:

1. `cbr_file_collector`;
2. `escrow`;
3. `cbr_forms`;
4. `cbr_industries`;
5. registries;
6. SORS alignment;
7. FRG parsers.

## Phase D — Work architecture

Replace conceptual center:

```text
ScenarioRunCase
```

with normalized:

```text
Work Instance
```

while scenarios remain UX projections if useful.

## Phase E — Knowledge/currentness

Introduce:

- dependency lineage;
- currentness calculation;
- impact analysis;
- maintained knowledge projections;
- research-to-current-knowledge reconciliation.

## Phase F — Evaluation/Challenge

Make reliance explicit.

## Phase G — Forecasting

Add Candidate/Vintage/ex-ante semantics.

## Phase H — Strategy/Decision

Only after evidence/forecast/evaluation boundaries are stable.

## Phase I — Communication/publishing

Treat artifacts as projections with protected properties.

## Phase J — Background revalidation

Source watchers become epistemic automation.

## Phase K — mobile / AI / remote

Reuse stabilized semantics rather than desktop implementation.

---

# 87. Acceptance tests целевой архитектуры

## Test 1 — Reported vs restored

Может ли пользователь отличить официально опубликованное значение от восстановленного?

Если нет — fail.

## Test 2 — Source trace

Можно ли от material result перейти к source snapshot/vintage?

## Test 3 — Definition trace

Можно ли понять, что именно означает показатель?

## Test 4 — Comparison bridge

Если сравниваются две series с разными perimeter/definitions, есть ли bridge или limitation?

## Test 5 — Historical integrity

Новый source не переписывает старый Forecast/Analysis silently?

## Test 6 — Currentness

Система понимает, что Result historically valid, но needs revalidation?

## Test 7 — UNKNOWN

Не исчезает ли UNKNOWN через normalization/export/UI?

## Test 8 — Claim-strength preservation

Может ли summary/report превратить conditional claim в factual claim?

Если да — fail.

## Test 9 — Decision separation

Recommendation может быть отображена как Decision без Authority transition?

Если да — fail.

## Test 10 — Acceptance separation

Successful computation автоматически становится accepted Result?

Если да — fail.

## Test 11 — Retry/effect

Если remote operation timed out, умеет ли Work выразить:

```text
effect unknown
```

а не просто `failed`?

## Test 12 — Dependency impact

При изменении registry/source можно определить зависимые Results без тотального refresh?

## Test 13 — Artifact lineage

Можно ли из Excel понять, какой semantic Result он represents?

## Test 14 — AI authority

Может ли AI сам повысить статус своего вывода до accepted/decision?

Если да — fail.

## Test 15 — Shared lineage

Несколько derivative reports считаются независимыми evidence только из-за количества?

Если да — fail.

## Test 16 — Forecast vintage

Historical Forecast может быть overwritten?

Если да — fail.

## Test 17 — UI semantics

Цвет/позиция/notification способны скрыто изменить action availability или priority meaning?

Если да — fail.

## Test 18 — Recovery

После restart/actor replacement можно безопасно продолжить Work без чтения полного transcript?

## Test 19 — Public boundary

Публичные core/surface contracts полностью нейтральны к конкретному закрытому окружению?

## Test 20 — Research amputation

После формирования Current Knowledge можно понять текущий result без обязательного чтения всей historical Research, сохранив forensic route назад?

---

# 88. Самые важные смысловые firewalls

Их стоит использовать как архитектурный checklist.

```text
Source ≠ world truth

Published value ≠ canonical internal value

Canonical ≠ true

Observation ≠ explanation

Data ≠ evidence for every claim

Evidence ≠ Authority

Model ≠ target

Model output ≠ fact

Decomposition ≠ cause

Correlation ≠ intervention effect

Scenario ≠ Forecast

Forecast ≠ Target

Forecast ≠ Decision

Probability ≠ confidence

Unknown ≠ zero

No finding ≠ absence

Many documents ≠ independent evidence

Result ≠ Artifact

Artifact ≠ Knowledge

Log ≠ Work State

Execution success ≠ Work success

Evaluation ≠ Acceptance

Acceptance ≠ world truth

Recommendation ≠ Decision

Decision ≠ Commitment

Commitment ≠ Execution

Execution ≠ intended effect

Outcome ≠ ex-ante decision quality

Message sent ≠ understood

Understood ≠ accepted

Accepted ≠ committed

Capability ≠ Authority

Presence ≠ responsibility

Workspace ≠ semantic owner

UI ≠ truth owner

Latest ≠ current for every use

Historical ≠ invalid

Current ≠ permanent
```

---

# 89. Итоговая целевая формула

Если всё исследование сжать в одну архитектурную формулу:

```text
Strategy Box
=
Domain/Data Engine
+
Epistemic Engine
+
Work Engine
+
Decision/Strategy Semantics
+
Projection/Communication Layer
+
Managed Runtime Boundary
```

Но более точная версия:

```text
Strategy Box
=
system that preserves
meaning,
identity,
grounds,
uncertainty,
time,
authority,
effects,
and lineage
while analytical work transforms
external information
into qualified knowledge
and, where authorized,
into decisions and actions.
```

---

# 90. Final assessment

Текущий Strategy Box уже содержит несколько элементов будущего продукта, но его нынешнюю архитектуру нельзя просто «довести».

Нужен сменённый conceptual center.

Сегодня:

```text
operation
→ scenario
→ case
→ artifact
```

Цель:

```text
Commission
→ Work
→ qualified semantic transformation
→ Result + Basis
→ knowledge/reliance state
→ optional Decision/Commitment
→ effects
→ maintained lineage
```

Сегодня:

```text
source
→ dataframe
→ xlsx
```

Цель:

```text
source authority
→ immutable snapshot
→ qualified observation
→ semantic definition
→ claim/inference
→ bounded Result
→ artifact projection
```

Сегодня:

```text
latest file
```

Цель:

```text
historical identity
+
currentness
+
applicability
+
successor relations
```

И самый важный переход:

> **Strategy Box должен перестать быть системой, которая только умеет что-то посчитать, и стать системой, которая умеет честно сказать, что именно она посчитала, что это означает, почему этому можно или нельзя доверять, что остаётся неизвестным, насколько результат актуален, для чего он пригоден и кто вправе на его основе что-либо решить.**

Именно в этом месте Strategy Box наиболее естественно стыкуется с MADAR.

---

# 91. Source ledger

## 91.1. MADAR current consolidation control

Repository: `ForestTiger-GH/MADAR`, branch `main`.

Ключевые материалы:

- `AGENTS.md`
- `_mw/AGENTS.md`
- `_mw/consolidation/STATE.md`
- `_mw/consolidation/BASELINE.md`
- `_mw/consolidation/ARCHITECTURE.md`
- `_mw/consolidation/PROCESS.md`
- `_mw/research/05_consolidation-input-research/README.md`
- `_mw/consolidation/notes/MADAR_Consolidation_Sequence_and_Target_Directory_Architecture_2026-10-01.md`

Наблюдаемый current-main в ходе исследования: линия около `be4dc2b3d53410286d37172e8ec7a8f071c518ea`. Отдельные Stage-3 Results фиксируют свои точные snapshots внутри самих Results.

## 91.2. Fresh Stage-3 consolidation-input Results

- `A1_Constitution_and_Boundaries_of_a_General_Engineering_Method_2026-10-01.md`
- `A2_Engineering_Object_Method_Boundaries_Identity_Composition_and_Evolution_2026-10-02.md`
- `A3_Commissioned_Work_Execution_Effects_Results_Acceptance_and_Closure_2026-10-02.md`
- `A4_Participation_Contracts_Authority_and_Adaptive_Work_Programs_2026-10-03.md`
- `A5_Durable_Work_State_Artifact_Ownership_Workspaces_Recovery_and_Handoff_2026-10-04.md`
- `A6_Engineering_Knowledge_Claims_Grounds_Uncertainty_Validity_and_Reliance_2026-10-05.md`
- `A7_Reconciliative_Knowledge_Synthesis_Provenance_Lifecycle_and_Learning_2026-10-05.md`
- `A8_Semantic_Relations_Bidirectional_Applicability_and_Governed_Resolution_2026-10-05.md`
- `B1_Goals_Values_Requirements_Decisions_and_Commitments_2026-10-06.md`
- `B2_Meaning_Representation_Models_Measurement_and_Comparability_2026-10-06.md`
- `B3_Structure_Composition_State_Time_Causality_and_Effects_2026-10-07.md`
- `B4_Evidence_Assurance_Independence_Freshness_and_Bounded_Reliance_2026-10-07.md`

B5 на наблюдаемом durable repository state ещё не был доступен как завершённый Result.

## 91.3. Fixed source repositories used by MADAR consolidation

- `ForestTiger-GH/MADARAII`
- `ForestTiger-GH/mandat-analytics`
- `ForestTiger-GH/mandat-forecast`
- `ForestTiger-GH/mandat-programming`
- `ForestTiger-GH/mandat-communication`
- `ForestTiger-GH/mandat-evaluation-challenge`
- `ForestTiger-GH/mandat-strategy-decision`

Baseline revisions записаны в MADAR `_mw/consolidation/BASELINE.md`.

## 91.4. `MADAR-supplements`

Repository: `ForestTiger-GH/MADAR-supplements`.

### 01-thinking

- `MADAR_Thinking_Corpus_Architectural_Decomposition_2026-10-02.md`
- `MADAR_Thinking_Corpus_Cross_Mandat_Integration_Research_2026-10-02.md`
- `MADAR_Thinking_Corpus_Future_Target_Lossless_Disposition_2026-10-02.md`

Along with original studies on abductive diagnostic hypothesis discovery, assumption-first/hypothesis support, conditional scenario consequence analysis, robust action under unresolved hypotheses, low-entropy control topology and hypothesis-conditioned equity analysis.

### 02-coding

- `MADAR-supplements_02-coding_cross-mandat-corpus-coupling_2026-10-02.md`
- `MADAR-supplements_02-coding_future-MADAR_lossless-disposition_2026-10-02.md`

Along with original studies on interfaces, formal interface systems/dynamics, low-entropy interfaces, temporal priority and governed adaptive interfaces.

### 03-communicating

- `MADAR_supplements_communication_corpus_mapping_to_MADAR.md`
- `MADAR_supplements_cross_mandat_communication_alignment_2026-10-02.md`
- `MADAR_supplements_03-communicating_target_MADAR_lossless_disposition_2026-10-02.md`

Along with original studies on authored text realization, pattern breaking, text transformation, communication as joint action, epistemic communication and representation/modality selection.

## 91.5. Strategy Box inputs

Project research:

- `stratbox_base_study_current_state_2026-10-06.md`
- `stratbox-windows_current_state_full_research_2026-10-06.md`
- current private environment-extension study, used only for neutral-boundary conclusions
- `AppDock — Базовое описание`

All current Strategy Box material is treated as transitional evidence, not target authority.

---

# 92. Research stopping note

Настоящий проход можно считать завершённым как **target-architecture Development Input**.

Исследование установило:

- целевой semantic center Strategy Box;
- основные epistemic firewalls;
- relation of source/data/observation/claim/model/result/artifact;
- Work/Result/Acceptance/Authority separation;
- Forecast/Scenario/Decision boundaries;
- representation/UI implications;
- currentness and revalidation model;
- relation to six mandate corpora;
- relation to all three MADAR-supplements corpora;
- target responsibilities of `stratbox`, `stratbox-windows` and AppDock boundary;
- transition priorities;
- acceptance/Jester tests.

Следующий уровень детализации уже должен быть отдельной commissioned задачей:

1. **Target Semantic Model of Strategy Box** — точное выделение минимальных semantic contracts без преждевременной schema design.
2. **Target Work Architecture** — Work / Program / Result / Acceptance / Question / Decision model.
3. **Target Knowledge Architecture** — Current Knowledge / Research / Claim / Evidence / Currentness / Revalidation.
4. **Target Data Semantics** — SourceSnapshot / Observation / Measure / Registry / Vintage / Comparability.
5. Только после этого — package/module topology и machine-readable schemas.

Это разделение важно: следующий шаг должен сначала уточнить смысл, а не начинать писать классы.
