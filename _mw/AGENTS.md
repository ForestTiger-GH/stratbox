# Strategy Box Engineering Workspace Passport

## Engineering Subject

Strategy Box — единый прикладной аналитический проект, состоящий из core и отдельных application/surface-реализаций.

Текущие implementation owners:

- `stratbox` — core-библиотека: доменная бизнес-логика, нейтральная инфраструктура, данные, модели и вычислительные операции;
- `stratbox-windows` — Windows application/surface Strategy Box;
- будущие platform surfaces получают собственных implementation owners только после их фактического появления.

Рабочее пространство `_mw/` является центральным Research/Work/provenance-контуром Strategy Box и физически размещено в репозитории `stratbox`. Размещение здесь материалов другого Strategy Box repository не переносит ownership его кода или текущей продуктовой семантики.

AppDock — отдельный внешний проект. Strategy Box может зависеть от его контрактов и среды исполнения, однако AppDock не входит в Engineering Subject этого workspace. Здесь исследуется только граница интеграции, когда она материальна для Strategy Box.

## Governing basis

- Human Commission: 2026-10-06 — минимально оформить инженерный workspace Strategy Box, сохранить исторические материалы и сформировать свежий baseline.
- Human Commission: 2026-10-09 — подготовить единый Knowledge Product и непрерывный агентный цикл, не начиная саму консолидацию.
- Scope clarification: 2026-10-06 — один общий `_mw` используется для Research и Work по `stratbox` и `stratbox-windows`; дублирование каталогов и исследований между репозиториями не требуется.
- Initial core baseline before workspace realization: `stratbox@72345991b2db272493e5d7c512c0f01ab32ca9b5`.
- Methodological orientation: general MADAR engineering method; concrete external material pointers are deliberately omitted from the public work passport.
- Core product boundary: root `README.md`, `docs/`, `pyproject.toml`, `src/stratbox/`, `tests/` and `scripts/`.
- Windows product boundary: current direct owners in repository `ForestTiger-GH/stratbox-windows`.

### Local specialization

По прямой Human Commission отдельный Work Architecture artifact сейчас не создаётся. Функция Engineering Work Architecture свёрнута в этот паспорт `_mw/AGENTS.md`, потому что отдельного жизненного цикла и отдельного потребителя для второго документа пока нет.

Отдельные `WORK_STATE.md`, `EPOCH.md`, `tasks/`, `results/`, `inbox/`, `outbox/` и другие поверхности также не материализуются заранее. Они появятся только при возникновении реальной ответственности, состояния или потребителя.

## Semantic owner map

| Роль | Текущий владелец / маршрут | Семантика |
| --- | --- | --- |
| Strategy Box core implementation | `stratbox/src/stratbox/` | текущая библиотечная реализация core |
| Core packaging and dependencies | `stratbox/pyproject.toml` | текущая упаковка и dependency contract core |
| Shared Strategy Box Knowledge Product | `stratbox/docs/` | будущие поддерживаемые Science / WHAT / Current HOW / HOW / Architecture / LDD; в данный момент bootstrap |
| Historic core documents | `stratbox/docs_old/` | content-preserved archive, не текущая спецификация |
| Knowledge consolidation Work | `stratbox/_mw/epochs-001-strategy-box-development/consolidation/` | отдельные циклы, census, source dispositions и checkpoints |
| Core verification | `stratbox/tests/`, `stratbox/scripts/` | проверки и evidence core |
| Windows surface implementation | `ForestTiger-GH/stratbox-windows` | текущая реализация Windows application/surface |
| Future Strategy Box surfaces | их собственные репозитории после материализации | platform-specific реализация |
| Strategy Box engineering workspace | `stratbox/_mw/` | общий Work/Research/provenance, отдельный от product runtime |
| Workspace passport and Work Architecture | `stratbox/_mw/AGENTS.md` | текущий маршрут, границы и архитектура Work-контура |
| Workspace human overview | `stratbox/_mw/README.md` | навигационная проекция |
| AppDock | внешний проект и его собственные owners | внешняя платформа; здесь владеем только Strategy Box-side integration questions |

Один общий workspace не превращает `stratbox` в монорепозиторий и не делает его владельцем Windows-кода. Текущая продуктовая истина всегда разрешается через прямой owner соответствующего компонента.

## Active Development Epoch

Ровно одна эпоха активна:

`_mw/epochs-001-strategy-box-development/`

**Purpose:** сформировать проверенную исходную картину Strategy Box как системы, сохранить прежние материалы с честной provenance-семантикой и подготовить дальнейшее согласованное развитие core и application surfaces.

**Current posture:** ACTIVE / CONSOLIDATION_PREPARED. Исследовательские ветки 01–03 существуют, а отдельный `consolidation/` готов к Human-commissioned непрерывной сборке знаний. Публичный `docs/` содержит пока только подготовительные маршруты; legacy-документы сохранены в `docs_old/`. Сам факт наличия Research или synthesis-материалов не означает принятого Product Decision, изменения реализации или admission в поддерживаемое Knowledge.

Повторное глобальное переоформление этой же работы не создаёт новую эпоху. Новая эпоха нужна при новом самостоятельном глобальном исходе или после явного закрытия текущей.

## Research architecture

Активный Research-контур находится в:

`_mw/epochs-001-strategy-box-development/research/`

### 01-old-notes

`_mw/epochs-001-strategy-box-development/research/01-old-notes/`

Роль: сохранять исторические заметки, прежние описания, ранние исследования и другие входы Strategy Box, возникшие до текущего формального workspace.

Материал здесь является source/provenance или историческим контекстом. Он не становится текущей архитектурой, текущим поведением или Product Decision из-за размещения в этой ветке.

### 02-base-study

`_mw/epochs-001-strategy-box-development/research/02-base-study/`

Роль: свежее базовое исследование фактического состояния Strategy Box по его прямым implementation owners.

Текущий состав включает отдельные исследования:

- core `stratbox`;
- Windows surface `stratbox-windows`.

Для каждого объекта первичный baseline — его фактический текущий репозиторий: код, упаковка, документация, тесты и инженерные проверки. `01-old-notes` используется как дополнительный источник вопросов и гипотез, но не как автоматическая текущая истина.

Research Result остаётся Research Result до отдельного допустимого перехода в продуктовый код, документацию, Decision или иной текущий owner.

### 03-consolidation-research

`_mw/epochs-001-strategy-box-development/research/03-consolidation-research/`

Роль: консолидировать накопленный Research corpus перед отдельной сборкой поддерживаемого Knowledge.

Ветка сводит темы и выводы между исследованиями, разрешает дублирование и противоречия, выравнивает терминологию и уровни абстракции, сохраняет provenance, отделяет текущее фактическое состояние от целевых гипотез и фиксирует UNKNOWN/пробелы. Основной вход — `02-base-study`; `01-old-notes` остаётся историческим source/provenance.

Результаты этой ветки остаются Research Results / Research Syntheses. Они не являются Scientific Knowledge, Product Decision, Target WHAT или Target HOW и не меняют implementation owners. Последующий Knowledge assembly имеет отдельный контракт и admission boundary.

## Work architecture

1. Текущие Product owners остаются вне `_mw/`; Work-история не дублирует их.
2. Общие и межрепозиторные Research/Work Strategy Box живут в одном центральном workspace.
3. Отдельный surface-репозиторий по умолчанию не получает дублирующий Research-контур только потому, что имеет собственный код.
4. Epoch-bound Research и будущие специализированные Work-артефакты живут внутри активной эпохи.
5. Физическая вложенность не задаёт Authority, приоритет или истинность.
6. Research-ветки именуются `NN-kebab-case`; числовой префикс даёт устойчивую навигацию, а не обязательную последовательность.
7. Новая поверхность создаётся только при реальном отличии ответственности, жизненного цикла, потребителя, доступа, failure/recovery или maintenance.
8. Исторический материал сохраняется; неизвестное наследие не удаляется ради чистоты.
9. Один класс текущего продукта имеет один основной текущий маршрут. Производные описания и Research не конкурируют с product owner.
10. AppDock-side продуктовые решения остаются в собственном проекте AppDock; здесь фиксируется только Strategy Box-side интеграционная семантика.
11. Общая архитектура Work-контура остаётся в этом паспорте; специализированный контур Knowledge consolidation имеет отдельные STATE, BASELINE, ARCHITECTURE и CYCLE ввиду собственного жизненного цикла и объёма.

## Authority and change boundaries

Human Commission определяет Work и может менять организационный контур.

Research может устанавливать evidence, гипотезы, выводы и рекомендации в пределах своего Result, но само по себе не:

- переписывает текущую реализацию core или surface;
- меняет публичные/внешние контракты;
- переносит ответственность между Strategy Box repositories;
- присваивает Strategy Box ownership внешним проектам;
- превращает старую заметку в текущую архитектуру;
- создаёт обязательный следующий Work.

Изменение продуктовой реализации выполняется отдельным явно порученным Work в репозитории фактического owner с релевантной проверкой.

## Interaction capabilities

- `may_emit_human_message: true`
- `may_block_waiting_for_human: false`

Файловые inbox/outbox каналы сейчас не требуются и поэтому не создаются.

## Cold recovery

Для нового агента или нового чата:

1. прочитать корневой `AGENTS.md` репозитория `stratbox`;
2. прочитать корневой `README.md`;
3. открыть этот `_mw/AGENTS.md`;
4. для Research открыть README точной нужной ветки; для Knowledge consolidation открыть `consolidation/README.md`, `STATE.md`, `BASELINE.md`, `ARCHITECTURE.md`, `CYCLE.md`;
5. определить фактический product owner исследуемого компонента;
6. читать только необходимые текущие code/docs/tests owners этого компонента и нужные Research materials.

Если задача касается `stratbox-windows`, текущая реализация читается из его собственного репозитория. Если задача касается интеграционной границы с AppDock, AppDock используется как внешний источник контракта; его внутренняя продуктовая архитектура не становится частью Strategy Box workspace.

Для понимания текущего продукта не требуется читать всю `_mw/` или восстанавливать историю по старым заметкам.

## Failure and fallback

Если текущая роль разрешается в ноль, несколько конфликтующих current-path кандидатов, устаревший locator или несовместимые источники, не выбирай по имени файла или исторической близости.

Для Product-состояния возвращайся к прямому owner соответствующего компонента. Для Work/Research — к этому паспорту и точной активной ветке. Материальную неоднозначность поднимай как отдельную проблему вместо скрытого выбора.

## Re-evaluation triggers

Пересмотри этот паспорт и при необходимости повторно обоснуй архитектуру и размещение Work-контура, если:

- меняется Engineering Subject или граница core/application surface;
- материализуется новый Strategy Box surface с собственным owner;
- появляется новый самостоятельный глобальный outcome;
- текущая эпоха закрывается или заменяется;
- появляется самостоятельный Work State, Task/Result lifecycle, file-backed human interaction или иной новый owner;
- Research приводит к принятой новой Knowledge/Product topology;
- cold entry перестаёт однозначно разрешать владельцев и безопасный следующий маршрут;
- физическая структура начинает расходиться с описанной здесь семантикой.

## Prepared Knowledge Consolidation

Точка входа: `_mw/epochs-001-strategy-box-development/consolidation/README.md`. Там один текущий Work State и проверяемая процедура длительного последовательного сведения исходных Research, старой документации и прямых реализационных оснований в раздельные публикуемые роли. Подготовка маршрута не принимает содержательные обязательства продукта и не запускает автономную работу. Для запуска следующему агенту требуется отдельная Human Commission; в её рамках предусмотрено непрерывное исполнение с checkpoint/recovery без обязательных межэтапных запросов к пользователю.

Ссылки на конкретные материалы внешней инженерной методологии и внешних когнитивных проектов в новом публичном корпусе и рабочих инструкциях не нужны. Общая методология MADAR и фундаментальные выводы доступны для применения в собственных предметных формулировках. Внешний ИИ-агент описывается нейтрально. Исторические исследовательские файлы остаются неизменными; охраняемые реализации расширений остаются вне открытого знания.
