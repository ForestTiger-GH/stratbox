# Strategy Box: будущий контракт корпоративных плагинов — требования, условия, критерии и сертификация

**Research branch:** вторая ветка исследований Strategy Box  
**Дата:** 2026-10-07  
**Статус:** Research Result — архитектурное исследование; код и репозитории не изменялись  
**Основной owner:** `stratbox` core  
**Связанные контуры:** AppDock как внешний deployment/runtime boundary; desktop/mobile surfaces только как consumers  
**Целевой горизонт:** будущая архитектура `stratbox`, без требования обратной совместимости с текущим plugin API  

---

# 0. Краткий вывод

Для будущего Strategy Box корпоративный плагин лучше определять не как «специальный пакет, который core попробует импортировать», а как **доверенное устанавливаемое расширение нейтральных capabilities `stratbox`**, подключаемое через публичный versioned extension protocol.

Главный принцип:

> **`stratbox` знает контракты и capabilities; корпоративный плагин знает конкретную среду. Ни одна сторона не должна знать внутреннее устройство другой сверх публичного контракта.**

Целевая цепочка:

```text
stratbox domain logic
        ↓
public neutral contracts
        ↓
capability registry / extension runtime
        ↓
explicitly activated corporate plugin(s)
        ↓
environment-specific implementations
        ↓
corporate infrastructure
```

В public `stratbox` при этом остаются только:

- versioned plugin API;
- нейтральные Protocol/contracts;
- capability vocabulary;
- discovery/activation runtime;
- строгая error model;
- structured diagnostics/events;
- health/readiness model;
- certification/conformance harness;
- synthetic reference plugins для тестов и документации.

В public `stratbox` **не должны попадать**:

- имена конкретных закрытых distributions;
- прямые imports закрытых packages;
- внутренние endpoint/domain/path names;
- названия корпоративных connector libraries;
- конкретные credential names;
- внутренние gateway rules;
- корпоративные storage topology/details;
- private style identities;
- инструкции установки конкретного закрытого расширения;
- private plugin as an optional dependency of the public core.

Предлагаемый базовый механизм discovery — стандартные Python package entry points, но с versioned group и уникальным plugin ID, например:

```toml
[project.entry-points."stratbox.plugins.v1"]
"example.corporate.infrastructure" = "example_plugin:plugin"
```

Entry point только объявляет установленное расширение. **Наличие пакета в environment не означает разрешение на его активацию.** В managed/production режиме activation должна быть явной: runtime profile / deployment graph выбирает plugin ID и bindings capabilities.

Самый важный переход относительно текущей архитектуры: отказаться от поведения вида «если внешний пакет найден — попробуем, если сломался — тихо откатимся на local». Для production это создаёт ложную работоспособность. В будущем должны существовать два разных факта:

```text
plugin not selected       → штатный builtin/local profile
plugin selected + broken  → readiness failure / startup failure для required capability
```

Точно так же несколько установленных плагинов не должны разрешаться по порядку discovery. Конфликты singleton capabilities — **фатальная диагностируемая ошибка**, пока binding не задан явно.

Корпоративный plugin v1 целесообразно ограничить **environment-specific infrastructure**. В него естественно входят storage, secrets/auth, outbound network policy/transport policy, certificate/proxy policy, reporting themes/templates и health diagnostics. Банковская и макроэкономическая предметная логика, parsers, официальные source schemas, расчёты, Artifact lifecycle и пользовательская orchestration остаются в core или в отдельных будущих типах расширений.

Критерий зрелости плагина — не «импортируется и happy-path работает», а **проходит публичную conformance suite `stratbox`**: package/discovery, compatibility, capability semantics, strict errors, failure injection, data-integrity checks, redaction, health, observability и managed-production certification.

---

# 1. Задача исследования

Нужно сформировать нейтральное описание корпоративного plugin contract, по которому можно:

1. проектировать будущий extension layer `stratbox`;
2. создавать новые закрытые environment adapters без правок business core;
3. проверять существующий частный корпоративный пакет на соответствие целевой архитектуре;
4. подключать несколько разных корпоративных поставок Strategy Box;
5. использовать одну и ту же core business logic в local, managed desktop, host, background и будущих agent/remote execution сценариях;
6. не раскрывать внутреннюю инфраструктуру через public repository;
7. делать совместимость и состояние расширения машинно-проверяемыми;
8. отделить installation trust от runtime capability selection;
9. исключить silent degradation и неоднозначное поведение нескольких extensions;
10. создать автоматическую сертификацию вместо ручного чтения конкретного плагина.

Документ намеренно описывает **будущий целевой контракт**, а не сохраняет текущие interfaces ради compatibility. Для Alta Veritas действует правило: обратная совместимость не требуется; слабую границу лучше заменить сразу на целевую.

---

# 2. Источники и метод

## 2.1. Project sources

Исследованы и сопоставлены:

- актуальный публичный `ForestTiger-GH/stratbox`, `main`;
- актуальный `stratbox` HEAD на момент исследования: `c96ec686fd2be46eb5963c5388a903f5af1af887`;
- `stratbox` package version `0.8.0`;
- исследование текущего состояния core от 2026-10-06;
- приватное исследование текущего environment-specific extension от 2026-10-06;
- предоставленный 2026-10-07 snapshot закрытого корпоративного расширения;
- исследование FileStore и file-format layer от 2026-10-07;
- исследование file/artifact layer;
- исследование observability/errors/logs от 2026-10-07;
- исследование commands/scenarios/cascades;
- базовое описание AppDock.

Private extension использован как **эмпирический test case требований**. Его concrete infrastructure details в настоящий документ не переносятся.

## 2.2. Актуальный public core

Отдельно проверены текущие public extension seams:

```text
stratbox.base.runtime
stratbox.base.filestore
stratbox.base.secrets
stratbox.base.net
stratbox.base.styles.excel
pyproject.toml
```

Текущая архитектура уже содержит правильную основу — domain → neutral contract → runtime provider → environment — однако extension boundary пока неоднородна и недостаточно строгая для нескольких plugins, managed production, remote/background execution и автоматической сертификации.

## 2.3. Внешняя техническая сверка

Использованы как reference:

- Python Packaging User Guide: Entry points specification;
- Python Packaging User Guide: Creating and discovering plugins;
- Python Packaging: PEP 440 / Version Specifiers;
- Python Packaging: `pylock.toml` reproducible environment specification;
- Python Packaging: index-hosted attestations / PEP 740;
- Python `typing.Protocol` / `runtime_checkable`;
- OpenTelemetry Logs Data Model;
- SLSA Build Provenance;
- SPDX 3.x;
- NIST SSDF SP 800-218.

Эти стандарты используются как interoperability и supply-chain reference. Канонический Strategy Box plugin contract должен оставаться собственным, небольшим и предметно ясным.

---

# 3. Что считать корпоративным плагином

## 3.1. Определение

**Corporate Plugin** — отдельно поставляемый доверенный Python distribution, который подключает к `stratbox` одну или несколько реализаций публично определённых infrastructure capabilities и не требует изменения domain code.

Ключевые свойства:

```text
separately distributed
explicitly discoverable
explicitly activatable
versioned contract
capability-declared
health-reporting
observable
certifiable
private implementation
neutral public boundary
```

## 3.2. Это не monkey patch

Plugin не должен:

- менять функции core через monkey patch;
- подменять модули в `sys.modules`;
- править `sys.path`;
- импортировать private/internal modules core;
- зависеть от случайной внутренней структуры repository;
- изменять globals core при import;
- перехватывать поведение через скрытые environment side effects;
- требовать, чтобы domain code знал package name plugin-а.

## 3.3. Это не пользовательское приложение

Infrastructure plugin не владеет:

- GUI;
- scenario chat;
- desktop lifecycle;
- Android UI;
- AppDock Node/Session lifecycle;
- scheduler;
- background job manager;
- user notifications;
- remote execution protocol.

Он библиотечная runtime dependency.

## 3.4. Это не место банковской бизнес-логики

В infrastructure plugin v1 не должны жить:

- парсинг конкретной формы регулятора;
- экономические формулы;
- модели банковских показателей;
- SORS reconstruction logic;
- правила формирования конкретного банковского отчёта;
- официальные public source schemas;
- business operation orchestration.

Это остаётся в `stratbox` domain layer.

## 3.5. Если позже понадобятся внутренние business extensions

Их лучше оформить отдельной extension family, например концептуально:

```text
stratbox.plugins.v1              # environment/infrastructure
stratbox.domain_extensions.v1    # future, separate contract
```

Не следует превращать один plugin API в универсальную систему для инфраструктуры, доменов, UI и workflows одновременно.

---

# 4. Публично-приватная граница

Это один из главных требований проекта.

## 4.1. Что публичный `stratbox` имеет право знать

Core знает только:

```text
plugin protocol version
plugin ID
plugin distribution identity/version
capability IDs
capability contract versions
provider Protocols
safe health state
safe diagnostics/events
configuration schema shape where needed
activation/binding decisions
```

Core **не знает**, какой конкретный backend, connector, gateway, secret store или corporate system скрыт за provider-ом.

## 4.2. Что запрещено публиковать в core

Публичные code/docs/tests/package metadata не должны содержать:

```text
private package names
private repository URLs
internal domains
internal host/share names
private API endpoints
corporate credentials/secret keys
internal Python library names
internal user/account conventions
corporate network topology
private certificate locations
internal storage topology
company-specific support instructions
```

## 4.3. Public examples

Документация использует только synthetic examples:

```text
example.corporate.infrastructure
ExampleStorageProvider
ExampleSecretProvider
https://gateway.example.invalid/
```

## 4.4. Public tests

Core CI использует synthetic reference plugins внутри tests/fixtures или отдельного test distribution.

Public test suite **никогда**:

- не устанавливает private extension;
- не обращается к private infrastructure;
- не проверяет private endpoints;
- не содержит private expected values.

## 4.5. Private CI

Закрытый plugin repository, напротив, импортирует публичный `stratbox.extensions.conformance` и запускает его against private implementation.

Получается правильная зависимость:

```text
public stratbox defines contract + tests
                ↑
private plugin consumes them
```

а не:

```text
public stratbox knows private plugin
```

---

# 5. Почему текущий generic plugin seam нужно переработать

Текущий core уже использует Python entry points — это правильное направление. Проблема находится не в самом механизме discovery, а в семантике вокруг него.

## 5.1. Auto-discovery ≠ activation

Сегодня installed extension фактически может быть подхвачен автоматически. Для корпоративного production лучше разделить:

```text
DISCOVERED
    пакет установлен и объявляет entry point

SELECTED
    runtime profile разрешил использовать plugin

ACTIVATED
    plugin прошёл validation и создан

READY
    required capabilities готовы к работе
```

Это четыре разных состояния.

## 5.2. First discovered provider недопустим как policy

Python Packaging entry points допускают несколько distributions в одной group; обработку конфликтов определяет consumer.

В Strategy Box порядок обнаружения не должен иметь business meaning.

Нельзя:

```text
нашли два storage providers
→ кто попался первым, тот и активен
```

Нужно:

```text
conflict
→ explicit binding required
```

## 5.3. Silent fallback опасен

Если managed production явно требует корпоративную capability, а plugin:

- не импортируется;
- несовместим;
- не может аутентифицироваться;
- backend unavailable;

то автоматический переход к local provider может создать **ложно успешную среду** с другим storage/network/security поведением.

Целевое правило:

```text
not selected        → builtin provider allowed
selected optional   → degraded state allowed only by profile
selected required   → readiness FAIL; no silent substitution
```

## 5.4. Direct package imports запрещены

Core не должен делать:

```python
try:
    import some_private_plugin
except ImportError:
    ...
```

вообще.

Любая environment-specific функция проходит только через public capability contract.

## 5.5. Public package dependency на private distribution запрещена

Public `stratbox` не должен содержать extra или dependency, указывающую конкретный private distribution.

Installation composition принадлежит:

- AppDock package graph;
- private deployment manifest;
- private lock/environment specification;
- operator-managed environment.

---

# 6. Целевая extension architecture

```text
stratbox
│
├─ extensions/
│  ├─ api.py
│  ├─ discovery.py
│  ├─ activation.py
│  ├─ registry.py
│  ├─ models.py
│  ├─ errors.py
│  ├─ events.py
│  ├─ health.py
│  ├─ config.py
│  ├─ capabilities/
│  │  ├─ storage.py
│  │  ├─ secrets.py
│  │  ├─ network.py
│  │  └─ reporting.py
│  └─ conformance/
│     ├─ common.py
│     ├─ storage.py
│     ├─ secrets.py
│     ├─ network.py
│     ├─ reporting.py
│     └─ certification.py
│
├─ base/
├─ sources/
├─ artifacts/
├─ operations/
└─ macrobanks/
```

Точное физическое дерево вторично. Важны обязанности.

---

# 7. Discovery contract

## 7.1. Стандартный механизм

Рекомендуется сохранить PyPA entry points как единственный стандартный discovery path.

Целевая group:

```text
stratbox.plugins.v1
```

Версия протокола кодируется в group name. Это даёт возможность увидеть несовместимый plugin **до его загрузки**.

Пример private `pyproject.toml`:

```toml
[project.entry-points."stratbox.plugins.v1"]
"example.corporate.infrastructure" = "example_plugin.entry:plugin"
```

## 7.2. Entry point name

`name` является стабильным `plugin_id`.

Требования:

- lowercase;
- ASCII;
- dotted namespace предпочтителен;
- не зависит от Python import path;
- не зависит от distribution file name;
- не меняется при рефакторинге modules.

Пример:

```text
example.corporate.infrastructure
```

## 7.3. Entry point function

Функция `plugin()`:

- импортируется без I/O side effects;
- не подключается к сети;
- не читает секреты;
- не создаёт каталоги;
- не запускает threads;
- не меняет глобальное состояние core;
- возвращает `PluginDescriptor` / object implementing public `StratboxPlugin` protocol.

## 7.4. Discovery result

До activation core должен уметь показать:

```text
plugin_id
distribution_name
distribution_version
entry_point_group
entry_point_value
api_version
discovery_status
```

Без чтения private configuration и без соединения с infrastructure.

---

# 8. Version model

Нужны три независимые версии.

## 8.1. Distribution version

Обычная PEP 440 version private package:

```text
1.4.0
1.4.1
2.0.0
```

Это release identity.

## 8.2. Plugin API version

Например:

```text
stratbox.plugins.v1
```

Это wire/interface contract между core и plugin.

В рамках текущего правила проекта core может поддерживать **только актуальный API major**. Legacy compatibility adapters не нужны.

## 8.3. Capability contract version

Отдельные capabilities желательно версионировать самостоятельно:

```text
storage.v2
secrets.v1
network_policy.v1
reporting_theme.v1
```

Plugin descriptor заявляет конкретные contracts.

## 8.4. Core package compatibility

Plugin может дополнительно объявить PEP 440 specifier для core:

```text
requires_stratbox = ">=0.9,<0.10"
```

Но managed deployment всё равно должен фиксировать exact package versions/hashes.

Полезное разделение:

```text
contract compatibility → version ranges / API versions
reproducible deployment → exact lock + artifact hashes
```

## 8.5. Никаких compatibility synonyms

В новом API не следует поддерживать одновременно:

```text
filestore / store / file_store
secrets / secret_provider
old dict / new object
```

Один versioned contract — одна форма.

---

# 9. Plugin descriptor

Концептуальный public model:

```python
@dataclass(frozen=True)
class PluginDescriptor:
    plugin_id: str
    api_version: int
    requires_stratbox: str
    capabilities: tuple[CapabilityDeclaration, ...]
    config_schema_version: int | None = None
    effects: frozenset[str] = frozenset()
```

Distribution name/version берутся из installed package metadata, а не дублируются вручную как второй source of truth.

## 9.1. Capability declaration

```python
@dataclass(frozen=True)
class CapabilityDeclaration:
    capability_id: str
    contract_version: int
    instance_name: str = "default"
    required_config: bool = False
    concurrency: str = "thread_safe"
    optional_features: frozenset[str] = frozenset()
```

## 9.2. Declared effects

Полезно декларировать side-effect classes:

```text
network.outbound
storage.read
storage.write
storage.destructive
secrets.read
process.spawn
certificate.access
```

Это не sandbox: in-process Python plugin всё равно имеет права процесса. Но effects дают:

- transparency;
- policy checks;
- audit metadata;
- security review scope;
- certification profile selection.

---

# 10. Activation lifecycle

Целевая state machine:

```text
DISCOVERED
   ↓ validate static metadata
COMPATIBLE
   ↓ selected by runtime profile
SELECTED
   ↓ plugin object loaded
LOADED
   ↓ activate(context)
ACTIVATED
   ↓ required health checks
READY
```

Failure branches:

```text
INCOMPATIBLE
LOAD_FAILED
CONFIG_REQUIRED
AUTH_REQUIRED
DEGRADED
NOT_READY
```

## 10.1. No hot install

Plugin installation/update — задача package/deployment layer, не core runtime.

`stratbox` не должен:

- `pip install` dependencies at runtime;
- update plugin packages;
- fetch private wheels itself.

## 10.2. Restart model

Для v1 достаточно:

> изменение набора plugin distributions или plugin version требует нового process/runtime activation.

Hot reload только усложнит correctness, connection state и security.

## 10.3. Shutdown

Если plugin/provider держит sessions/resources, он предоставляет lifecycle close/shutdown contract. Shutdown errors регистрируются как diagnostics и не маскируют основной operation outcome.

---

# 11. Explicit activation и profiles

Discovery отвечает на вопрос **что установлено**. Runtime profile — **что разрешено использовать**.

Пример концептуальной конфигурации:

```yaml
extensions:
  enabled:
    - example.corporate.infrastructure

  bindings:
    secrets.default: example.corporate.infrastructure
    storage.workspace: example.corporate.infrastructure
    network.default: example.corporate.infrastructure
```

Конкретный формат YAML/JSON/TOML вторичен.

## 11.1. Local profile

```text
plugins = []
builtin local capabilities active
```

## 11.2. Managed corporate profile

```text
selected plugin IDs explicit
required capability bindings explicit
strict compatibility
strict readiness
no silent local fallback
```

## 11.3. Developer profile

Может разрешать explicit degraded/fallback поведение для разработки, но оно должно быть видно в runtime diagnostics.

---

# 12. Несколько plugins одновременно

Будущий contract должен считать multi-plugin environment нормальным случаем, даже если первая production поставка использует один plugin.

## 12.1. Plugin identity conflicts

Два distributions с одним `plugin_id` → blocking error.

```text
PLUGIN_DUPLICATE_ID
```

Никаких «выберем новую версию» автоматически.

## 12.2. Singleton capability conflicts

Например, два кандидата на:

```text
secrets.default
network.default
storage.workspace
```

Без explicit binding → blocking error.

## 12.3. Multi-contribution capabilities

Некоторые addons могут быть множественными:

```text
reporting themes
templates
format readers
```

Для них core определяет merge semantics.

Plugin не может сам объявить «мой объект имеет приоритет».

## 12.4. Namespace collision

Addon IDs должны быть namespaced или конфликтовать явно. Нельзя тихо перезаписывать чужой preset/template.

## 12.5. Default selection

Plugin может объявить recommendation, но global default выбирает runtime/user profile. Особенно важно при нескольких plugins.

---

# 13. Capability taxonomy v1

Не нужно делать plugin API каталогом всего на свете. Для первого целевого контракта достаточно нескольких реальных extension seams.

## 13.1. `storage`

Environment-specific physical file/storage access.

Core owns:

- `FileStore` semantics;
- `StoragePath`;
- `FileStat` / `FileEntry`;
- error taxonomy;
- capability model;
- artifact layer above storage.

Plugin owns:

- connection/auth to backend;
- path translation where required;
- actual I/O;
- backend-specific performance optimization;
- safe implementation of declared capabilities.

Plugin **не владеет** Artifact IDs, provenance graph, SourceSnapshot semantics или business workspace policy.

## 13.2. `secrets`

Environment-specific secret resolution / authentication bootstrap.

Core owns safe contract and error semantics. Plugin owns integration with concrete secret/auth system.

## 13.3. `network_policy`

Environment-specific outbound routing/policy.

Это заменяет любые прямые private imports из `stratbox.base.net`.

В v1 capability может:

- normalize/transform outbound request destination;
- declare proxy/TLS requirements;
- attach safe policy metadata;
- report access readiness.

Domain code продолжает знать original source identity, а infrastructure layer решает physical route.

## 13.4. `http_transport` — только если реально понадобится

Если одной policy недостаточно из-за custom TLS/session/auth transport, вводится отдельный neutral transport capability. Не стоит заранее переносить весь HTTP client в plugin.

## 13.5. `reporting_theme`

Passive reporting contribution:

- fonts;
- palettes;
- number formats;
- semantic block styles;
- chart theme;
- templates where generic reporting engine это поддерживает.

Business report composition остаётся core/domain responsibility.

## 13.6. `health`

Health/readiness не отдельная optional business capability, а обязательная cross-cutting способность каждого active plugin.

---

# 14. FileStore contract для plugin providers

Связанные исследования показывают, что идеальный FileStore должен быть небольшим, format-agnostic и capability-aware.

Концептуально:

```python
class FileStore(Protocol):
    def open_read(self, path: StoragePath) -> BinaryIO: ...
    def open_write(self, path: StoragePath, *, mode: WriteMode = ...) -> BinaryIO: ...

    def stat(self, path: StoragePath) -> FileStat: ...
    def list(self, path: StoragePath) -> Iterable[FileEntry]: ...

    def mkdir(self, path: StoragePath, *, parents: bool = False) -> None: ...
    def delete(self, path: StoragePath, *, recursive: bool = False) -> None: ...
    def copy(self, src: StoragePath, dst: StoragePath) -> None: ...
    def move(self, src: StoragePath, dst: StoragePath) -> None: ...

    def capabilities(self) -> StorageCapabilities: ...
```

## 14.1. Storage capabilities

Пример:

```text
streaming_read
streaming_write
seek_read
range_read
atomic_replace
atomic_move
conditional_write
server_side_copy
native_checksum
native_directories
case_sensitive
```

Core не должен притворяться, что любой backend — POSIX filesystem.

## 14.2. Capability honesty

Если backend не умеет atomic move, provider не может объявить `atomic_move=True` потому что реализовал `copy + delete`.

Fallback, меняющий гарантию, **не является прозрачным fallback**.

## 14.3. Destructive semantics

Для `move/delete/recursive delete`:

- success означает доказанный success;
- partial failure не считается success;
- ignored exceptions запрещены;
- destructive fallback обязан либо сохранять contract, либо возвращать `UnsupportedOperation`/`PartialFailure`;
- source нельзя удалять после неполностью проверенного copy;
- root/namespace guards обязательны, если backend допускает destructive operations.

## 14.4. Streaming

Если `open_read/open_write` объявлены как streams, conformance suite проверяет, что они не обязаны держать весь объект в памяти. Если backend этого не умеет, capability profile обязан отражать ограничение или core contract должен давать отдельный buffered mode.

## 14.5. Transactional write

Для artifact-producing operations желательно иметь temp/draft → commit semantics выше FileStore. Plugin storage provider должен дать необходимые primitives или честно объявить их отсутствие.

---

# 15. SecretProvider contract

Текущий минимальный `str | None` contract слишком слаб для managed runtime.

Нужно различать:

```text
secret resolved
secret not configured
authentication required
permission denied
secret backend unavailable
configuration invalid
secret intentionally absent
```

## 15.1. Typed outcome

Возможная форма:

```python
SecretResolution = SecretValue | SecretMissing
```

а operational failures идут typed exception/error model.

`SecretValue` должен иметь redacted `repr` и никогда автоматически не сериализоваться в diagnostics.

## 15.2. Provenance without value

Допустимо уметь ответить:

```text
source = managed_secret_store
source = environment
source = runtime_config
```

без раскрытия значения.

## 15.3. Interactive prompts

Plugin provider не должен самостоятельно вызывать terminal prompt в managed/background/remote execution.

Вместо этого:

```text
AUTHENTICATION_REQUIRED
```

и safe action metadata возвращаются caller-у.

UI/AppDock уже решает, как инициировать credential flow.

## 15.4. Strict mode

Если production policy требует определённый secret backend, его outage не должен автоматически переводить систему на менее защищённый источник.

Fallback policy должна быть явной runtime configuration.

---

# 16. Network contract

Network environment policy — отдельная capability, а не utility с private import.

## 16.1. Domain invariant

Domain/source layer знает:

```text
source_id
canonical requested URL
request semantics
expected content
```

Plugin знает:

```text
physical route
proxy/gateway policy
certificates/TLS policy
environment authentication
```

## 16.2. Deterministic transformation

Одинаковый request + одинаковая configuration должны давать одинаковую policy decision.

## 16.3. Safe diagnostics

Можно логировать:

```text
policy applied = true
route class = gateway/proxy/direct
result = allowed/denied/unavailable
```

Нельзя без необходимости логировать private full URLs, tokens, credentials и sensitive query parameters.

## 16.4. Deny is explicit

Policy denial ≠ network failure.

Нужны разные errors:

```text
POLICY_DENIED
NETWORK_UNAVAILABLE
AUTH_REQUIRED
TLS_FAILURE
TIMEOUT
```

---

# 17. Reporting addon contract

Corporate reporting layer — хороший пример **passive addon**, а не service provider.

## 17.1. Core owns semantics

Core/domain описывает:

```text
title
header
value
percentage
warning
forecast
source note
```

Plugin theme сопоставляет semantic roles с visual tokens.

## 17.2. No hardcoded business report

Plugin не должен знать, какие банки, показатели или формы находятся в конкретной таблице.

## 17.3. Stable IDs

Preset/theme IDs должны быть stable и namespaced.

## 17.4. Default

Plugin может объявить `recommended_default`, но runtime profile/user selection определяет активный theme.

---

# 18. Error model

Это одна из самых важных частей будущего контракта.

## 18.1. Ошибка не может превращаться в пустой успешный результат

Запрещены паттерны:

```text
network error → []
permission denied → False
backend unavailable → None
partial delete → success
unsupported operation → silently skipped
```

## 18.2. Общая taxonomy

Минимальный generic набор:

```text
NotFound
AlreadyExists
InvalidPath
PermissionDenied
AuthenticationRequired
AuthenticationFailed
ConfigurationError
Unavailable
Timeout
UnsupportedOperation
Conflict
IntegrityError
PartialFailure
PolicyDenied
DependencyUnavailable
CompatibilityError
InternalProviderError
```

Capability-specific errors могут уточнять эту модель.

## 18.3. Error record

На extension boundary каждая structured problem имеет:

```text
code                  stable machine ID
category              generic class
message_safe          safe user/operator text
plugin_id             origin
capability_id         origin capability
operation             safe operation name
retryable             yes/no/unknown
action_required       optional
correlation_id        run linkage
cause_ref             technical evidence reference where available
```

## 18.4. Raw exception

Python exception — technical cause/evidence. Он не становится public result напрямую.

## 18.5. Provider wrapping

Core extension runtime должен перехватывать unexpected plugin exceptions и превращать их в:

```text
InternalProviderError
```

с сохранением traceback в technical diagnostics/evidence layer, где это разрешено.

---

# 19. Outcome model

Для plugin operations и health checks полезно использовать те же terminal semantics, что и общий Strategy Box observability:

```text
SUCCESS
PARTIAL
CANCELLED
FAILURE
UNKNOWN
```

Особенно важно `UNKNOWN`: при network/process crash нельзя автоматически объявлять destructive remote action failed, если side effect мог успеть произойти.

---

# 20. Observability contract

Plugin не должен `print()` diagnostics как primary mechanism.

Core предоставляет `EventSink` / diagnostic emitter.

## 20.1. Structured event

Минимальные поля:

```text
timestamp
severity
event_name
plugin_id
plugin_version
plugin_api_version
capability_id
operation
correlation_id / run_id
attempt_id optional
duration_ms optional
outcome
error_code optional
retry_count optional
fallback_used optional
attributes safe map
```

## 20.2. OpenTelemetry compatibility

Внутренний event model Strategy Box не обязан зависеть от OpenTelemetry package. Но поля должны естественно маппиться на OTel log/event model:

- timestamp;
- severity;
- event name;
- resource/component identity;
- trace/span/correlation IDs;
- attributes;
- exception/evidence metadata.

## 20.3. Event classes

Нужно разделять:

```text
lifecycle event
health event
operation event
retry/fallback event
configuration event
security/audit-relevant event
technical debug log
```

## 20.4. Redaction

Обязательная policy:

- secret values никогда;
- auth tokens никогда;
- passwords никогда;
- sensitive query params никогда;
- полный local/private path — только если policy разрешает;
- user names/hosts — только safe classification;
- exception text проходит sanitization перед user-facing surface.

## 20.5. Fallback observable

Если provider переключился между эквивалентными internal transports, это должно быть видно diagnostics/metrics.

Но раскрывать private backend name наружу не обязательно. Достаточно stable plugin-local adapter class/route code с redaction policy.

---

# 21. Health и readiness

Debug dump и health — разные вещи.

## 21.1. Liveness

Plugin package и object могут быть загружены.

## 21.2. Readiness

Required capabilities реально способны выполнить ожидаемую работу.

## 21.3. Health levels

```text
READY
DEGRADED
NEEDS_ACTION
NOT_READY
UNKNOWN
```

## 21.4. Check result

```python
@dataclass(frozen=True)
class HealthCheckResult:
    check_id: str
    status: HealthStatus
    code: str
    message_safe: str
    capability_id: str | None
    action: ActionHint | None
    duration_ms: int | None
```

## 21.5. Check depths

### Static

Без внешнего I/O:

```text
entry point loaded
API compatible
config schema valid
required dependency importable
capability object conforms structurally
```

### Connectivity

Неразрушающая связь с backend:

```text
auth/session possible
namespace reachable
network route available
```

### Roundtrip certification

Изолированная test area:

```text
write
read
stat/list
rename/move if declared
cleanup
unicode
integrity verify
```

Roundtrip — не обычный startup check, а explicit certification/deep diagnostic action.

## 21.6. Health privacy

Health report показывает:

```text
storage.workspace READY
secrets.default READY
network.default DEGRADED
```

а не internal host/share/user/endpoint identities.

---

# 22. Configuration contract

## 22.1. Namespaced config

Plugin-specific keys находятся внутри plugin namespace.

Core не знает semantics ключей; он лишь хранит/передаёт typed configuration where applicable.

## 22.2. Determinism

Production configuration должна иметь однозначный source/provenance.

Широкий implicit search по current working directory, parents и случайным files нежелателен в managed production.

## 22.3. Schema

Plugin может объявить machine-readable schema:

```text
field id
type
required
sensitive
restart_required
allowed_values
safe_description
```

## 22.4. Unknown keys

Strict production mode → unknown keys являются configuration error.

Это ловит typos и stale configuration.

## 22.5. Secrets in config

В schema поле может быть `sensitive`, но values не должны автоматически попадать в descriptor/health/log serialization.

## 22.6. Config provenance

Полезно хранить только safe provenance:

```text
managed profile
environment
secret provider
explicit file
```

---

# 23. Concurrency and execution model

Future Strategy Box предполагает background jobs и несколько одновременных runs. Plugin contract обязан определить concurrency раньше, чем это станет аварией.

## 23.1. Provider declaration

```text
THREAD_SAFE
SERIALIZED
PROCESS_LOCAL
```

## 23.2. THREAD_SAFE

Provider допускает одновременные calls.

## 23.3. SERIALIZED

Extension runtime должен сериализовать обращения к provider instance.

## 23.4. PROCESS_LOCAL

Provider создаётся отдельно в каждом process и не должен ожидать shared in-memory state между worker processes.

## 23.5. Async

Для v1 лучше выбрать один sync contract, соответствующий текущему `stratbox`.

Если async потребуется реально, создать explicit async capability contract/version. Одновременная неформальная поддержка sync+async быстро делает API двусмысленным.

---

# 24. Security model

## 24.1. Plugin is trusted code

In-process Python extension выполняется с правами Strategy Box process.

Следовательно:

> plugin discovery/activation — security boundary, а не просто feature toggle.

Если требуется подключать недоверенный third-party code, нужен отдельный out-of-process/sandbox contract. Это другая архитектура.

## 24.2. Explicit allowlist

Managed production активирует только явно выбранные plugin IDs/distributions.

Installed ≠ trusted/active.

## 24.3. Least privilege

Providers должны по возможности использовать:

- ограниченные storage roots;
- scoped credentials;
- read-only credentials для read-only capabilities;
- минимальные network destinations;
- отдельные destructive permissions.

## 24.4. No runtime dependency installation

Plugin не выполняет dynamic `pip install` и не загружает executable code при обычном runtime.

## 24.5. Shell/process execution

Если plugin требует subprocess, effect должен быть declared и security review должен это видеть.

`shell=True` для внешних/user-controlled arguments запрещён без отдельного обоснования и hardening.

## 24.6. Path safety

Provider обязан защищать namespace escape / root destructive actions согласно capability contract.

## 24.7. Secret hygiene

- no plaintext logs;
- no repr;
- no accidental JSON serialization;
- no long-lived disk cache без explicit secure store;
- no exception messages with secret value.

---

# 25. Supply-chain requirements

Corporate plugin является privileged code, поэтому package provenance важнее обычной utility library.

## 25.1. Wheel-first production

Production delivery должна использовать built wheel, а не editable checkout.

## 25.2. Reproducible dependency set

Managed deployment фиксирует exact versions и hashes. Современный PyPA `pylock.toml` может служить стандартной формой reproducible environment, если выбранный installer/tooling его поддерживает.

## 25.3. Artifact hash

Wheel hash хранится в deployment provenance.

## 25.4. Build provenance

При зрелом CI желательно выдавать SLSA-compatible provenance или эквивалентную attestation, связывающую wheel с source revision и build process.

## 25.5. Package attestations

Если private package index поддерживает attestations, полезно применять модель, аналогичную PyPA index-hosted attestations / PEP 740.

## 25.6. SBOM

Release может публиковать SPDX SBOM с:

- distribution;
- direct/transitive dependencies;
- versions;
- hashes;
- licenses where applicable;
- supplier/build provenance.

## 25.7. No generated junk

Source distribution/repository не должен включать accidental generated metadata/cache/runtime files.

## 25.8. Vulnerability process

Plugin project должен иметь понятный процесс dependency/security updates. NIST SSDF пригоден как high-level reference, а не как тяжёлая обязательная bureaucracy.

---

# 26. Package quality requirements

Production plugin package обязан:

- иметь `pyproject.toml`;
- иметь один authoritative version source;
- корректно строить wheel;
- устанавливаться в clean environment;
- объявлять `Requires-Python`;
- объявлять runtime dependencies;
- не зависеть от source-tree-only files;
- не требовать editable install;
- не содержать stale duplicate implementations;
- не включать generated `.egg-info` в source tree как maintained source;
- не содержать dead compatibility code ради старых API;
- иметь test extras / dev dependency group;
- иметь private deployment docs отдельно от public core docs.

---

# 27. Import and dependency boundary

## 27.1. Allowed imports from core

Private plugin импортирует только documented public extension API и capability models:

```text
stratbox.extensions.*
stratbox.base.<documented public contracts>
```

## 27.2. Forbidden imports

Запрещена зависимость на:

```text
stratbox._internal
private helpers
implementation modules not marked public
domain internals
UI/runtime surface packages
```

## 27.3. No reverse import

Core не импортирует plugin package по имени.

## 27.4. Structural protocols

Python `Protocol` удобен для static typing, но `runtime_checkable` проверяет только наличие атрибутов, а не signature/type semantics. Поэтому certification tests остаются обязательными: `isinstance(provider, Protocol)` недостаточно для доказательства conformance.

---

# 28. Capability binding rules

Нужна единая таблица cardinality/merge semantics, принадлежащая core.

| Capability | Type | Cardinality | Selection |
|---|---|---:|---|
| `storage.workspace` | service | 1 active | explicit or builtin |
| `storage.artifacts` | service | 0..1 active | explicit/default |
| `secrets.default` | service | 1 active | explicit or builtin |
| `network.default` | policy/service | 0..1 | explicit |
| `reporting.theme` | addon | many | merged registry |
| `health` | cross-cutting | every active plugin | mandatory |

Future capabilities получают свою policy отдельно.

---

# 29. Capability requirements vs operations

Domain operation должна зависеть от generic capability:

```text
requires:
  storage.workspace
  network.default
```

а не:

```text
requires:
  example.corporate.infrastructure
```

Это позволяет:

- local execution;
- alternative corporate providers;
- test doubles;
- host execution;
- future Linux environment;
- consistent operation discovery.

---

# 30. Fallback policy

Fallback — одна из самых опасных частей infrastructure adapters.

## 30.1. Semantically equivalent fallback

Допустим, если:

- результат имеет тот же contract;
- integrity guarantees не слабее;
- security guarantees не слабее;
- caller outcome остаётся корректным;
- fallback observable.

## 30.2. Semantically weaker fallback

Нельзя скрывать.

Пример:

```text
atomic move unavailable
→ copy + delete
```

Это уже другая семантика.

Варианты:

- capability `atomic_move=False` и core использует другой algorithm;
- explicit transactional higher-level operation;
- `UnsupportedOperation`.

## 30.3. Suppressed errors

`except Exception: pass` недопустим для operations, влияющих на correctness/state.

Best-effort разрешён только если contract прямо называет действие best-effort и diagnostics фиксируют failure.

---

# 31. Data-integrity requirements

Особенно важны для storage providers.

## 31.1. Write success

Успешный `write/commit` означает, что caller может затем прочитать именно опубликованный object в рамках гарантий backend-а.

## 31.2. Partial write

Partial output не становится committed artifact.

## 31.3. Move/copy

Если операция имитируется несколькими steps, source удаляется только после доказанной успешности destination согласно contract.

## 31.4. Checksum

Если provider объявляет native checksum, conformance suite проверяет semantics. Higher layer всё равно может считать cryptographic digest самостоятельно.

## 31.5. Unicode/path edge cases

Certification включает:

- Unicode/Cyrillic names;
- spaces;
- deep paths within supported limits;
- separators/normalization;
- root guards;
- duplicate names;
- case sensitivity behavior where relevant.

---

# 32. Certification architecture

Главная практическая ценность будущего контракта — автоматическая проверяемость.

Предлагается public package:

```text
stratbox.extensions.conformance
```

с reusable test harness.

## 32.1. Certification profiles

### `core-contract`

Обязателен каждому plugin.

Проверяет:

- discovery;
- identity;
- API version;
- descriptor;
- activation;
- error/event model;
- health;
- redaction;
- shutdown.

### `capability-<name>`

Например:

```text
capability-storage
capability-secrets
capability-network
capability-reporting
```

### `managed-production`

Дополнительно:

- strict activation;
- no silent fallback;
- package provenance;
- deep health;
- failure injection;
- concurrency;
- clean wheel install;
- lock/hash checks where available.

## 32.2. Certification result

```python
@dataclass(frozen=True)
class CertificationReport:
    plugin_id: str
    distribution: str
    distribution_version: str
    plugin_api_version: int
    stratbox_version: str
    profile: str
    status: str              # PASS / FAIL / CONDITIONAL
    checks: tuple[CheckResult, ...]
    blocking_failures: tuple[str, ...]
    warnings: tuple[str, ...]
    generated_at: datetime
```

No secrets/private infrastructure details in default report.

## 32.3. JSON output

CLI/programmatic certification должен уметь вернуть stable JSON report для AppDock/CI/support.

---

# 33. Core conformance checklist

Ниже — минимальный blocking checklist для любого plugin.

| ID | Requirement | Level |
|---|---|---|
| ARCH-001 | Core imports plugin only through versioned entry point | MUST |
| ARCH-002 | Plugin imports only documented public core API | MUST |
| ARCH-003 | No monkey patch / `sys.path` mutation | MUST |
| ARCH-004 | Import has no external I/O side effects | MUST |
| ARCH-005 | Domain/business logic is outside infrastructure plugin | MUST |
| PRIV-001 | Public core contains no private implementation details | MUST |
| PRIV-002 | Public core has no dependency on named private distribution | MUST |
| DISC-001 | Stable unique plugin ID | MUST |
| DISC-002 | Versioned entry-point group | MUST |
| DISC-003 | Duplicate ID detected as error | MUST |
| ACT-001 | Installed plugin is not auto-authorized | MUST |
| ACT-002 | Managed activation is explicit | MUST |
| ACT-003 | Required plugin failure cannot silently switch provider | MUST |
| VER-001 | Plugin API version checked before activation | MUST |
| VER-002 | Core compatibility spec checked | MUST |
| VER-003 | No legacy alias compatibility in new API | MUST |
| CAP-001 | Capabilities declared before activation | MUST |
| CAP-002 | Conflicting singleton bindings fail explicitly | MUST |
| CAP-003 | Optional features are truthfully declared | MUST |
| ERR-001 | Errors never masquerade as successful empty results | MUST |
| ERR-002 | Partial failure represented explicitly | MUST |
| ERR-003 | Unexpected exception wrapped into stable provider error | MUST |
| OBS-001 | Structured event sink used for diagnostics | MUST |
| OBS-002 | Secret redaction tests pass | MUST |
| OBS-003 | Fallback/retry observable | MUST |
| HLT-001 | Plugin exposes static health | MUST |
| HLT-002 | Active external capability exposes readiness | MUST |
| HLT-003 | Health output is safe/redacted | MUST |
| CFG-001 | Production configuration is deterministic | MUST |
| CFG-002 | Sensitive fields marked and redacted | MUST |
| CFG-003 | Unknown keys rejected in strict mode | SHOULD |
| SEC-001 | Runtime dynamic package install forbidden | MUST |
| SEC-002 | Declared privileged side effects | MUST |
| SEC-003 | Destructive operations preserve contract guarantees | MUST |
| PKG-001 | Clean wheel build succeeds | MUST |
| PKG-002 | Clean wheel install succeeds | MUST |
| PKG-003 | Runtime assets are present in wheel | MUST |
| PKG-004 | No source-tree accidental dependency | MUST |
| TST-001 | Public conformance suite passes | MUST |
| TST-002 | Capability-specific fault injection passes | MUST |
| TST-003 | Production backend smoke exists privately | MUST |
| TST-004 | Concurrency behavior tested | SHOULD |
| SUP-001 | Exact deployment artifact identity/hash recorded | MUST for managed production |
| SUP-002 | Reproducible dependency set | SHOULD |
| SUP-003 | SBOM generated | SHOULD |
| SUP-004 | Build provenance/attestation | SHOULD |

---

# 34. Storage conformance checklist

| ID | Check | Blocking when feature declared |
|---|---|---|
| STO-001 | write → read byte equality | yes |
| STO-002 | empty file | yes |
| STO-003 | Unicode filename/path | yes |
| STO-004 | exists semantics for missing path | yes |
| STO-005 | empty directory ≠ unavailable backend | yes |
| STO-006 | permission denied distinct from not found | yes |
| STO-007 | stat fields coherent | yes |
| STO-008 | list empty directory returns success empty | yes |
| STO-009 | list backend outage raises `Unavailable` | yes |
| STO-010 | recursive mkdir semantics | yes |
| STO-011 | file delete semantics | yes |
| STO-012 | directory delete semantics | yes |
| STO-013 | recursive delete reports partial failure | yes |
| STO-014 | root destructive guard | yes |
| STO-015 | move file preserves content | yes |
| STO-016 | move directory does not delete source after partial copy | yes |
| STO-017 | `atomic_move` claim verified | yes |
| STO-018 | interrupted write does not publish committed artifact | yes where supported |
| STO-019 | stream behavior checked | yes if declared |
| STO-020 | checksum semantics | yes if declared |
| STO-021 | capability profile stable after activation | yes |
| STO-022 | backend timeout mapped correctly | yes |
| STO-023 | authentication failure mapped correctly | yes |
| STO-024 | retry/fallback emits structured event | yes |
| STO-025 | cleanup certification area | yes |

---

# 35. Secrets conformance checklist

| ID | Check |
|---|---|
| SECRES-001 | Existing secret resolves |
| SECRES-002 | Missing secret distinguishable from backend outage |
| SECRES-003 | AuthenticationRequired distinguishable |
| SECRES-004 | PermissionDenied distinguishable |
| SECRES-005 | Secret value absent from `repr` |
| SECRES-006 | Secret absent from logs/events/health |
| SECRES-007 | Secret absent from exception message after sanitization |
| SECRES-008 | Provenance may be reported without value |
| SECRES-009 | Managed runtime does not block on terminal prompt |
| SECRES-010 | Strict backend policy does not silently downgrade |

---

# 36. Network conformance checklist

| ID | Check |
|---|---|
| NET-001 | Canonical source identity preserved |
| NET-002 | Policy transformation deterministic |
| NET-003 | Query/fragment semantics preserved where contract requires |
| NET-004 | PolicyDenied distinct from connectivity failure |
| NET-005 | Timeout distinct from auth failure |
| NET-006 | TLS/certificate failure distinct |
| NET-007 | Sensitive URL/query redacted |
| NET-008 | Health can test route without leaking endpoint details |
| NET-009 | No direct private package import from core |
| NET-010 | Domain parsers do not know physical gateway route |

---

# 37. Reporting addon conformance checklist

| ID | Check |
|---|---|
| REP-001 | Theme loads through generic addon contract |
| REP-002 | IDs stable and collision-safe |
| REP-003 | Addon does not contain domain calculation logic |
| REP-004 | Semantic role mapping complete |
| REP-005 | Missing optional font/resource fails predictably |
| REP-006 | Global default not silently hijacked in multi-plugin environment |
| REP-007 | Registry merge deterministic |

---

# 38. Fault-injection matrix

Happy-path smoke недостаточен. Adapter code особенно нуждается в negative tests.

Обязательные fault scenarios:

```text
missing dependency
bad config
expired credential
auth backend unavailable
permission denied
network timeout
connection reset
partial stream read
partial write
backend returns malformed metadata
operation unsupported
fallback backend unavailable
second fallback fails
concurrent requests
shutdown during operation
process restart after partial side effect
corrupt local config
plugin throws unexpected exception
health backend timeout
```

Для destructive storage:

```text
copy file N of M fails
verification fails
source removal fails
destination cleanup fails
```

Expected result не может быть «success».

---

# 39. Certification command

В будущем удобно иметь generic command:

```text
python -m stratbox.extensions.certify \
  --plugin example.corporate.infrastructure \
  --profile managed-production \
  --output certification.json
```

И отдельно capability/deep checks:

```text
python -m stratbox.extensions.certify \
  --plugin example.corporate.infrastructure \
  --capability storage.workspace \
  --deep
```

Private plugin CI запускает synthetic/fake tests всегда, deep integration — на controlled corporate runner.

---

# 40. Testing pyramid

## Layer 1 — pure unit

No network:

- config parsing;
- path normalization;
- capability decisions;
- error mapping;
- policy transformation;
- redaction;
- fallback decision logic.

## Layer 2 — adapter contract with fakes

Fake corporate clients simulate capability matrices and failures.

Это главный слой для сложных fallback paths.

## Layer 3 — public conformance

Reusable Strategy Box suite.

## Layer 4 — private integration

Real backend in isolated test namespace.

## Layer 5 — managed smoke

После установки AppDock/environment:

```text
discovery
activation
readiness
small roundtrip
cleanup
```

---

# 41. AppDock boundary

Хотя этот документ относится к `stratbox`, corporate plugin должен естественно работать в AppDock-managed environment.

## 41.1. AppDock не знает private implementation

AppDock видит:

```text
Strategy Box package graph
runtime activation success
capability readiness
safe diagnostics/problem references
```

Ему не нужно знать storage driver, secret backend или network routing details.

## 41.2. Package graph

AppDock/private deployment layer определяет exact packages, versions и hashes.

## 41.3. Strategy Box health projection

Core/application может проецировать:

```text
extensions:
  status: READY
  required_capabilities:
    storage.workspace: READY
    secrets.default: READY
    network.default: READY
```

## 41.4. Physical logs

Plugin emits structured diagnostics. Strategy Box/AppDock observability layer решает physical retention, log files, support bundles и shared problem projection.

Plugin не должен самостоятельно строить параллельный platform-wide log system.

## 41.5. Errors

Plugin/capability error проходит:

```text
provider error
→ stratbox structured failure/diagnostic
→ surface execution boundary
→ AppDock ProblemDraft/ProblemRef where relevant
```

Private backend exception не должен выходить в пользовательский UI напрямую.

---

# 42. Interaction with artifact layer

Corporate storage plugin — physical layer.

Целевая структура:

```text
ArtifactService / SourceSnapshot / Workspace
              ↓
        neutral FileStore
              ↓
    corporate storage provider
```

Plugin не должен:

- присваивать business Artifact IDs;
- решать artifact retention globally;
- хранить business lineage как private backend feature;
- делать private path canonical artifact identity.

Это обеспечивает переносимость Windows → host → Android и замену storage backend без изменения domain semantics.

---

# 43. Interaction with operation/scenario architecture

Operation descriptor может заявлять required capabilities:

```text
operation:
  id: cbr.files.collect
  requires:
    - network.default
    - storage.workspace
```

Execution runtime перед стартом проверяет:

```text
capability bound?
provider ready?
required optional feature available?
```

Если нет — operation не запускается и получает structured precondition failure.

Это лучше, чем обнаруживать отсутствие capability в середине большого расчёта.

---

# 44. Plugin capabilities and AI agents

В будущем AI должен видеть **разрешённые Strategy Box operations**, а не plugin internals.

AI не получает:

- secret provider;
- storage driver object;
- gateway config;
- raw plugin methods.

Цепочка:

```text
AI
→ operation/scenario API
→ core capability resolution
→ plugin provider internally
```

Это сохраняет least privilege и не превращает corporate plugin в agent tool server.

---

# 45. Documentation contract

## 45.1. Public core documentation

Должна описывать:

- plugin concept;
- public protocols;
- capability IDs;
- error semantics;
- health semantics;
- activation model;
- certification;
- synthetic example plugin.

## 45.2. Private plugin documentation

Хранит:

- installation source;
- environment requirements;
- concrete configuration;
- private backend descriptions;
- secret/bootstrap procedures;
- support contacts;
- private deep diagnostics;
- internal rollout process.

## 45.3. No private cross-link requirement

Public core docs могут сказать:

> install an organization-specific plugin distribution and enable its plugin ID.

Имя конкретного private package не требуется.

---

# 46. Reference API sketch

Ниже не готовый implementation API, а проверка того, что концепция складывается в компактный интерфейс.

```python
from dataclasses import dataclass
from typing import Mapping, Protocol


@dataclass(frozen=True)
class CapabilityDeclaration:
    capability_id: str
    contract_version: int
    instance_name: str = "default"
    concurrency: str = "thread_safe"
    optional_features: frozenset[str] = frozenset()


@dataclass(frozen=True)
class PluginDescriptor:
    plugin_id: str
    api_version: int
    requires_stratbox: str
    capabilities: tuple[CapabilityDeclaration, ...]
    effects: frozenset[str] = frozenset()


class EventSink(Protocol):
    def emit(self, event: "ExtensionEvent") -> None: ...


@dataclass(frozen=True)
class PluginContext:
    runtime_profile: str
    config: Mapping[str, object]
    events: EventSink


@dataclass(frozen=True)
class PluginContribution:
    providers: Mapping[str, object]


class StratboxPlugin(Protocol):
    def descriptor(self) -> PluginDescriptor: ...
    def activate(self, context: PluginContext) -> PluginContribution: ...
    def health(self, depth: str = "static") -> "PluginHealthReport": ...
    def close(self) -> None: ...
```

Важнее signatures — invariants:

- descriptor safe and side-effect-free;
- activation explicit;
- providers keyed by public capabilities;
- health machine-readable;
- events host-owned;
- errors typed;
- no private imports in core.

---

# 47. Reference discovery sketch

```python
from importlib.metadata import entry_points


def discover_plugins() -> list[DiscoveredPlugin]:
    eps = entry_points(group="stratbox.plugins.v1")
    # do not activate here
    # validate duplicate IDs
    # bind distribution metadata
    return ...
```

Activation отдельно:

```python
def activate_selected(selection: ExtensionSelection) -> ExtensionRuntime:
    discovered = discover_plugins()
    selected = resolve_selection(discovered, selection)
    validate_compatibility(selected)
    load_descriptors(selected)
    resolve_capability_bindings(selected, selection)
    activate_plugins(selected)
    run_required_readiness()
    return ExtensionRuntime(...)
```

---

# 48. Runtime diagnostics surface

Core должен уметь вернуть safe machine-readable snapshot:

```json
{
  "extensions": [
    {
      "plugin_id": "example.corporate.infrastructure",
      "distribution_version": "1.4.0",
      "api_version": 1,
      "state": "READY",
      "capabilities": [
        {"id": "storage.workspace", "state": "READY"},
        {"id": "secrets.default", "state": "READY"},
        {"id": "network.default", "state": "READY"}
      ]
    }
  ]
}
```

Private backend names are absent.

---

# 49. Compliance scoring

Я бы **не** вводил условные Bronze/Silver/Gold уровни. Они создают ложную управленческую простоту.

Лучше:

```text
PASS
FAIL
CONDITIONAL
```

по конкретному profile.

Пример:

```text
core-contract          PASS
capability-storage     PASS
capability-network     PASS
managed-production     FAIL (2 blocking checks)
```

Это сразу показывает, что исправлять.

---

# 50. Requirements catalogue

Ниже более полный каталог, пригодный для issue/implementation tracking.

## Architecture

**PLG-ARCH-001 — Dependency inversion.** Domain code depends only on public core contracts. **MUST**.  
**PLG-ARCH-002 — No named private import.** Core cannot import private distribution/module names. **MUST**.  
**PLG-ARCH-003 — No monkey patch.** Plugin cannot patch core globals/functions. **MUST**.  
**PLG-ARCH-004 — No UI ownership.** Infrastructure plugin has no product surface. **MUST**.  
**PLG-ARCH-005 — No domain logic.** Banking/macro calculations remain outside infrastructure plugin. **MUST**.  
**PLG-ARCH-006 — Artifact separation.** Physical storage provider does not own logical artifact identity. **MUST**.  
**PLG-ARCH-007 — Public API imports only.** Plugin cannot use internal core modules. **MUST**.  

## Discovery and identity

**PLG-DISC-001 — PyPA entry point.** Distribution advertises plugin through versioned group. **MUST**.  
**PLG-DISC-002 — Stable plugin ID.** ID independent from module path. **MUST**.  
**PLG-DISC-003 — Unique ID.** Duplicate plugin IDs are blocking. **MUST**.  
**PLG-DISC-004 — Side-effect-free entry import.** No network/secrets/files on discovery. **MUST**.  
**PLG-DISC-005 — Distribution metadata linkage.** Runtime records installed distribution identity/version. **MUST**.  

## Activation

**PLG-ACT-001 — Explicit enablement.** Installation does not imply activation. **MUST managed**.  
**PLG-ACT-002 — Explicit bindings.** Singleton conflicts require configured binding. **MUST**.  
**PLG-ACT-003 — No order precedence.** Discovery order never selects provider. **MUST**.  
**PLG-ACT-004 — Required means required.** Failure of required plugin blocks readiness. **MUST**.  
**PLG-ACT-005 — Optional degradation explicit.** Degraded fallback must be configured and observable. **MUST**.  

## Compatibility

**PLG-VER-001 — Plugin API version.** Checked before activation. **MUST**.  
**PLG-VER-002 — Capability contract versions.** Checked individually. **MUST**.  
**PLG-VER-003 — Core version requirement.** PEP 440-compatible specifier. **MUST**.  
**PLG-VER-004 — No legacy adapters by default.** Old contract rejected after redesign. **MUST**.  

## Capabilities

**PLG-CAP-001 — Declaration.** Plugin declares all provided capabilities. **MUST**.  
**PLG-CAP-002 — Honest optional features.** Feature claim is testable. **MUST**.  
**PLG-CAP-003 — Core-owned semantics.** Provider cannot redefine core meaning. **MUST**.  
**PLG-CAP-004 — Core-owned merge policy.** Multi-addon conflict behavior belongs to core. **MUST**.  
**PLG-CAP-005 — Stable capability snapshot.** Capabilities cannot randomly change during one runtime activation. **MUST**.  

## Errors

**PLG-ERR-001 — Stable taxonomy.** Provider errors map to core error model. **MUST**.  
**PLG-ERR-002 — No false success.** Error cannot become empty successful result. **MUST**.  
**PLG-ERR-003 — Partial explicit.** Partial operation is not success. **MUST**.  
**PLG-ERR-004 — Unexpected exception isolation.** Runtime wraps provider bug. **MUST**.  
**PLG-ERR-005 — Retry metadata.** Retryable semantics where known. **SHOULD**.  
**PLG-ERR-006 — Unknown outcome.** Side-effect ambiguity can be represented. **MUST for remote/destructive**.  

## Observability

**PLG-OBS-001 — Structured events.** No print as primary diagnostics. **MUST**.  
**PLG-OBS-002 — Correlation.** Events carry run/correlation IDs when invoked from operation. **MUST**.  
**PLG-OBS-003 — Duration/outcome.** External calls expose duration and result. **SHOULD**.  
**PLG-OBS-004 — Retry/fallback event.** Any fallback is observable. **MUST**.  
**PLG-OBS-005 — Redaction.** Secrets/sensitive fields removed. **MUST**.  
**PLG-OBS-006 — OTel mappability.** Event fields can map to common telemetry model. **SHOULD**.  

## Health

**PLG-HLT-001 — Static health.** Always available after load. **MUST**.  
**PLG-HLT-002 — Capability readiness.** External service providers expose readiness. **MUST**.  
**PLG-HLT-003 — Deep check isolated.** Roundtrip checks use isolated namespace. **MUST**.  
**PLG-HLT-004 — Safe report.** No private sensitive configuration. **MUST**.  
**PLG-HLT-005 — Action hint.** Auth/config problems provide safe remediation hint. **SHOULD**.  

## Configuration

**PLG-CFG-001 — Deterministic production config.** **MUST**.  
**PLG-CFG-002 — Schema version.** **MUST if plugin has config**.  
**PLG-CFG-003 — Sensitive fields classified.** **MUST**.  
**PLG-CFG-004 — Unknown key handling.** strict profile rejects. **SHOULD**.  
**PLG-CFG-005 — No hidden interactive block.** **MUST managed**.  
**PLG-CFG-006 — Safe provenance.** config source may be diagnosed without values. **SHOULD**.  

## Security

**PLG-SEC-001 — Explicit trust.** Enabled plugin belongs to approved distribution set. **MUST managed**.  
**PLG-SEC-002 — No runtime installer.** **MUST**.  
**PLG-SEC-003 — Privileged effects declared.** **MUST**.  
**PLG-SEC-004 — Least privilege.** **SHOULD**.  
**PLG-SEC-005 — Secret hygiene.** **MUST**.  
**PLG-SEC-006 — Namespace/root safety.** **MUST for destructive storage**.  
**PLG-SEC-007 — No weaker silent security fallback.** **MUST**.  

## Packaging

**PLG-PKG-001 — Wheel build.** **MUST**.  
**PLG-PKG-002 — Clean install.** **MUST**.  
**PLG-PKG-003 — Declared dependencies.** **MUST**.  
**PLG-PKG-004 — Runtime files included.** **MUST**.  
**PLG-PKG-005 — Portable archive paths.** **MUST**.  
**PLG-PKG-006 — No generated runtime state.** **MUST**.  
**PLG-PKG-007 — Single version source.** **SHOULD**.  

## Testing

**PLG-TST-001 — Unit suite.** **MUST**.  
**PLG-TST-002 — Fake backend failure matrix.** **MUST where adapter branching exists**.  
**PLG-TST-003 — Public conformance suite.** **MUST**.  
**PLG-TST-004 — Private backend integration.** **MUST production**.  
**PLG-TST-005 — Fault injection destructive paths.** **MUST if destructive**.  
**PLG-TST-006 — Concurrency test.** **SHOULD**.  
**PLG-TST-007 — Wheel-installed smoke.** **MUST**.  

## Supply chain

**PLG-SUP-001 — Exact wheel hash in managed deployment.** **MUST**.  
**PLG-SUP-002 — Locked dependencies.** **SHOULD**.  
**PLG-SUP-003 — SBOM.** **SHOULD**.  
**PLG-SUP-004 — Build provenance.** **SHOULD**.  
**PLG-SUP-005 — Signed/attested publishing where available.** **SHOULD**.  

---

# 51. Blocking acceptance criteria

Plugin может считаться пригодным для managed production только если одновременно выполнено:

```text
1. correct versioned entry point
2. unique stable plugin ID
3. exact supported plugin API
4. selected explicitly
5. all required capability bindings resolved
6. descriptor/import side-effect-free
7. all providers satisfy public contracts
8. no false-success error semantics
9. no destructive integrity violation
10. secret redaction passes
11. structured observability works
12. static + readiness health pass
13. public conformance suite pass
14. private integration smoke pass
15. wheel build/install pass
16. deployment artifact hash recorded
17. no direct private coupling in public core
```

Любой failure из 1–13 — блокирующий для activation/certification. 14–16 блокируют production deployment, но не обязательно local development.

---

# 52. Current private plugin: как применять этот документ

Этот документ специально не содержит concrete private implementation details. Существующий закрытый plugin проверяется как **black-box/white-box private implementation** against public criteria.

Рекомендуемая процедура:

```text
Step 1  Build wheel in clean environment
Step 2  Inspect entry point and distribution metadata
Step 3  Run core-contract conformance
Step 4  Run each declared capability suite against fakes
Step 5  Run fault injection
Step 6  Run real isolated integration certification
Step 7  Run managed activation through AppDock environment
Step 8  Capture redacted CertificationReport
Step 9  Fix blocking failures
Step 10 repeat until managed-production PASS
```

Проверка должна отвечать на вопросы вида:

```text
Does it implement storage semantics exactly?
Does it distinguish backend outage from empty data?
Can it lose data during fallback move?
Can a secret-store outage silently downgrade?
Can managed execution block on interactive input?
Can multiple plugins coexist deterministically?
Are load failures visible?
Are health and capabilities machine-readable?
Are private details absent from public core?
Does installed wheel contain everything runtime needs?
Are versions/provenance reproducible?
```

Результат сохраняется в private repo/support material, а не в public `stratbox`.

---

# 53. Что следует изменить в будущем `stratbox`

## P0 — Public/private sanitation

1. Удалить любую dependency на конкретный private distribution из public package metadata.
2. Удалить direct imports private packages из core.
3. Переписать public docs/examples на synthetic plugin vocabulary.
4. Добавить automated scan/check, запрещающий known private identifiers в public repository.

## P0 — New extension API

5. Ввести `stratbox.plugins.v1`.
6. Ввести `PluginDescriptor`, `CapabilityDeclaration`, activation state model.
7. Разделить discovery и activation.
8. Сделать enabled plugins explicit.
9. Ввести deterministic conflict handling.

## P0 — Error correctness

10. Установить typed generic infrastructure errors.
11. Запретить silent successful fallbacks.
12. Подготовить `UNKNOWN`/`PARTIAL` semantics where needed.

## P1 — Capability contracts

13. Обновить FileStore до capability-aware target contract.
14. Усилить SecretProvider result/error model.
15. Сделать NetworkPolicy public capability.
16. Нормализовать reporting addon.

## P1 — Health and observability

17. Ввести structured extension events.
18. Ввести health/readiness models.
19. Связать events с operation run correlation IDs.
20. Сделать AppDock projection generic.

## P1 — Conformance

21. Создать synthetic reference plugin.
22. Создать public conformance harness.
23. Добавить test distributions с конфликтами, broken imports и wrong contracts.
24. Добавить certification JSON model/CLI.

## P2 — Supply chain

25. Определить managed lock/artifact hash policy.
26. Добавить wheel install smoke в CI.
27. Подготовить SBOM/provenance hooks.

---

# 54. Reference synthetic plugin

Public repository полезно иметь **полностью искусственный** plugin test fixture, который демонстрирует contract без company details.

Например:

```text
tests/fixtures/example_extension/
  pyproject.toml
  src/example_stratbox_extension/
    entry.py
    storage.py
    secrets.py
```

Он работает только с temp directory/in-memory secrets и нужен для:

- documentation;
- CI;
- loader tests;
- conflict tests;
- failure injection;
- examples.

---

# 55. Loader test matrix

Public core CI должен иметь synthetic distributions:

```text
good_plugin
wrong_api_version
wrong_descriptor_type
broken_import
duplicate_plugin_id
capability_conflict
provider_wrong_protocol
provider_raises_on_activate
health_failure
addon_name_collision
```

Expected behavior фиксируется contract tests.

---

# 56. Why entry points remain the right discovery mechanism

PyPA entry points специально предназначены для случая, когда independently distributed package объявляет component, discoverable другим code. Они дают:

- package metadata discovery;
- отсутствие ручного import list;
- standard wheel/install integration;
- distribution identity;
- interoperability с `importlib.metadata`.

Strategy Box должен пользоваться этим стандартом, но добавить свою строгую policy:

```text
entry point = discovery transport
Strategy Box contract = semantics/trust/activation
```

Entry points сами по себе не решают:

- authorization;
- API compatibility;
- multiple-plugin conflicts;
- health;
- security;
- conformance;
- error semantics.

Именно эти части должен определить `stratbox`.

---

# 57. Why a separate static manifest is not required for v1

Можно было бы добавить `stratbox-plugin.json`, но это создаёт второй metadata source.

Для v1 достаточно:

```text
PyPA distribution metadata
+ versioned entry point
+ side-effect-free descriptor()
```

Преимущества:

- меньше duplication;
- version/name/dependencies уже живут в standard metadata;
- plugin ID виден через entry-point name до import;
- descriptor даёт capability details.

Static manifest стоит вводить только если AppDock/package tooling реально понадобится читать capability metadata **без Python import**. До такого consumer — преждевременно.

---

# 58. Why not Pluggy as mandatory dependency

Frameworks типа Pluggy полезны для rich hook systems, но текущая задача Strategy Box проще:

```text
few typed service capabilities
explicit activation
small addon registries
strict provider contracts
```

Собственный небольшой runtime поверх PyPA entry points + Protocol/dataclasses будет:

- прозрачнее;
- легче сертифицировать;
- легче держать public/private boundary;
- без лишнего hook lifecycle.

Если в будущем появятся десятки hook types и composition semantics, Pluggy можно оценить повторно. Сейчас он не нужен как architectural dependency.

---

# 59. Why not expose private providers directly to UI/AppDock

Это создаст transitive coupling:

```text
UI → private plugin → backend
```

и сломает Android/remote portability.

Правильно:

```text
UI/AppDock
→ Strategy Box operation/runtime state
→ capability registry
→ private plugin internally
```

Surface видит safe capability state, а не private objects.

---

# 60. Why exact plugin semantics matter more than feature count

Infrastructure code опасен тем, что ошибка часто выглядит как нормальный результат:

```text
[]
False
None
empty file
partial folder
fallback path
```

Поэтому maturity plugin-а измеряется прежде всего:

- semantic correctness;
- data integrity;
- failure transparency;
- reproducibility;
- observability;
- certification coverage.

Количество gateways/styles/backends — вторично.

---

# 61. Future remote/host implications

Когда operation выполняется на host:

- plugin активируется **на execution node**, где находится infrastructure;
- client не получает provider object;
- capability state публикуется safe projection;
- plugin-local paths не пересылаются как universal identity;
- results возвращаются через ArtifactRef/operation result;
- outcome `UNKNOWN` поддерживается при network loss;
- exact plugin/core versions входят в run provenance.

Это ещё один аргумент за strict versioned plugin API сейчас.

---

# 62. Reproducibility manifest

Каждый существенный run в managed environment в будущем сможет сохранять:

```text
stratbox version/revision
plugin IDs
plugin distribution versions
plugin API versions
capability contract versions
activation profile ID/hash
source snapshot hashes
registry versions
operation parameters hash
result artifact hashes
```

Без private secrets/config values.

Это позволит доказать, **в каком environment был получен результат**, не публикуя внутреннее устройство environment.

---

# 63. Support bundle

При проблеме support bundle может включать:

```text
safe extension inventory
compatibility report
health report
certification summary
recent structured events
problem refs
core/plugin versions
package hashes
sanitized config provenance
```

Не включает автоматически:

```text
secrets
raw credentials
private full config
unredacted environment dump
full home directory paths
```

---

# 64. Definition of Done для plugin API v1 в core

Новая public extension architecture готова, когда:

1. Core не содержит ни одного named private import/dependency.
2. Plugin discovery идёт только через `stratbox.plugins.v1`.
3. Discovery и activation разделены.
4. Managed selection explicit.
5. Duplicate plugin IDs и capability conflicts deterministic errors.
6. `PluginDescriptor` и capability models public/stable within v1.
7. FileStore/Secret/Network/Reporting contracts описаны.
8. Provider errors normalized.
9. No silent fallback in required managed mode.
10. Structured extension events работают.
11. Health/readiness model работает.
12. Synthetic reference plugin проходит tests.
13. Broken synthetic plugins дают ожидаемые errors.
14. Public conformance suite может запускаться private repositories.
15. Certification report serializable and redacted.
16. Core CI не требует private infrastructure.
17. AppDock/desktop могут увидеть generic capability readiness without private details.
18. Private plugin можно заменить другим implementation без изменений domain code.

---

# 65. Definition of Done для конкретного corporate plugin

Конкретный plugin считается готовым к production, когда:

1. Его wheel reproducibly устанавливается.
2. Он обнаруживается под уникальным approved ID.
3. Он соответствует актуальному plugin API без compatibility shims.
4. Все declared capability contracts проходят conformance.
5. Fault injection не выявляет false success/data loss.
6. Managed activation не использует silent fallback.
7. Required capability health = READY в target environment.
8. Secrets и internal configuration не попадают в logs/health/certification output.
9. Deep integration roundtrip проходит в isolated namespace.
10. Concurrency model подтверждён.
11. Wheel hash и exact dependency set входят в deployment provenance.
12. Public repositories не содержат его implementation details.

---

# 66. Приоритетная последовательность разработки

## Stage A — очистка public boundary

Сначала убрать любую concrete private coupling из `stratbox`.

## Stage B — extension core

Сделать models/discovery/activation/registry/errors.

## Stage C — storage pilot

FileStore — лучший pilot, потому что он сложнее всего по semantic/failure matrix и уже необходим real plugin.

## Stage D — secrets + network

После storage закрепить auth/config и outbound policy.

## Stage E — reporting addons

Перевести passive styles/templates в общий contribution model.

## Stage F — health/observability

Связать plugin diagnostics с общей Strategy Box observability моделью.

## Stage G — conformance suite

Публичные tests + synthetic plugin + certification report.

## Stage H — private plugin migration

Только после фиксации public contract переписать private implementation под него. Обратный путь — подгонять public contract под текущий private code — даст слабую архитектуру.

## Stage I — managed AppDock validation

Проверить install graph, readiness projection, errors/support bundle.

---

# 67. Что сознательно не включать в v1

Чтобы contract остался сильным и небольшим, в первый API не стоит включать:

- hot plugin reload;
- plugin marketplace;
- untrusted sandboxing;
- arbitrary event hooks во все стадии core;
- domain operation injection;
- UI widgets;
- background scheduler API;
- AppDock-specific package manifest inside plugin API;
- generic RPC protocol;
- dynamic code download;
- legacy compatibility layer;
- plugin-to-plugin imports;
- plugin-defined precedence rules.

При реальной потребности каждую такую функцию лучше добавить как отдельный contract.

---

# 68. Главные архитектурные решения

Итоговая позиция исследования:

1. **Entry points сохранить.** Это правильный standard discovery transport.
2. **Discovery отделить от activation.** Installed не значит active.
3. **Version the group.** `stratbox.plugins.v1`.
4. **Plugin ID сделать stable и unique.**
5. **Capabilities declarative.** Core знает capability, а не implementation.
6. **Bindings explicit.** Никакого first-wins.
7. **Managed mode fail-closed.** Required plugin failure нельзя маскировать local fallback.
8. **No named private imports/dependencies in public core.**
9. **Infrastructure plugin держать infrastructure-only.**
10. **FileStore сделать capability-aware и semantically strict.**
11. **Secrets сделать typed и non-interactive in managed mode.**
12. **Network routing поднять в neutral capability.**
13. **Reporting styles оставить passive addon.**
14. **Structured errors/events/health обязательны.**
15. **Private backend details не входят в public diagnostics.**
16. **Conformance suite принадлежит core.**
17. **Private CI использует public certification harness.**
18. **Supply-chain provenance считать частью production readiness.**
19. **Artifact semantics держать выше storage plugin.**
20. **Не строить compatibility shims.** Новый contract внедрять сразу в целевой форме.

---

# 69. Итоговая формула

Самая короткая формулировка будущего corporate plugin contract:

> **Corporate plugin — это явно активируемый, versioned, capability-declared и автоматически сертифицируемый adapter package, который реализует нейтральные инфраструктурные контракты `stratbox` для конкретной среды, не раскрывая эту среду в public core и не меняя semantics domain logic.**

А критерий хорошей архитектуры выглядит так:

```text
Удалили private plugin из environment
→ stratbox по-прежнему является полностью корректным public product
→ меняется только доступный capability profile.

Заменили private plugin другим conforming implementation
→ domain operations не переписываются.

Plugin сломался
→ система точно знает, что сломалось
→ не притворяется успешной
→ не переключается тайно на другую семантику
→ выдаёт safe health/error evidence.
```

Именно такой контракт позволит дальше независимо развивать:

- публичный `stratbox`;
- закрытые корпоративные capability packs;
- AppDock-managed deployments;
- Windows/Android surfaces;
- local/host/background/remote execution;
- будущие AI scenarios.

---

# Приложение A. Минимальный шаблон private plugin package

```text
example-stratbox-plugin/
├── pyproject.toml
├── README.private.md
├── src/
│   └── example_plugin/
│       ├── __init__.py
│       ├── entry.py
│       ├── config.py
│       ├── health.py
│       ├── providers/
│       │   ├── storage/
│       │   ├── secrets/
│       │   ├── network/
│       │   └── reporting/
│       └── diagnostics.py
└── tests/
    ├── unit/
    ├── conformance/
    └── integration/
```

Необязательно создавать пустые directories заранее. Это target responsibility map.

---

# Приложение B. Минимальный `pyproject.toml` пример

```toml
[build-system]
requires = ["setuptools>=...", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "example-stratbox-plugin"
version = "1.0.0"
requires-python = ">=3.10"
dependencies = [
  "stratbox>=0.9,<0.10",
]

[project.entry-points."stratbox.plugins.v1"]
"example.corporate.infrastructure" = "example_plugin.entry:plugin"
```

Exact versions/hashes фиксируются deployment lock, а не обязательно `dependencies` plugin package.

---

# Приложение C. Private plugin review worksheet

```text
IDENTITY
[ ] stable plugin ID
[ ] correct distribution version
[ ] correct plugin API
[ ] exact target core compatibility

DISCOVERY
[ ] entry point present in installed wheel
[ ] import side-effect-free
[ ] descriptor safe

ACTIVATION
[ ] explicit enablement
[ ] explicit singleton bindings
[ ] no silent local fallback
[ ] deterministic conflict handling

CAPABILITIES
[ ] all declared
[ ] all required interfaces implemented
[ ] optional features truthful
[ ] concurrency declared

ERRORS
[ ] not-found distinct
[ ] permission distinct
[ ] unavailable distinct
[ ] unsupported distinct
[ ] partial distinct
[ ] no swallowed destructive failures

OBSERVABILITY
[ ] structured events
[ ] correlation IDs
[ ] retries visible
[ ] fallbacks visible
[ ] no secrets

HEALTH
[ ] static
[ ] readiness
[ ] deep isolated roundtrip
[ ] safe output

STORAGE
[ ] read/write
[ ] empty object
[ ] Unicode
[ ] list/stat
[ ] move/copy
[ ] recursive delete
[ ] root safety
[ ] interrupted write
[ ] partial copy failure
[ ] checksum if declared
[ ] streaming if declared

SECRETS
[ ] no value in repr/log/error
[ ] auth-required state
[ ] backend unavailable state
[ ] strict fallback policy
[ ] non-interactive managed execution

NETWORK
[ ] deterministic route policy
[ ] deny vs unavailable
[ ] timeout/auth/TLS split
[ ] redaction

PACKAGING
[ ] clean wheel
[ ] clean install
[ ] no source-tree dependency
[ ] no generated junk
[ ] portable archive

TESTS
[ ] unit
[ ] fakes
[ ] public conformance
[ ] fault injection
[ ] private integration
[ ] managed smoke

SUPPLY CHAIN
[ ] exact wheel hash
[ ] locked dependency set
[ ] source revision recorded
[ ] SBOM
[ ] provenance/attestation where supported
```

---

# Приложение D. Использованные внешние технические источники

1. Python Packaging User Guide — Entry points specification  
   https://packaging.python.org/en/latest/specifications/entry-points/

2. Python Packaging User Guide — Creating and discovering plugins  
   https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/

3. Python Packaging User Guide — Version specifiers / PEP 440  
   https://packaging.python.org/en/latest/specifications/version-specifiers/

4. Python Packaging User Guide — `pylock.toml` specification  
   https://packaging.python.org/en/latest/specifications/pylock-toml/

5. Python Packaging User Guide — Index hosted attestations / PEP 740  
   https://packaging.python.org/en/latest/specifications/index-hosted-attestations/

6. Python documentation — `typing.Protocol`, `runtime_checkable`  
   https://docs.python.org/3/library/typing.html

7. OpenTelemetry — Logs Data Model  
   https://opentelemetry.io/docs/specs/otel/logs/data-model/

8. SLSA — Provenance  
   https://slsa.dev/spec/v1.2/provenance

9. SPDX — Specifications  
   https://spdx.dev/use/specifications/

10. NIST SP 800-218 — Secure Software Development Framework  
    https://csrc.nist.gov/pubs/sp/800/218/final

---

# Приложение E. Связанные внутренние исследования

- `stratbox_base_study_current_state_2026-10-06.md`;
- private current-state research of the corporate environment extension, 2026-10-06;
- `stratbox_filestore_file_formats_research_2026-10-07.md`;
- `stratbox_file_artifact_layer_research_2026-10-06.md`;
- `stratbox_observability_errors_logs_research_2026-10-07.md`;
- `stratbox_commands_scenarios_cascades_research_2026-10-07.md`;
- AppDock product and observability architecture materials.

Private details intentionally excluded from this document.
