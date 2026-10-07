# Strategy Box: универсальная архитектура бизнес-сегментов, переносимость и повторное использование кода

**Research branch:** вторая ветка исследований Strategy Box  
**Дата:** 2026-10-07  
**Статус:** Research Result — приватный исследовательский материал проекта; в репозитории не размещается  
**Scope:** `stratbox` core, `stratbox-windows`, будущий `stratbox-android`, корпоративный runtime, AppDock boundary, Jupyter Notebook, Google Colab, обычный Python, повторное использование библиотечных блоков  
**Практический кейс:** приложенный notebook `CBR_dbf_to_csv (1).ipynb`

> **Граница публикации.** Этот research хранится внутри проекта и поэтому рассматривает корпоративный контур целиком. Любая последующая реализация в публичных репозиториях `stratbox` и `stratbox-windows` должна оставаться полностью нейтральной к закрытому корпоративному расширению: без его имени, package name, внутренних типов, адресов и описания реализации. Корпоративная конкретика должна оставаться только за приватной границей.

---

# 0. Краткий вывод

Главное архитектурное правило:

> **Одна бизнес-возможность должна иметь одну каноническую реализацию в `stratbox`, но несколько способов потребления.**

Эта реализация не должна быть одним большим скриптом. Зрелый сегмент раскладывается на уровни:

```text
маленькие библиотечные primitives
        ↓
общие технические сервисы
formats / archives / HTTP / materialization / FileStore
        ↓
доменные функции
discovery / parsing / normalization / views / calculations / export
        ↓
каноническая business operation
Typed Request → Typed Result
        ↓
сценарии / workflows
        ↓
consumer
Windows / Android / Jupyter / Colab / plain Python / automation / AI
```

**Единым должен быть внешний контракт, а не внутренняя сложность.** DBF→CSV может состоять из нескольких чистых функций; escrow — из обычного end-to-end pipeline; SORS — из большой вычислительной подсистемы. Их не нужно искусственно выравнивать по внутренней структуре. Снаружи у зрелой operation должны быть единые свойства: stable ID, typed Request/Result, declared capabilities, явные side effects, structured failures, progress/cancellation для долгих запусков, provenance и отсутствие зависимости от UI/environment.

Это даёт одновременно четыре требуемых режима:

```text
Strategy Box Windows
    → вызывает operation из stratbox

корпоративный Jupyter
    → вызывает ту же operation из stratbox

Google Colab / plain Python
    → вызывает ту же operation из stratbox

другой код
    → при необходимости импортирует нижний reusable building block
      и вообще не использует application/scenario engine
```

Именно такой подход позволяет в будущем «брать» универсальные куски кода из Strategy Box без копирования исходника.

---

# 1. Ответ на исходный практический вопрос

Для истории счетов эскроу целевой Python-native вызов должен выглядеть примерно так:

```python
from stratbox.macrobanks.escrow import (
    EscrowHistoryBuildRequest,
    build_escrow_history,
)

result = build_escrow_history(
    EscrowHistoryBuildRequest(...)
)
```

Этот же вызов должен работать в Jupyter, Colab, обычном Python и внутри managed application. Различается только `ExecutionContext`: storage, network policy, materialization, progress, cancellation и artifact target.

Если другому коду нужен лишь parser:

```python
from stratbox.macrobanks.escrow import parse_escrow_source

parsed = parse_escrow_source(content)
```

Если нужен только универсальный DBF converter:

```python
from stratbox.formats.dbf import transcode_dbf_to_csv
```

То есть правильное повторное использование — **import stable public function**, а не copy/paste блока исходника. Исправление ошибки тогда делается один раз.

---

# 2. Исследованная база

## 2.1. `stratbox`

Повторно проверен актуальный `main` на 2026-10-07.

```text
package version: 0.8.0
Python: >= 3.10
current main: cffe019e17e1b88a58bd9ca277c9a960964b623b
```

Последние commits добавляют материалы второй ветки исследований; production-архитектура core относительно baseline 2026-10-06 принципиально не изменилась.

Проверены: `pyproject.toml`, runtime provider selection, network layer, DBF/CSV/RAR helpers, `cbr_forms`, `escrow`, а также исследования file/artifact и file-format layers.

## 2.2. `stratbox-windows`

Проверен `main`:

```text
HEAD: 959e9c4ce1441124af5111c1e025041714e04d3b
package version: 0.1.0
```

Повторно проверены operation registry/contracts/handlers, scenarios, runtime bootstrap, artifacts, file types, package metadata и AppDock manifest.

## 2.3. AppDock

По просьбе основной AppDock-рамкой использован актуальный repository, а не только базовое описание.

```text
current main: a4d87c643e620e54e04083d4d0b8d867513e7065
```

Проверены current README, world/source/package/runtime model, activation, observability target и task lifecycle.

## 2.4. Корпоративный runtime

Использован приватный current-state research от 2026-10-06. Его главный вывод остаётся верным: environment-specific infrastructure должна подключаться снаружи, а банковская/макроэкономическая логика остаётся в public core.

## 2.5. Приложенный notebook

`CBR_dbf_to_csv (1).ipynb` разобран статически:

```text
1 code cell
1 157 строк Python
37 653 символа
3 class/dataclass
28 top-level functions
```

Он содержит одновременно: даты, HTTP/retry, discovery публикаций ЦБ, jobs, RAR tool bootstrap, download, extraction, собственный DBF parser, DBF→CSV, hashes, manifests, ZIP, concurrency и Colab-specific download. Это не «одна функция-конвертер», а вертикальный мини-продукт — идеальный test case для декомпозиции.

---

# 3. Пять сущностей, которые нельзя смешивать

## 3.1. Building block

Обычная библиотечная функция/тип:

```text
read_dbf_header
decode_dbf_field
transcode_dbf_to_csv
period_points
sha256
normalize_bank_name
safe_extract_archive
```

Свойства: маленький scope, прямой import, отсутствие UI/AppDock/case semantics, хорошие unit tests.

## 3.2. Technical service

Техническая capability выше primitives:

```text
DBF reader/transcoder
archive reader
materializer
HTTP fetch
format detection
```

Она понимает технический формат/transport, но не бизнес-смысл формы ЦБ или escrow.

## 3.3. Domain service

Предметный блок:

```text
discover escrow sources
parse one escrow workbook
build canonical escrow history
resolve CBR reporting archive
parse form 802 physical schema
```

Он знает предметную семантику, но ещё не обязан быть пользовательской кнопкой.

## 3.4. Canonical operation

Стабильный use case:

```text
escrow.history.build
escrow.history.export
cbr.forms.raw_export
cbr.forms.build
frg.cleanup.plan
frg.cleanup.execute
sors.restore
```

Operation имеет Request/Result, required capabilities, side effects, availability, error/outcome semantics, progress/cancellation и artifacts/provenance.

## 3.5. Scenario / surface

Scenario компонует operations в пользовательский workflow. Surface превращает operation/scenario в кнопку, форму, progress и карточку результата.

```text
operation = business use case
scenario  = workflow
surface   = presentation
```

---

# 4. Базовый принцип: uniform exterior, variable interior

Нельзя пытаться сделать все домены одинаковыми внутри.

Правильная унификация:

```text
Request → operation → Result
capabilities
diagnostics
provenance
artifacts
progress/cancellation
```

Внутри operation может быть:

- одна pure function;
- 5-stage ETL;
- solver subsystem;
- safe destructive plan/apply workflow.

Так core сохраняет естественную архитектуру каждого домена, а consumers получают единый контракт.

---

# 5. Applicability должна быть capability-driven

Пользователь отдельно отметил различную применимость сегментов. Нельзя фиксировать её флагами:

```text
works_in_colab
works_in_company
works_in_windows
```

Нужна формула:

```text
required capabilities
+ input constraints
+ dependency availability
+ permissions
+ true platform constraints
= availability
```

Пример DBF→CSV:

```text
binary read
text/binary write
DBF faithful decoder
CSV writer
```

Он доступен почти везде.

Escrow:

```text
HTTP fetch
XLSX parse
temporary/materialized content
writable output/artifact target
```

Эти capabilities могут быть реализованы local Python, Colab, corporate notebook или managed Strategy Box.

Рекомендуемый availability result:

```text
AVAILABLE
AVAILABLE_DEGRADED
AUTHENTICATION_REQUIRED
DEPENDENCY_MISSING
CAPABILITY_MISSING
INPUT_UNSUPPORTED
PLATFORM_UNSUPPORTED
CONFIGURATION_REQUIRED
UNAVAILABLE
```

UI получает причину и может выключить кнопку. Notebook может вызвать `check_operation_availability()` до запуска.

---

# 6. Ownership по репозиториям

```text
stratbox
    business truth
    parsers / calculations / canonical data
    canonical operations
    generic formats
    neutral capability contracts
    provenance

shared Strategy Box application semantics
    scenarios
    jobs/cases
    operation presentation projection
    artifact/event workflow

stratbox-windows
    Qt rendering
    Windows host integration
    desktop UX

future stratbox-android
    mobile rendering
    Android host integration

AppDock
    delivery
    exact runtime/package composition
    activation
    node/session
    platform observability
    remote execution boundary

private environment package
    environment-specific implementations
    no banking business logic
```


---

# 7. Public facade зрелого домена

На примере escrow:

```text
stratbox.macrobanks.escrow
│
├─ contracts.py
├─ sources.py
├─ parser.py
├─ history.py
├─ views.py
├─ export.py
├─ operations.py
└─ __init__.py
```

Curated public API:

```python
from stratbox.macrobanks.escrow import (
    EscrowHistoryBuildRequest,
    EscrowHistoryResult,
    discover_escrow_sources,
    parse_escrow_source,
    build_escrow_history,
    build_escrow_views,
    export_escrow_workbook,
)
```

`__init__.py` должен быть осознанной public boundary. Внутренние helpers могут оставаться private.

---

# 8. Escrow уже близок к целевой форме

Текущий escrow имеет:

```text
discover_escrow_sources
build_escrow_history
build_escrow_views
export_escrow_workbook
run_escrow_export
```

и typed contracts:

```text
EscrowHistoryBuildRequest
EscrowHistoryResult
EscrowViewBuildRequest
EscrowWorkbookExportRequest
EscrowExportResult
```

Плюсы:

- discovery отделён;
- parsing/building отделён от presentation;
- canonical long data существует раньше Excel;
- source failures представлены данными;
- FileStore можно передать явно;
- full wrapper не уничтожает lower-level API.

Это хороший pilot canonical operation architecture.

## 8.1. Что ещё исправить в escrow

### Environment-specific network flag

Public business request сейчас содержит флаг, влияющий на environment-specific routing. Это лишняя утечка слоя.

Domain должен сказать:

```text
fetch this source
```

а runtime/network capability выбирает маршрут.

### Неявный global context

Notebook convenience полезен:

```python
filestore or get_filestore()
```

Но managed execution лучше строить на explicit `ExecutionContext`.

### Cache path

В user-level request физический `source_cache_dir` лучше постепенно заменить semantic policy:

```text
USE_CACHE
REFRESH
BYPASS
```

Physical cache location — runtime concern.

### Provenance

Нужно фиксировать source snapshots, hashes, parser/schema version, core version, request fingerprint и warnings.

---

# 9. `cbr_forms` — противоположный пример

Текущий public shortcut:

```python
run_all_forms_to_xlsx(...)
```

удобен для notebook, но смешивает:

```text
period resolution
bank registry
semantic model
download
RAR
DBF
calculation
local Path output
Excel export
print/tqdm
dict[path] result
```

`common/runner.py` дополнительно:

- ищет `unrar/7z`;
- запускает subprocess;
- создаёт локальные temp dirs;
- распаковывает;
- выбирает DBF;
- строит DataFrame;
- печатает progress.

Это рабочий код, но не каноническая multi-environment boundary.

Целевой pipeline:

```text
source discovery/fetch
        ↓
archive/materialization
        ↓
physical DBF parser
        ↓
semantic form build
        ↓
FormDataResult
        ↓
views
        ↓
export
```

`run_all_forms_to_xlsx` после этого может остаться тонким notebook convenience wrapper.

---

# 10. Нейтральный `ExecutionContext`

Предлагаемая минимальная модель:

```python
@dataclass(frozen=True)
class ExecutionContext:
    filestore: FileStore
    http: HttpClient
    materializer: Materializer
    progress: ProgressSink
    cancellation: CancellationToken
    clock: Clock
    run_identity: RunIdentity | None = None
    artifact_sink: ArtifactSink | None = None
```

Реализация может быть capability-based; не каждый operation использует всё.

## 10.1. Почему это лучше environment flags

Business code не спрашивает:

```text
am I in Windows?
am I in Colab?
am I inside company?
```

Он использует:

```text
read
write
fetch
materialize
progress
cancel
```

## 10.2. Default context

Notebook:

```python
ctx = get_default_context()
```

Managed runtime:

```python
ctx = build_context_from_runtime(...)
```

Tests:

```python
ctx = ExecutionContext(
    filestore=MemoryFileStore(...),
    http=FakeHttpClient(...),
    ...
)
```

---

# 11. Нейтральный provider contract

Текущий core уже использует Python package metadata/entry points — направление правильное. PyPA официально определяет entry points как механизм, через который установленный distribution объявляет discoverable components, доступные consumer через `importlib.metadata`.

Целевой public contract:

```text
entry point group: stratbox.providers
```

Условный bundle:

```text
ProviderBundle
├─ storage capability
├─ network capability/policy
├─ optional auth/secrets capability
├─ optional presentation/style capability
└─ health/readiness
```

Public core не знает имени конкретного distribution. Environment package просто регистрирует generic provider.

---

# 12. P0: public/private boundary сейчас нарушена

При повторной проверке актуального `main` обнаружено несколько мест, которые стоит исправить немедленно.

## 12.1. `stratbox`

Current public package metadata содержит optional dependency на закрытый distribution.

Current runtime использует private-specific terminology в provider discovery.

Current URL/network layer прямо пытается импортировать конкретный private package.

Даже если fallback делает систему работоспособной снаружи, сама зависимость public code → private package name неправильна.

## 12.2. `stratbox-windows`

Current `pyproject.toml` также содержит private optional dependency.

Current business operation metadata/handler передают environment-specific network flag.

## 12.3. Target

Public repos содержат только:

```text
generic provider contract
generic entry-point group
generic NetworkPolicy / HttpClient
generic FileStore
generic capability/readiness API
```

Ни package name, ни infrastructure implementation, ни corporate routing details в public source не остаются.

## 12.4. Контроль границы

Публичный repository не должен хранить даже список private identifiers, потому что такой список сам раскрывает их.

Два уровня контроля:

1. **Public architecture test**
   - core/domain imports только из allowlisted public namespaces;
   - network/runtime зависят от public Protocols;
   - environment implementation imports отсутствуют.

2. **Private release/compliance audit**
   - сканирует public source/wheel/docs/manifest на private identifiers;
   - живёт вне публичного repository.

---

# 13. Operation contract

Предлагаемый descriptor:

```python
OperationDescriptor(
    id="escrow.history.export",
    request_type=EscrowHistoryExportRequest,
    result_type=EscrowHistoryExportResult,
    required_capabilities=(
        "http.fetch",
        "filestore.read",
        "filestore.write",
        "format.xlsx.read",
        "format.xlsx.write",
    ),
    side_effects=("network.read", "artifact.write"),
    cancellable=True,
    progress=True,
    risk="low",
    idempotency="deterministic_for_same_sources",
    artifact_outputs=("dataset", "workbook"),
)
```

Descriptor не содержит:

- Qt widget;
- Windows path;
- AppDock internal class;
- private package;
- Colab code;
- private gateway;
- button style.

---

# 14. Canonical Result

Текущий Windows `OperationResult`:

```text
ok
message
outputs
details
```

достаточен для prototype, но слишком слаб для portable execution.

Target envelope:

```text
OperationResult
├─ outcome
├─ value
├─ warnings
├─ failures
├─ diagnostics
├─ artifacts
├─ provenance
└─ metrics
```

## 14.1. Terminal outcome

```text
SUCCESS
PARTIAL
CANCELLED
FAILURE
UNKNOWN
```

`UNKNOWN` нужен для side effects, чей итог нельзя доказать. Например remote write мог быть committed до timeout. Нельзя автоматически считать «failure = ничего не произошло».

Это согласуется с current AppDock observability target: success, expected cancellation, partial, registered failure и unknown outcome должны различаться.

## 14.2. Structured Failure

```text
code
category
stage
safe_message
retryable
structured_context
```

Raw exception остаётся в technical log/evidence.

---

# 15. P0: current Windows runner раскрывает raw exception

Сейчас exception превращается примерно в:

```text
message = "Operation failed: {exc}"
details["error"] = str(exc)
```

Это удобно для разработки, но плохо для:

- security;
- stable automation;
- localization;
- AI consumption;
- AppDock observability;
- future remote API.

Target:

```text
Exception
   ↓
operation boundary
   ↓
Failure(code, stage, safe_message, retryable)
   ↓
Windows projection
Notebook projection
AppDock problem/evidence projection
```

---

# 16. Progress — часть execution contract

Сегодня в разных местах существуют `print`, `tqdm`, Qt signals.

Лучше:

```python
context.progress.emit(
    OperationProgress(
        stage_id="download",
        current=4,
        total=12,
        message="..."
    )
)
```

Adapters:

```text
NullProgressSink
TqdmProgressSink
NotebookProgressSink
QtProgressBridge
AppDockProgressBridge
```

Business code выпускает semantic progress. Surface решает, как рисовать.

---

# 17. Cancellation

Для долгих операций нужен neutral token:

```python
if context.cancellation.requested:
    ...
```

Проверка выполняется между безопасными stages.

Это одинаково применимо к Windows, background jobs, remote host, Jupyter и будущему Android.

AppDock current task runner уже имеет cancellation event; Strategy Box не должен импортировать его тип. Adapter связывает его с generic `CancellationToken`.

---

# 18. Artifact вместо path-only result

Предыдущее исследование file/artifact layer правильно отделило artifact identity от физического path.

Local notebook:

```text
/path/report.xlsx
```

удобен.

Remote/mobile:

```text
C:\...\report.xlsx
```

не имеет смысла.

Поэтому canonical Result должен постепенно возвращать:

```text
ArtifactRef
ArtifactDescriptor
```

а path быть одной из materializations.

---

# 19. SourceSnapshot и provenance

Минимальный provenance для data operation:

```text
operation_id
operation_version
stratbox_version
request_fingerprint

sources:
- source_id
- requested URL
- final URL
- fetched_at
- content_type
- size
- sha256
- schema/parser version

registries:
- bank registry version
- geography version
- classifier version

outputs:
- artifact IDs
- output hashes

warnings
failures
```

Это даёт reproducibility, caching, change detection и auditability.


---

# 20. Роль `stratbox-windows`

Windows должна стать **generic consumer canonical operations**, а не вторым владельцем business truth.

Сегодня цепочка выглядит:

```text
Windows OperationSpec
→ domain-specific Windows handler
→ core domain function
```

При росте до десятков operations это создаст дублирование metadata и adapters.

## 20.1. Target

```text
stratbox:
    OperationDescriptor + callable + Request/Result

shared application:
    scenario catalog
    Job/Case/Event/Artifact semantics
    operation presentation projection

stratbox-windows:
    presentation overlay
    Qt renderer
    Windows host adapter
```

## 20.2. Generic core-operation adapter

Вместо обязательного handler-файла на каждый новый domain:

```text
CoreOperationAdapter
    resolve operation ID
    map UI values → typed Request
    inject ExecutionContext
    execute
    map Result → Case/Artifacts/Events
```

Dedicated handler остаётся только для реально platform-specific integration.

---

# 21. Parameter schema: semantic vs presentation

Current Windows `OperationParamSpec` смешивает:

```text
type
required
default
enum/range
title
description
placeholder
UI section
```

Target:

## Core semantic schema

```text
name
type
required
default
enum
range
accepted formats
semantic meaning
```

## Presentation overlay

```text
display title
localization
icon
group/order
widget preference
placeholder
basic/advanced grouping
```

Windows и Android читают одну semantic schema и рендерят её разными toolkit.

---

# 22. Scenario layer

Current `scenario.cbr.full_update` — хороший пример application-level composition.

```text
1. collect raw CBR files
2. build escrow history
```

Scenario — user workflow, поэтому естественный owner — shared Strategy Box application semantics.

Если композиция сама становится устойчивым предметным алгоритмом со своим domain result, её можно поднять в core как отдельную operation. По умолчанию workflows не должны утягивать core в UI/application semantics.

---

# 23. AppDock boundary

Current AppDock строится вокруг:

```text
source admission
→ world definition
→ release
→ deployment/runtime truth
→ activation
→ surface
```

Внешнее приложение сохраняет свою внутреннюю архитектуру. Из этого следует:

> AppDock разворачивает и наблюдает Strategy Box как продукт; он не должен становиться registry каждой банковской функции.

AppDock не обязан знать:

```text
escrow.history.export
escrow.build_views
decode_dbf_field
```

Он должен знать:

```text
Strategy Box world
exact runtime packages
surface activation
Data/Node binding
runtime readiness
session/job/process state
high-level artifacts
```

## 23.1. Три уровня observability

### Core

```text
operation stage
source failure
validation warning
domain diagnostics
provenance
```

### Strategy Box application

```text
Job
Case
step
progress
artifact
user-facing operation result
```

### AppDock

```text
process/runtime/session/node truth
platform ProblemOccurrence
delivery/activation/runtime evidence
```

Authority не дублируется.

---

# 24. Corporate AppDock delivery

Public `stratbox-windows` manifest не должен раскрывать private environment package.

Корпоративной поставке при этом нужен дополнительный provider. Чистая модель — private composition вне public repositories:

```text
private AppDock world / manifest authority
    ├─ references public Strategy Box sources/packages
    └─ adds private environment package
```

или equivalent private authoring/release definition, если AppDock позволяет дополнять отсутствующие fields без изменения public source authority.

Ключ:

```text
public manifest
    = public product truth

private corporate release composition
    = private environment truth
```

Если current manifest immutability не позволяет безопасно дополнить уже объявленный package graph, правильнее сделать private manifest-authority/wrapper, чем вписывать private dependency в public manifest.

---

# 25. P0: version drift

На 2026-10-07:

```text
stratbox = 0.8.0
```

а current `stratbox-windows`:

```text
pyproject: stratbox==0.2.1
AppDock manifest: core package 0.2.1
```

Это прямое расхождение production contracts.

С учётом правила «обратная совместимость не нужна» лучше сразу синхронизировать current surface с current core, а не сохранять compatibility с 0.2.1.

---

# 26. Corporate Jupyter

Notebook внутри корпоративного environment должен писать тот же public код:

```python
from stratbox.macrobanks.escrow import (
    EscrowHistoryBuildRequest,
    build_escrow_history,
)

result = build_escrow_history(
    EscrowHistoryBuildRequest(...)
)
```

Разница находится в environment:

```text
public core
+
installed environment provider
```

Core discovers generic provider contract.

Notebook:

- не импортирует private package;
- не знает storage implementation;
- не знает network routing implementation;
- не содержит credentials;
- не содержит альтернативную бизнес-реализацию.

---

# 27. Google Colab

Colab нужно считать **disposable execution environment**.

Официальная FAQ Google Colab говорит, что code выполняется в VM, VM удаляется после idle period и имеет maximum lifetime. Поэтому Colab нельзя делать владельцем долговременного application state или канонической реализации.

Target notebook:

```text
cell 1: install exact public stratbox release
cell 2: imports
cell 3: typed Request
cell 4: run
cell 5: inspect/materialize/download artifact
```

Colab-specific glue:

```text
pip install
optional system dependency bootstrap
/content paths
Google Drive mount
google.colab.files.download
rich display
```

остаётся в notebook adapter, а не в core.

---

# 28. Plain Python

Plain Python — самый простой consumer:

```python
from stratbox.formats.dbf import transcode_dbf_to_csv

result = transcode_dbf_to_csv(...)
```

или dynamic operation call:

```python
from stratbox.operations import run

result = run("cbr.forms.raw_export", request)
```

Windows/AppDock dependency отсутствует.

---

# 29. Building blocks нельзя превращать в giant operation registry

Плохой operation registry:

```text
decode_dbf_field
sha256_file
normalize_form_code
csv_relative_path
```

Это library API.

Правильный registry:

```text
cbr.forms.raw_export
cbr.forms.build
escrow.history.build
escrow.history.export
frg.cleanup.plan
frg.cleanup.execute
sors.restore
```

Правило:

> **Operation = use case. Building block = import.**

---

# 30. Curated reusable block API

Чтобы developer реально мог «взять готовый блок», public namespaces должны быть понятными:

```text
stratbox.formats.dbf
stratbox.formats.csv
stratbox.formats.archives
stratbox.sources
stratbox.common.time
stratbox.text
```

В public module:

```python
__all__ = [
    "inspect_dbf",
    "iter_dbf_records",
    "transcode_dbf_to_csv",
]
```

Developer получает явный сигнал: exported symbol является supported reusable API.

---

# 31. Notebook DBF→CSV: фактическая декомпозиция

Приложенный notebook — вертикальный pipeline.

| Строки | Блок | Архитектурный уровень |
|---:|---|---|
| ~147–202 | date/form-code helpers | common/domain helper |
| ~209–256 | HTTP + official archive discovery | source layer |
| ~260–324 | Job / planning | operation orchestration |
| ~335–492 | RAR tools/download/extraction | format/runtime |
| ~500–645 | DBF structural parser | generic format primitive |
| ~648–754 | SHA + DBF→CSV transcoder | generic format service |
| ~761–783 | output paths/encoding policy | domain/export policy |
| ~786–936 | one CBR job | domain operation step |
| ~943–1009 | manifests/ZIP | provenance/artifact packaging |
| ~1012–1153 | full series runner | application/domain operation |
| ~1143–1148 | Colab auto-download | Colab adapter |

Следовательно, перенос notebook «целиком в один module» лишь перенесёт монолит. Нужна декомпозиция по ownership.

---

# 32. Source-faithful DBF — важный новый generic capability

Notebook содержит более строгую DBF-семантику, чем current `base.ioapi.dbf.read_df`.

Особенно важны:

## Character

Убирается только fixed-width right padding.

## N/F numeric fields

Физически это textual values. Notebook сохраняет исходную decimal lexical representation, а не делает:

```text
parse float → stringify
```

Это критично для source-faithful conversion.

## Date

Исходный `YYYYMMDD` сохраняется без нормализации.

## Logical

Source markers сохраняются.

## Binary integer/currency/double

Декодируются по физическому типу и размеру.

## Timestamp

Raw 8 bytes сохраняются детерминированно в hex вместо неподтверждённой календарной интерпретации.

## Memo-like M/G/P

Fail-fast: одного DBF недостаточно, нужен DBT/FPT-aware path.

## Deleted records

Физические deleted rows также выгружаются, а record numbers фиксируются в manifest.

## Invariants

Notebook проверяет record length и row count, а не тихо продолжает.

---

# 33. Current `ioapi.dbf` и faithful transcoder — разные продукты

Current generic reader:

```text
DBF
→ dbfread
→ Python values
→ pandas DataFrame
```

Это хорошо для анализа.

Faithful converter:

```text
DBF physical records
→ controlled lexical decode
→ UTF-8 CSV
+ structural manifest
```

Это archival/replication use case.

Их нельзя объединять под двусмысленным `read_dbf()`.

---

# 34. Target DBF API

```text
stratbox.formats.dbf
│
├─ DBFField
├─ DBFHeader
├─ inspect_dbf
├─ iter_dbf_records
├─ read_dbf_frame
├─ transcode_dbf_to_csv
├─ DBFTranscodePolicy
└─ DBFTranscodeResult
```

## `read_dbf_frame`

Analysis convenience. Python types допустимы.

## `transcode_dbf_to_csv`

Source-faithful representation.

```python
DBFTranscodePolicy(
    text_encoding="cp866",
    include_deleted=True,
    numeric_mode="source_lexeme",
    memo_policy="fail",
)
```

Result:

```text
field descriptors
source record count
exported record count
deleted record numbers
encoding
source hash
target hash
warnings
unsupported features
```

---

# 35. Stream/materialization boundary

Current notebook работает с local `Path`. Generic format service лучше проектировать:

```text
BinaryIO → TextIO
```

где возможно.

Для libraries, которым нужен physical path, использовать общий materialization layer:

```python
with materialize_read(source, store=...) as local_path:
    ...
```

и:

```python
with materialize_write(target, store=...) as local_path:
    ...
# commit only after successful context exit
```

Это устраняет повторяющиеся temp-dir implementations в DBF/RAR/XBRL/legacy Excel.

---

# 36. RAR — generic format capability, не CBR business logic

Notebook:

- ищет `unrar`, `7zz`, `7z`;
- строит command;
- вызывает subprocess;
- распаковывает.

Target:

```text
stratbox.formats.archives
    ArchiveReader
    ArchiveExtractionPlan
    safe_extract
```

Environment отвечает за backend.

Core business run **не должен делать package/system installation**.

```text
AppDock → dependency installed in exact runtime
Colab  → optional bootstrap cell
Jupyter→ provisioned environment
```

Если backend отсутствует:

```text
DEPENDENCY_MISSING
```

---

# 37. Archive safety

При переносе notebook стоит сразу сертифицировать:

```text
path traversal rejection
absolute path rejection
symlink policy
member count limit
expanded byte limit
compression ratio limit
collision detection
case-fold collision detection
partial extraction cleanup
```

Notebook уже проверяет collision после case-fold normalization — хорошая идея, которую стоит сохранить.

---

# 38. CBR-specific discovery

Функции вроде:

```text
discover_official_archives
build_jobs
indexed_dates_in_window
normalize_form_code
```

принадлежат не format layer, а:

```text
stratbox.sources.cbr
```

или `macrobanks.cbr_forms.sources`.

Целевая модель:

```text
CbrReportingSourceDescriptor
CbrReportingArchiveSnapshot
```

со stable source identity и provenance.

---

# 39. Target operation из notebook

Предлагаемый stable use case:

```text
cbr.forms.raw_export
```

Request:

```python
CbrFormsRawExportRequest(
    date_from="2026-01-01",
    date_to="2026-09-01",
    forms=("101", "102", "123", "135", "802", "805"),
    representation="csv",
    source_fidelity=True,
    include_source_archives=False,
)
```

Result:

```text
outcome
requested periods
available periods
source snapshots
per-form results
missing publications
failures
artifacts
manifest
metrics
provenance
```

Pipeline:

```text
discover
→ plan
→ fetch
→ safe extract
→ DBF faithful transcode
→ manifest
→ artifact commit
```


---

# 40. Future Colab notebook

Вместо 1 157 строк:

```python
!pip install "stratbox==<release>"

from stratbox.macrobanks.cbr_forms import (
    CbrFormsRawExportRequest,
    export_raw_forms,
)

result = export_raw_forms(
    CbrFormsRawExportRequest(
        date_from="2026-01-01",
        date_to="2026-09-01",
    )
)

result
```

Colab-only adapter:

```python
from google.colab import files

local_zip = result.primary_artifact.materialize()
files.download(local_zip)
```

`google.colab` остаётся в notebook, не в `stratbox`.

---

# 41. Reuse только DBF converter

```python
from stratbox.formats.dbf import (
    DBFTranscodePolicy,
    transcode_dbf_to_csv,
)

result = transcode_dbf_to_csv(
    "0409101.dbf",
    "0409101.csv",
    policy=DBFTranscodePolicy(
        text_encoding="cp866",
        include_deleted=True,
        numeric_mode="source_lexeme",
    ),
)
```

Это целевая форма «взять готовый универсальный блок».

---

# 42. Нужна ли отдельная operation `files.dbf.convert_csv`

Только если появляется product use case:

```text
user selects DBF
→ clicks Convert
→ gets CSV
```

Тогда operation:

```text
files.dbf.convert_csv
```

является thin wrapper над **той же** `transcode_dbf_to_csv`.

```text
one implementation
    ↑
direct import
    ↑
optional operation
    ↑
Windows/Android action
```

---

# 43. Notebook as executable documentation

После извлечения production logic notebook превращается в:

```text
tutorial
example
recipe
smoke
exploratory surface
```

Это полезнее, чем production source в `.ipynb`.

Правило:

> Если полезная функция из notebook имеет повторное применение, она должна мигрировать в package; notebook оставляет orchestration/display.

---

# 44. Target tree `stratbox`

С учётом исследований второй ветки:

```text
stratbox/
│
├─ base/
│  ├─ filestore/
│  ├─ runtime/
│  ├─ materialization/
│  ├─ diagnostics/
│  └─ capabilities/
│
├─ formats/
│  ├─ registry.py
│  ├─ csv/
│  ├─ excel/
│  ├─ dbf/
│  ├─ archives/
│  ├─ documents/
│  └─ ...
│
├─ sources/
│  ├─ contracts.py
│  ├─ fetch.py
│  ├─ snapshot.py
│  └─ cbr/
│
├─ artifacts/
│  ├─ contracts.py
│  ├─ manifests.py
│  └─ provenance.py
│
├─ operations/
│  ├─ contracts.py
│  ├─ registry.py
│  └─ availability.py
│
├─ registries/
├─ common/
├─ text/
│
└─ macrobanks/
   ├─ cbr_file_collector/
   ├─ cbr_forms/
   ├─ cbr_industries/
   ├─ cbr_sors_restoration/
   ├─ escrow/
   └─ frg/
```

Это target taxonomy. Новые directories материализуются по мере появления реальных consumers, а не ради красивого дерева.

---

# 45. `FormatRegistry` и `OperationRegistry` — разные уровни

`FormatRegistry` отвечает:

```text
что за файл
как технически его открыть
какие generic capabilities доступны
```

`OperationRegistry` отвечает:

```text
какой business use case Strategy Box умеет выполнить
```

Связь:

```text
OperationDescriptor.accepted_formats
        ↓
FormatRegistry
        ↓
availability / input validation
        ↓
file picker / API validation
```

Windows/Android не должны держать независимые extension maps.

---

# 46. Windows business registry: split canonical/presentation

Current `OperationSpec` владеет одновременно:

```text
business ID
handler
params
title/group/icon/order
dangerous flag
artifact kinds
AI visibility
```

Target:

## Core `OperationDescriptor`

```text
id
request/result types
semantic summary
capabilities
inputs/outputs
side effects
risk
idempotency
progress/cancellation
artifact kinds
```

## Application `OperationPresentation`

```text
title
localization
group
icon
order
submit label
field display labels
widget hints
```

---

# 47. Android portability

Shared semantics:

```text
operation catalogue projection
scenario catalogue
parameter semantics
jobs/cases
events
artifacts
availability
status vocabulary
presentation/common view models
```

Platform-specific:

```text
Qt widgets
Windows file dialogs
shell/reveal

vs

Android UI
share/open
notifications
mobile permissions
```

Core operations неизменны.

---

# 48. Qt-free orchestration

Current `stratbox-windows.runtime.bootstrap` импортирует Qt `ScenarioCoordinator`. Это делает shared runtime toolkit-dependent.

Target:

```text
application/orchestration/
    ScenarioExecutionService
    JobManager
    ExecutionBackend

presentation/qt_desktop/
    QtScenarioBridge
```

Qt bridge подписывается на application events/signals, но application engine импортируется без PySide6.

---

# 49. `ExecutionBackend`

Отделить:

```text
what to run
```

от:

```text
where to run
```

```python
class ExecutionBackend(Protocol):
    def submit(self, request: OperationExecutionRequest) -> JobRef:
        ...
```

Реализации:

```text
LocalExecutionBackend
Future RemoteNodeExecutionBackend
```

Windows сегодня — local. Android в перспективе чаще будет remote client. Jupyter может вызывать core напрямую, минуя JobManager.

---

# 50. Jupyter не обязан использовать Case/Scenario engine

Для интерактивной работы:

```python
history = build_escrow_history(req)
history.df_long
```

намного естественнее, чем:

```text
create Job
create Case
emit UI Event
wait application runner
```

Поэтому обязательно нужны **два уровня API**:

## Python-native

Rich Python objects/DataFrames.

## Serializable operation boundary

Для UI, remote, automation, AI и future API.

Они используют одну implementation, но разную projection.

---

# 51. DataFrame внутри Result

DataFrame полезен in-process и не должен быть запрещён.

Но он не должен быть единственной transport identity.

Пример:

```text
EscrowHistoryResult
├─ df_long               # in-process convenience
├─ dates
├─ indicators
├─ failures
├─ provenance
└─ optional dataset ArtifactRef
```

Application adapter commits dataset artifact при необходимости.

---

# 52. Уровни стабильности

Полезно разделить:

## Public stable

- documented imports;
- Request/Result;
- operation IDs.

## Public experimental

новые APIs до стабилизации target architecture.

## Internal

private helpers/drivers.

Backward compatibility сейчас не нужна, поэтому migration лучше выполнить резко, а затем сузить public API и начать его защищать.

---

# 53. Dependencies и installation profiles

Разные operations требуют разные capabilities.

Не нужно тащить все optional libs в минимальный install.

Примеры capability groups:

```text
excel
archives-rar
pdf
sors-restoration
xbrl
parquet
```

Profiles:

```text
core-minimal
desktop-full
notebook-banking
specialized extras
```

AppDock exact runtime заранее устанавливает closure. Colab выбирает нужный public extra.

---

# 54. Runtime auto-install запретить

Business operation не должна делать:

```text
pip install
apt install
download binary
```

Причины:

- reproducibility;
- security;
- offline corporate environments;
- AppDock package truth;
- deterministic tests.

Правильный preflight:

```text
DEPENDENCY_MISSING
```

Environment provisioning решает install отдельно.

---

# 55. Operation contract version

Core и clients имеют разные release lifecycle, поэтому полезен явный contract version:

```text
operation_contract_version = 1
```

Descriptor может иметь:

```text
operation_id
operation_version
contract_version
```

Это поможет раньше ловить drift, подобный текущему:

```text
core 0.8.0
windows expects 0.2.1
```

---

# 56. Source fidelity как отдельный contract

Принцип из DBF распространяется шире:

```text
read table for analysis
≠
source-faithful transcode
```

Аналогично:

```text
XLSX semantic extraction
≠
preserve raw workbook

PDF text extraction
≠
preserve PDF

XML parse
≠
preserve raw XML snapshot
```

Raw source artifact и normalized data — разные объекты.

---

# 57. Reuse taxonomy

## L0 — pure primitives

```text
decode
normalize
hash
date math
identity
```

## L1 — format services

```text
DBF reader/transcoder
Excel reader
archive reader
materialization
```

## L2 — source services

```text
CBR discovery
source fetch
snapshot
schema recognition
```

## L3 — domain services

```text
parse escrow
build history
build form data
```

## L4 — operations

```text
escrow.history.export
cbr.forms.raw_export
```

## L5 — scenarios

```text
monthly CBR update
```

## L6 — surface actions

```text
button / dialog / notification / mobile action
```

Сторонний код может входить на любом L0–L4.

---

# 58. Не строить universal mega-API

Не нужна модель, где всё делается только:

```python
stratbox.run("anything", ...)
```

Лучше два пути:

```python
from stratbox.macrobanks.escrow import build_escrow_history
```

и:

```python
from stratbox.operations import get_operation
op = get_operation("escrow.history.build")
```

Domain-native API удобен разработчику; operation registry нужен для discovery/application/automation.

---

# 59. Error model по слоям

## Building block

Может бросать typed exception:

```text
DBFUnsupportedField
ArchiveTraversalDetected
EncodingError
```

## Operation boundary

Преобразует в:

```text
Failure(
    code="DBF_MEMO_SIDECAR_REQUIRED",
    stage="transcode",
    retryable=False,
)
```

## UI

Локализует safe message.

## AppDock

При необходимости регистрирует platform ProblemOccurrence/evidence, не меняя domain truth.

---

# 60. Logging

Core не определяет, куда писать log.

Он использует:

```text
standard logging
structured diagnostics
progress events
```

Caller выбирает sink:

```text
notebook → cell/stream
Windows  → operation log
AppDock  → platform evidence
tests    → capture
```

---

# 61. Secrets и network

Domain request не должен содержать infrastructure credentials.

Плохо:

```text
gateway_password
internal_host
proxy_token
```

Хорошо:

```text
HttpClient already configured by ExecutionContext
```

Neutral network contract:

```python
class HttpClient(Protocol):
    def fetch(self, request: HttpRequest) -> HttpResponse:
        ...
```

Environment может менять route, proxy, gateway, auth и TLS policy без изменения domain code.

Это устраняет current direct coupling public network layer → private package.

---

# 62. FileStore

FileStore остаётся format-agnostic:

```text
paths
bytes/streams
stat/list
copy/move
atomic write
```

Domain не знает физический storage backend. Это одна из сильных сторон current core, её нужно усиливать.

---

# 63. Materialization

Общий materialization layer:

```text
FileStore object
        ↓
materialize
        ↓
local path
        ↓
third-party library
        ↓
commit or abort
```

позволяет убрать индивидуальные temp implementations из DBF/RAR/XBRL/legacy Excel.

---

# 64. Test strategy: DBF primitives

Нужны fixtures:

```text
C
N
F
D
L
I
+
Y
B/O
T/@
deleted rows
M/G/P unsupported
bad header
record length mismatch
truncated DBF
invalid encoding
```

Invariants:

```text
record order preserved
field order preserved
row count preserved
blank != zero
numeric source lexeme preserved
same input → same CSV bytes
same input → same structural manifest
```

---

# 65. Test strategy: `cbr.forms.raw_export`

Unit/integration без live internet:

```text
fake CBR index
fake HTTP
archive fixtures
multiple DBFs
missing publication
404
bad archive
path collision
partial mode
strict mode
cancellation
source hashes
artifact manifest
```

Live source smoke — отдельный test class, не часть deterministic unit suite.

---

# 66. Environment contract matrix

| Environment | Проверяемая граница |
|---|---|
| local Python | default local providers |
| unit tests | fake providers |
| managed desktop | explicit context + UI adapter |
| corporate runtime | private provider certification, отдельно |
| Colab smoke | public package install + public API |
| future remote/Android | serializable operation contract |

Business truth suite остаётся одна.

---

# 67. Private provider certification

Private repository должен проверять только public provider contract:

```text
provider discovery
readiness
FileStore semantics
network semantics
auth/secrets
optional styles
```

Business operation tests остаются в public core.

---

# 68. Public boundary release audit

Перед public release:

```text
build wheel
inspect wheel
import scan
docs scan
manifest scan
source scan
```

Private compliance layer проверяет:

```text
no private package identifiers
no internal hosts
no private paths
no credentials
no environment implementation details
```

---

# 69. Library of building blocks

Чтобы reusable code было легко находить, полезен generated/documented catalog:

```text
Building Blocks
├─ Time
├─ Files
├─ Formats
│  ├─ Excel
│  ├─ CSV
│  ├─ DBF
│  └─ Archives
├─ Sources
│  └─ CBR
├─ Banking
└─ Text
```

У каждой записи:

```text
public import
purpose
inputs
outputs
side effects
dependencies
example
stability
```

Это даёт разработчику реальную discoverability без копирования source.

Machine-readable registry для L0/L1 функций не обязателен; он нужен прежде всего operations.

---

# 70. Full flow: escrow in Windows

```text
User
↓
Windows Scenario UI
↓
OperationPresentation
↓
operation id = escrow.history.export
↓
typed Request
↓
LocalExecutionBackend
↓
ExecutionContext
↓
stratbox operation
↓
generic HttpClient
↓
parse → canonical history → views → export
↓
OperationResult
↓
Artifact commit
↓
Case / Event / Log
↓
Qt projection
↓
AppDock runtime state / platform observability
```

---

# 71. Same escrow in corporate Jupyter

```text
Notebook
↓
import stratbox
↓
typed Request
↓
get_default_context()
↓
generic provider discovery
↓
environment provider
↓
same stratbox operation
↓
same Result
```

Notebook не знает implementation.

---

# 72. Same escrow in Colab

```text
Colab VM
↓
install public stratbox
↓
typed Request
↓
local provider
↓
public network
↓
same operation
↓
same Result
↓
local materialization
↓
Colab download
```

---

# 73. Same DBF converter in another project

```text
Other Python project
↓
dependency on stratbox
↓
from stratbox.formats.dbf import transcode_dbf_to_csv
↓
exact tested implementation
```

AppDock/Windows/scenarios не участвуют.


---

# 74. Idempotency и retries

Operation descriptor должен описывать idempotency.

Примеры:

```text
read-only build        → safe_to_retry
content-addressed export → retry may reproduce same content
destructive cleanup    → requires plan ID, not blindly retryable
```

Поля:

```text
idempotency
retry_policy_hint
```

особенно важны для background, remote и AI execution.

---

# 75. Destructive operations

FRG уже показывает правильную форму:

```text
plan
→ inspect
→ execute
```

Это нужно сделать общим паттерном:

```text
frg.cleanup.plan
frg.cleanup.execute
```

Agent/UI никогда не должен превращать destructive operation в скрытый fallback.

---

# 76. Concurrency

Notebook использует небольшой `ThreadPoolExecutor`. Это execution policy, а не Colab business truth.

Параметры:

```text
max_workers
per-host limit
rate limit
```

могут быть operation/source policy. UI не должен выбирать внутреннее число threads без специальной advanced опции.

---

# 77. Output target

Сегодня многие operations требуют physical `target_dir`.

Для local desktop это удобно. Для remote target лучше постепенно ввести:

```text
OutputTarget
├─ workspace logical path
├─ artifact store
├─ explicit FileStore path
└─ return-only/in-memory
```

Python convenience API может сохранять `out_path`, но remote-ready canonical operation не должна навсегда зависеть от Windows/local filesystem path.

---

# 78. Как определять слой нового кода

Практические вопросы:

### Код знает форму 0409802?

Domain layer.

### Код знает только DBF?

Formats.

### Код знает только HTTP?

Transport/source infrastructure.

### Код знает Qt button?

Windows presentation.

### Код знает case/session/job?

Application layer.

### Код знает AppDock Activation Context?

AppDock adapter/runtime boundary.

### Код знает конкретную corporate infrastructure?

Private provider.

Эта проверка должна стать частью code review.

---

# 79. Что делать с current `base.ioapi`

`base.ioapi` полезен, но format Research уже показывает, что форматный слой вырос.

Target:

```text
base:
    physical/runtime primitives

formats:
    codecs + detection + format registry
```

Так как backward compatibility не нужна, лучше сделать чистое перемещение, а не навсегда держать aliases `base.ioapi.*` → `formats.*`.

---

# 80. DBF — лучший первый migration pilot

Почему:

- current DBF reader уже существует;
- notebook даёт более строгий faithful use case;
- формат важен для CBR;
- есть два различимых contracts;
- можно сделать полный deterministic test corpus;
- downstream `cbr_forms` сразу получает реальный benefit.

Sequence:

```text
1. create stratbox.formats.dbf
2. migrate analytical reader
3. add faithful parser/transcoder
4. remove generic DBF writer
5. add fixtures/tests
6. migrate cbr_forms
7. build cbr.forms.raw_export
8. shrink Colab notebook
```

---

# 81. Generic DBF writer лучше удалить

Current best-effort writer:

- угадывает field types;
- нормализует names;
- выбирает generic widths;
- не гарантирует target schema fidelity.

Это слишком сильный generic promise.

Write DBF допустим только как специализированный exporter под конкретный schema contract.

---

# 82. RAR/materialization migration

```text
1. common materialization
2. archive backend protocol
3. safe extraction
4. capability/dependency preflight
5. remove per-domain subprocess extraction
6. cbr_forms uses archive API
```

---

# 83. Network migration

```text
1. public HttpClient/NetworkPolicy
2. default public RequestsHttpClient
3. provider capability hook
4. remove direct private-package import
5. remove environment flags from domain requests
6. FakeHttpClient tests
```

Один refactor одновременно улучшает:

- public/private boundary;
- tests;
- Colab/Jupyter portability;
- desktop execution;
- future remote mode.

---

# 84. Operation registry migration

```text
1. define core OperationDescriptor
2. define availability
3. define standard outcome/failure
4. register 2–4 pilot operations
5. expose list/get/run
6. Windows reads core registry
7. split presentation overlay
8. retain client-local service ops separately
```

Первые pilots:

```text
escrow.history.build
escrow.history.export
cbr.files.collect
cbr.forms.raw_export
```

---

# 85. Windows migration

P0/P1:

```text
align core version
remove public private-package references
remove environment flags
generic core-operation adapter
safe failure projection
progress bridge
cancellation bridge
```

Затем:

```text
Qt-free application orchestration
shared operation presentation semantics
Android-ready client runtime
```

---

# 86. AppDock migration

Не требуется менять AppDock под каждую business operation.

Strategy Box needs from AppDock:

```text
exact release graph
managed environment
activation
generic readiness
task/process observability
artifact/runtime bridge
future remote execution
```

Operation catalogue остаётся owned by Strategy Box.

---

# 87. Private corporate composition

Target deployment matrix:

```text
Outside Python/Colab
    public stratbox
    local/default providers

Public Windows
    public stratbox
    public surface
    AppDock-managed public runtime

Corporate Jupyter
    public stratbox
    private environment provider

Corporate AppDock
    public stratbox
    public surface
    private environment provider
    private release composition
```

Во всех четырёх случаях банковская implementation одна.

---

# 88. Acceptance criteria: новый business segment

Сегмент считается архитектурно готовым, если:

1. Business algorithm живёт в `stratbox`.
2. Есть curated public Python API.
3. User-facing use case имеет stable operation ID.
4. Есть typed Request/Result.
5. UI отсутствует в core.
6. AppDock types отсутствуют в core.
7. Environment-specific package names отсутствуют в public core/surface.
8. Physical infrastructure не зашита в domain.
9. Required capabilities описаны.
10. Availability можно проверить до run.
11. Errors отличают domain failure от technical exception.
12. Long-running operation имеет structured progress.
13. Cancellation поддерживается там, где безопасно.
14. Raw sources имеют provenance/hash там, где это важно.
15. Output готов к ArtifactRef, а не только path.
16. Lower-level building blocks доступны отдельно.
17. Unit tests не требуют live network.
18. Live-source smoke отделён.
19. Python/Jupyter запускают core напрямую.
20. Colab notebook остаётся thin consumer.
21. Windows вызывает ту же operation.
22. Corporate environment меняет provider, не algorithm.
23. Public source не раскрывает private environment.
24. Android сможет использовать тот же operation contract без Qt.

---

# 89. Acceptance criteria: reusable building block

Для DBF transcoder:

1. Явный public import.
2. Нет AppDock dependency.
3. Нет Windows dependency.
4. Нет notebook global state.
5. Нет `print`.
6. Нет runtime installation.
7. Explicit inputs.
8. Structured result.
9. Deterministic semantics.
10. Unit fixtures.
11. Explicit fidelity policy.
12. Unsupported features fail explicitly.
13. Stream/materialization-friendly.
14. Stable documentation/example.

---

# 90. Recommended implementation roadmap

## P0 — public/private and version hygiene

1. Синхронизировать Windows/AppDock package declarations с current core.
2. Удалить private distribution references из public `pyproject`.
3. Удалить direct import private package из public runtime/network.
4. Удалить environment-specific flag из business API/Windows metadata.
5. Ввести generic provider/network capability.
6. Ввести private external compliance scan.

## P1 — canonical execution contracts

1. `ExecutionContext`.
2. `OperationDescriptor`.
3. `OperationOutcome`.
4. `Failure`.
5. `OperationAvailability`.
6. `ProgressSink`.
7. `CancellationToken`.
8. Artifact/provenance attachment.

## P2 — DBF pilot

1. `stratbox.formats.dbf`.
2. Analytical reader.
3. Faithful parser/transcoder from notebook.
4. DBF corpus/tests.
5. Remove generic writer.
6. Common materialization.

## P3 — archive/source pilot

1. Archive backend.
2. Safe extraction.
3. CBR reporting source descriptors.
4. Source snapshot.
5. Raw export operation.
6. Thin Colab notebook.

## P4 — escrow canonical operation

1. Remove environment flags.
2. Add operation descriptor.
3. Standard provenance.
4. Standard progress.
5. Standard artifact outputs.
6. Windows generic adapter.

## P5 — `cbr_forms`

1. Split fetch/build/export.
2. Remove local-path-only assumptions.
3. Replace print-driven progress.
4. Use common archive/DBF.
5. Typed result.
6. Register stable operations.

## P6 — application portability

1. Qt-free orchestration.
2. Shared operation/scenario projection.
3. ExecutionBackend.
4. Android bridge.
5. Remote backend later.

---

# 91. Что не стоит делать

1. **Не делать notebook центральной реализацией.**
2. **Не делать Windows владельцем business truth.**
3. **Не делать AppDock владельцем banking operation registry.**
4. **Не давать domain environment booleans.**
5. **Не регистрировать каждый helper как operation.**
6. **Не заставлять Jupyter идти через UI Case engine.**
7. **Не копировать private environment naming в public code.**
8. **Не создавать второй DBF converter внутри `cbr_forms`.**
9. **Не делать runtime `pip install`.**
10. **Не возвращать только physical paths.**
11. **Не смешивать source-faithful conversion с analytical parsing.**
12. **Не создавать compatibility aliases после target refactor только ради старого API.**

---

# 92. Target architecture

```text
                         STRATEGY BOX

                ┌──────────────────────┐
                │ Windows / Android    │
                │ Jupyter / Colab      │
                │ Python / Automation  │
                └──────────┬───────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │ Application semantics│
                │ scenarios / jobs     │
                │ cases / presentation │
                └──────────┬───────────┘
                           │ operation ID / typed request
                           ▼
┌──────────────────────────────────────────────────────────┐
│                       STRATBOX CORE                       │
│                                                          │
│  Operations                                               │
│       ↓                                                  │
│  Domain services                                         │
│       ↓                                                  │
│  Source adapters ─────→ Format services                  │
│       ↓                    ↓                             │
│  Provenance          DBF / Excel / archives / CSV ...   │
│       ↓                    ↓                             │
│  Artifacts         Materialization / FileStore           │
│                           ↓                              │
│                Neutral capability contracts              │
└───────────────────────────┬──────────────────────────────┘
                            │
             ┌──────────────┴──────────────┐
             ▼                             ▼
      local/public providers        private provider
             │                             │
             └──────────────┬──────────────┘
                            ▼
                      execution world

AppDock remains outside:
delivery → exact runtime → activation → session/node → platform observability
```

---

# 93. Target DBF flow

```text
                       Other code
                           │
                           ▼
              transcode_dbf_to_csv()
                           ▲
                           │
      ┌────────────────────┼────────────────────┐
      │                    │                    │
 CBR raw export       optional UI op       direct notebook
      │
      ▼
discover CBR publication
      ↓
SourceSnapshot
      ↓
safe archive extraction
      ↓
DBF faithful transcode
      ↓
CSV + manifest
      ↓
Artifact
```

Одна implementation converter обслуживает все consumers.

---

# 94. Target escrow flow

```text
discover sources
       ↓
fetch snapshots
       ↓
parse one source
       ↓
canonical history
       ↓
build views
       ↓
export workbook
       ↓
artifact
```

Developer может остановиться на любом промежуточном уровне.

```text
direct imports:
discover / parse / history / views

operations:
escrow.history.build
escrow.history.export

application:
scenario.cbr.full_update
```

---

# 95. Основные решения в 24 тезисах

1. Единица повторного использования — public function/type, а не copied source block.
2. Единица product execution — canonical operation.
3. Единица user workflow — scenario.
4. UI action ссылается на operation/scenario, а не реализует business code.
5. Applicability определяется capabilities.
6. Business logic живёт в `stratbox`.
7. Windows/Android не копируют business algorithms.
8. AppDock не копирует business operation catalog.
9. Corporate environment меняет provider, а не algorithm.
10. Jupyter и Colab — first-class consumers public Python API.
11. Notebook-specific code — thin adapter.
12. Faithful conversion и analytical parsing — разные contracts.
13. DBF notebook — лучший первый reuse pilot.
14. Escrow — лучший первый canonical operation pilot.
15. `cbr_forms` — следующий pilot декомпозиции notebook-oriented API.
16. FileStore остаётся format-agnostic.
17. Materialization становится общей infrastructure capability.
18. FormatRegistry и OperationRegistry не смешиваются.
19. Operation Result становится artifact/provenance aware.
20. Progress/cancellation/availability/failure — platform-neutral.
21. Public/private boundary нужно очистить немедленно.
22. Windows package graph нужно синхронизировать с core 0.8.0.
23. Qt нужно вывести из shared orchestration до Android.
24. Backward compatibility сейчас не нужна — целевой API можно выпрямить сразу.

---

# 96. Самый полезный следующий implementation pilot

Если выбирать одну задачу, лучше всего проверяющую исследование:

> **Вынести source-faithful DBF parser/transcoder из приложенного notebook в public generic format API `stratbox`, затем собрать поверх него canonical `cbr.forms.raw_export`.**

Почему:

- готовый реальный код;
- ясная декомпозиция по слоям;
- current DBF support уже существует, но имеет другую семантику;
- сразу проверяется direct reuse;
- сразу проверяется Colab;
- сразу проверяется CBR source layer;
- появляется реальный consumer materialization/archive APIs;
- появляется реальный pilot OperationDescriptor;
- Windows сможет получить действие без нового converter;
- сторонний код сможет импортировать converter напрямую.

После этого operation model стоит применить к escrow и далее к `cbr_forms`.

---

# 97. Источники

## Внутренние материалы

1. `stratbox_base_study_current_state_2026-10-06.md`
2. `stratbox-windows_current_state_full_research_2026-10-06.md`
3. `stratbox_plugin_current_state_research_2026-10-06.md` — приватный project research.
4. `AppDock - Базовое описание.docx`
5. `CBR_dbf_to_csv (1).ipynb`
6. `stratbox_file_artifact_layer_research_2026-10-06.md`
7. `stratbox_filestore_file_formats_research_2026-10-07.md`

## `ForestTiger-GH/stratbox`

Проверенный current `main`:

```text
cffe019e17e1b88a58bd9ca277c9a960964b623b
```

Ключевые проверенные areas:

```text
pyproject.toml
src/stratbox/base/runtime.py
src/stratbox/base/net/http.py
src/stratbox/base/net/url.py
src/stratbox/base/ioapi/dbf.py
src/stratbox/base/ioapi/csv.py
src/stratbox/base/ioapi/rar.py
src/stratbox/base/ioapi/archives.py
src/stratbox/macrobanks/cbr_forms/api.py
src/stratbox/macrobanks/cbr_forms/common/runner.py
src/stratbox/macrobanks/cbr_forms/forms/registry.py
src/stratbox/macrobanks/escrow/operations.py
```

Repository:

https://github.com/ForestTiger-GH/stratbox

## `ForestTiger-GH/stratbox-windows`

```text
current main:
959e9c4ce1441124af5111c1e025041714e04d3b
```

Проверены:

```text
pyproject.toml
appdock/manifest.json
operation catalog
execution requests/runner
CBR/escrow handlers
scenario model/registry/runner
runtime bootstrap
workspace file types
artifact model
```

Repository:

https://github.com/ForestTiger-GH/stratbox-windows

## `ForestTiger-GH/AppDock`

```text
current main:
a4d87c643e620e54e04083d4d0b8d867513e7065
```

Проверены current README, activation architecture, observability target/status, task models/runner.

Repository:

https://github.com/ForestTiger-GH/AppDock

## Python Packaging Authority

Entry Points specification:

https://packaging.python.org/en/latest/specifications/entry-points/

Creating and discovering plugins:

https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/

Эти документы подтверждают пригодность package metadata / entry points для neutral discovery отдельно устанавливаемых providers.

## Google Colab

Official FAQ:

https://research.google.com/colaboratory/faq.html

FAQ описывает Colab execution как VM-based runtime с удалением VM после idle period и ограниченным lifetime, что поддерживает модель «Colab = thin disposable consumer package», а не место хранения канонического production code/state.

---

# Заключение

Исходная постановка приводит к одному фундаментальному решению:

> **Business segment Strategy Box нужно проектировать как переносимую библиотечную capability с канонической operation boundary, а не как код конкретной поверхности.**

Тогда Windows является удобной surface этой capability, AppDock — управляемой delivery/runtime средой, corporate Jupyter — consumer того же core с другим provider, Colab — публичным disposable consumer, а сторонний Python-код может импортировать ровно тот нижний building block, который ему нужен.

Это избегает двух крайностей:

```text
каждый notebook / UI / environment
имеет свою копию business logic
```

и:

```text
всё можно делать только через
огромный universal operation engine
```

Целевая модель:

```text
маленькие reusable imports
        +
domain-native Python API
        +
canonical operations
        +
application scenarios
        +
несколько surfaces
```

Один код одновременно становится:

- продуктовой функцией Strategy Box;
- библиотекой аналитика;
- building block разработчика;
- Jupyter workflow;
- Colab workflow;
- будущей remote capability;
- будущей Android capability;
- безопасной operation для automation/AI.

Приложенный DBF→CSV notebook показывает, что переход можно начинать сразу на конкретном полезном коде, а не с абстрактной перестройки ради архитектуры.
