# Strategy Box: целевая архитектура файлового и артефактного слоя

**Research branch:** 02 / вторая ветка исследований Strategy Box  
**Дата:** 2026-10-06  
**Статус:** архитектурное исследование и целевая модель; код и репозитории не изменяются  
**Scope:** `stratbox` core, универсальный client/runtime слой Strategy Box, AppDock boundary, локальные/удалённые хранилища, артефакты, provenance, ИИ-агенты  

---

## 0. Итог в одном абзаце

Путь с `FileStore` выбран правильно, однако `FileStore` должен остаться **узким нижним контрактом физического файлового доступа**, а не превращаться в универсальное понятие для всех данных и результатов Strategy Box. У продукта уже возникает более высокий класс сущностей: исходные снимки внешних данных, наборы данных, отчёты, Excel-файлы, архивы, диагностические результаты, модели, логи и будущие результаты ИИ-агентов. Их идентичность должна жить дольше конкретного пути и конкретного storage backend. Поэтому целевая архитектура должна быть многослойной: **FileStore → Content/Blob layer → ArtifactStore → Artifact Catalog → Provenance/Lineage**, рядом с отдельным **Workspace layer** для изменяемых пользовательских файлов. Файл — физическое размещение байтов. Артефакт — логический, версионированный, проверяемый результат с устойчивым ID, manifest, content hash, происхождением и lifecycle. Workspace — изменяемое пространство пользователя. SourceSnapshot — специальная предметная роль, которая ссылается на зафиксированный артефакт исходного контента. ИИ-агент работает прежде всего с Artifact/Operation API, а прямой доступ к произвольной файловой системе получает только там, где это явно разрешено.

---

# I. Что именно мы пытаемся решить

## 1. Задача шире файлового API

Strategy Box задуман как широкое приложение для работы с макроэкономическими и банковскими данными, расчётами, сценариями и отчётными результатами. Из уже накопленного исследования core видна естественная цепочка:

```text
source
  ↓
raw snapshot
  ↓
parse / normalization
  ↓
canonical data
  ↓
validation / reconstruction / calculation
  ↓
view
  ↓
artifact
```

Одновременно пользовательская поверхность уже мыслит результат выполнения как самостоятельный объект, связанный с кейсом, сценарием, операцией, логом и автором. AppDock, в свою очередь, рассматривает результаты, рабочую среду, файлы, восстановление и будущих ИИ-агентов как части единого управляемого мира.

Поэтому вопрос «как читать файл по пути» является лишь одной частью задачи. Полная задача звучит так:

> **Как Strategy Box должен адресовать, хранить, фиксировать, проверять, показывать, передавать, воспроизводить и безопасно использовать данные и результаты независимо от того, где физически лежат их байты и кто с ними работает — человек, операция, удалённый host или ИИ-агент?**

Это уже storage/data plane, а не один FileStore.

---

## 2. Уже существующие предпосылки

В текущем core `FileStore` уже абстрагирует физическое хранилище и даёт операции уровня read/write/stat/list/copy/walk. Это хороший фундамент переносимости. Исследование core уже отдельно указывает на естественные будущие возможности: atomic write, checksum, metadata/etag, настоящий streaming, copy between stores и capability discovery.

В клиентском слое артефакты уже являются отдельными сущностями, а не просто строками путей. Есть связь `case → step → operation → log → artifact → event`. В roadmap уже появляются content hash, lineage, source URLs, retention и artifact-to-scenario chaining.

AppDock также задаёт важный системный контекст: рабочая среда должна уметь хранить результаты, показывать их, передавать, использовать удалённо и выдавать агентам ограниченные действия вместо полного доступа к компьютеру.

Следовательно, новая архитектура не создаётся с нуля. Она **формализует уже возникшие естественные границы**.

---

# II. Термины, которые необходимо развести

## 3. `FileStore`

`FileStore` — **иерархическое path-addressed хранилище файлов и каталогов**.

Его предмет — физические операции:

```text
open/read/write
exists/stat/list
mkdir/remove
copy/move
stream/range read
metadata/checksum where supported
```

Он отвечает на вопрос:

> Где и как физически прочитать или записать байты по некоторому locator/path?

Он не обязан знать, что файл является отчётом, исходной публикацией ЦБ, результатом сценария или артефактом ИИ.

---

## 4. `Workspace`

`Workspace` — **изменяемое пользовательское рабочее пространство**.

Типичные свойства:

- человек может создавать, редактировать, переименовывать и удалять файлы;
- пути имеют пользовательский смысл;
- структура каталогов важна для UX;
- содержимое может измениться вне Strategy Box;
- файл в workspace не обязан иметь устойчивую идентичность;
- workspace может содержать входы, промежуточные материалы и экспортированные результаты.

Workspace — это не ArtifactStore.

Пример:

```text
workspace:/input/manual.xlsx
workspace:/output/report.xlsx
workspace:/scratch/temporary.csv
```

`report.xlsx` может быть **материализацией** артефакта, но сам путь `workspace:/output/report.xlsx` не должен становиться идентичностью артефакта.

---

## 5. `Blob` / content object

Blob — **неизменяемый набор байтов**, идентифицируемый содержимым или внутренним object ID.

Минимальный descriptor:

```text
algorithm = sha256
Digest     = sha256:...
size       = ... bytes
media_type = application/...
```

Это уровень, на котором полезна content-addressability.

Blob не знает бизнес-смысла данных.

---

## 6. `Artifact`

Artifact — **логический зафиксированный результат или вход Strategy Box**, имеющий устойчивый ID и metadata независимо от физического пути.

Он может быть:

- одним файлом;
- каталогом/набором файлов;
- dataset;
- workbook;
- report;
- ZIP bundle;
- image/chart;
- raw source snapshot;
- model output;
- diagnostic package;
- published log;
- объектом, созданным ИИ-агентом.

Ключевое свойство:

> committed artifact immutable.

Если содержимое изменилось — появился другой artifact или другой immutable artifact version, но не «тот же самый объект с тихо изменившимися байтами».

---

## 7. `Artifact Manifest`

Manifest — переносимое описание содержимого артефакта.

Для одиночного файла он тривиален. Для составного артефакта он перечисляет части:

```text
Artifact
  ├─ report.xlsx
  ├─ data.parquet
  ├─ chart.png
  └─ README.md
```

Каждая часть имеет role, logical path, digest, size и media type.

Manifest позволяет представить directory artifact без зависимости от реальной семантики каталогов backend-а.

---

## 8. `Artifact Catalog`

Catalog — **индекс метаданных и связей**, а не место для больших payloads.

Он отвечает на вопросы:

- какой artifact имеет такой ID;
- кто и когда его создал;
- каким run он создан;
- какие входы использованы;
- какой digest у содержимого;
- где payload физически доступен;
- какие теги/классификация/retention применяются;
- какие artifacts производны от этого;
- является ли объект committed/tombstoned/quarantined.

---

## 9. `SourceSnapshot`

`SourceSnapshot` — предметная сущность слоя источников, которая говорит:

> в такой момент Strategy Box получил такой ответ/файл от такого source.

SourceSnapshot должен **ссылаться на ArtifactRef**, содержащий зафиксированные байты raw source.

То есть:

```text
SourceDescriptor
    ↓ fetch
SourceSnapshot ─────→ ArtifactRef(raw source bytes)
```

Это сохраняет разделение:

- `sources` знает источник и fetch semantics;
- `artifacts` знает immutable object;
- `storage` знает физические байты.

---

## 10. `Materialization`

Materialization — **вывод artifact в конкретную файловую поверхность**.

Например:

```text
artifact://a-123
    ↓ materialize
C:\Users\...\Strategy Box Data\output\report.xlsx
```

или:

```text
artifact://a-123
    ↓ remote download
Android Downloads/report.xlsx
```

Один artifact может иметь несколько materializations. Ни одна из них не является его идентичностью.

---

# III. Правильно ли был выбран FileStore

## 11. Да — как нижний слой

`FileStore` решает очень важную проблему: domain code не должен зависеть от `open()`, Windows paths, SMB, local disk, host filesystem или конкретного storage SDK.

Это правильная инверсия зависимости:

```text
domain operation
      ↓
neutral storage contract
      ↓
environment-specific provider
```

Такой подход стоит сохранить.

---

## 12. Где заканчивается FileStore

FileStore становится недостаточным, когда появляются требования:

- результат должен иметь ID после переименования файла;
- нужно понять происхождение результата;
- два одинаковых файла желательно дедуплицировать;
- результат состоит из 20 файлов;
- удалённый host выполнил задачу, а клиенту нужен лишь handle;
- Android не имеет прямого доступа к host path;
- AI должен прочитать только разрешённые результаты;
- нужен immutable snapshot исходной публикации;
- пользователь вручную изменил экспортированный Excel и надо отличить его от оригинала;
- нужно безопасно удалить физические bytes только когда на них больше никто не ссылается;
- нужно повторить расчёт и доказать, какими входами он пользовался.

Попытка решить это расширением одного `FileStore` приведёт к неправильной абстракции: он начнёт одновременно изображать filesystem, database, provenance graph и lifecycle engine.

---

## 13. Главный архитектурный тезис

```text
FileStore ≠ ArtifactStore
```

Более точно:

```text
FileStore     = physical mutable namespace
ArtifactStore = logical immutable object system
Workspace     = human mutable working namespace
```

ArtifactStore **может использовать FileStore как backend**, но не должен сводиться к FileStore.

---

# IV. Что требуется от всей системы

## 14. Функциональные требования

Целевой слой должен поддерживать одновременно:

| Требование | Почему нужно |
|---|---|
| local files | обычный desktop/dev |
| network filesystems | корпоративные и host environments |
| object storage | будущий server/remote scale |
| large files | архивы, наборы данных, модели |
| directories/bundles | составные отчёты и datasets |
| streaming | нельзя держать крупные payloads целиком в RAM |
| atomic/logical commit | не публиковать частичный результат |
| checksum/integrity | reproducibility и remote verification |
| immutable committed artifacts | доверие и lineage |
| mutable workspace | нормальная ручная работа пользователя |
| metadata search | UI, агенты, history |
| stable IDs | путь и backend могут меняться |
| provenance | аудит и воспроизводимость |
| retention/GC | хранилище не растёт бесконечно |
| permission model | пользователи/агенты/remote surfaces |
| remote references | host и mobile |
| multi-platform serialization | Windows/Android/AppDock |
| capability discovery | backend-ы имеют разные возможности |
| recovery | сбой во время записи/commit |

---

## 15. Нефункциональные требования

### Предсказуемая семантика ошибок

Нельзя смешивать:

```text
not found
empty directory
permission denied
backend unavailable
unsupported operation
integrity failure
partial failure
```

### Crash safety

Сбой процесса или питания не должен превращать half-written output в committed artifact.

### Backend neutrality

Архитектура не должна предполагать, что каждый backend имеет настоящий каталог или atomic rename.

### Machine readability

Любой объект, который должен использоваться AppDock/Android/agent, обязан иметь versioned сериализуемое описание.

### Public/private separation

Публичный core и клиенты описывают только contracts/capabilities. Реализации конкретной закрытой среды остаются за provider boundary и не документируются в публичных репозиториях.

---

# V. Какие архитектурные варианты возможны

## 16. Вариант A — оставить только FileStore и пути

```text
OperationResult
  └─ paths: ["output/report.xlsx"]
```

### Плюсы

- минимальная сложность;
- уже работает;
- удобно для локального desktop.

### Минусы

- path становится ложной идентичностью;
- rename ломает ссылки;
- remote/mobile плохо переносимы;
- слабый provenance;
- каталоги и object storage имеют разную семантику;
- агенту придётся давать файловый доступ;
- трудно сделать reliable retention/GC;
- пользователь может изменить файл, а система продолжит считать его прежним результатом.

**Вердикт:** годится как ранний прототип, не как целевая модель.

---

## 17. Вариант B — FileStore + sidecar metadata рядом с файлами

```text
report.xlsx
report.xlsx.meta.json
```

### Плюсы

- просто;
- метаданные переносятся вместе с каталогом;
- легко смотреть вручную.

### Минусы

- sidecar легко потерять при копировании/переименовании;
- конфликт имён;
- search требует полного обхода;
- cross-file transaction слабая;
- directory artifact неудобен;
- concurrency неудобна;
- sidecar трудно считать единственным источником истины.

**Вердикт:** sidecar manifest полезен как экспорт/portable representation, но не как основной catalog.

---

## 18. Вариант C — FileStore + ArtifactStore + metadata catalog

```text
ArtifactService
   ├─ ContentStore backed by FileStore
   └─ ArtifactCatalog
```

### Плюсы

- сохраняется существующая полезная абстракция FileStore;
- artifact ID отделён от path;
- появляются manifests, hashes, lineage, lifecycle;
- можно начать локально;
- позже backend можно заменить без изменения domain API;
- подходит Windows/Android/host/agent;
- catalog даёт быстрый поиск;
- можно постепенно внедрять content-addressed storage.

### Минусы

- появляется второй системный слой;
- нужны transaction/recovery/GC rules;
- надо договориться об ownership metadata.

**Вердикт:** **оптимальная целевая модель для Strategy Box сейчас.**

---

## 19. Вариант D — полноценный CAS/object-store + отдельная БД

```text
Metadata DB
    ↕
Artifact manifests
    ↕
Content-addressed blob store
```

Это зрелая форма варианта C.

### Плюсы

- отличная remote/server масштабируемость;
- dedup;
- immutable payload;
- content verification;
- object storage естественно подходит.

### Минусы

- выше эксплуатационная сложность;
- для простого desktop может быть избыточен настоящий server stack.

**Вердикт:** архитектуру стоит сделать совместимой с этой формой с первого дня, но инфраструктуру уровня S3/PostgreSQL не требуется поднимать сейчас.

---

## 20. Вариант E — event-sourced artifact platform

Каждое изменение lifecycle хранится как event, состояние строится проекциями.

Это красиво сочетается с cases/events, однако для текущего этапа слишком тяжело.

**Вердикт:** не делать artifact event sourcing обязательной базой. Audit events можно добавить позднее, сохраняя простой catalog как operational source of truth.

---

# VI. Рекомендуемая целевая архитектура

## 21. Общая схема

```text
                         ┌─────────────────────────────┐
                         │     Domain Operations       │
                         │ sources / forms / models    │
                         └──────────────┬──────────────┘
                                        │
                         typed Result + Artifact intent
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────┐
│                        Artifact Service                          │
│                                                                  │
│  begin_write  commit  resolve  inspect  materialize  derive      │
└───────────────┬──────────────────────────────┬───────────────────┘
                │                              │
                ▼                              ▼
┌───────────────────────────┐      ┌───────────────────────────────┐
│      Artifact Catalog     │      │     Content / Blob Store      │
│ IDs, manifests, lineage,  │      │ immutable payload objects     │
│ tags, lifecycle, indexes  │      │ digest → bytes                │
└───────────────────────────┘      └──────────────┬────────────────┘
                                                  │
                                                  ▼
                                      ┌───────────────────────────┐
                                      │         FileStore         │
                                      │ path/file operations      │
                                      └─────────────┬─────────────┘
                                                    │
                         ┌──────────────────────────┼──────────────────────┐
                         ▼                          ▼                      ▼
                    local FS                network provider       object backend


        ┌────────────────────────────────────────────────────────┐
        │                       Workspace                         │
        │ mutable files / imports / user exports / scratch       │
        └─────────────────────┬──────────────────────────────────┘
                              │ import / snapshot / materialize
                              └──────────↔ Artifact Service
```

---

## 22. Самое важное разделение

### Управляемая artifact area

Системная зона. Пользователь не должен вручную редактировать committed payload.

### Workspace

Пользовательская зона. Файлы можно менять.

### Cache

Восстанавливаемая зона. Может быть очищена без потери логической истины.

### Scratch/staging

Временная зона незавершённых операций. После crash безопасно очищается по lease/TTL.

Эти четыре зоны нельзя смешивать под одним `output/`.

---

# VII. Низкоуровневый storage contract

## 23. Что оставить в FileStore

Идеальный `FileStore` остаётся небольшим и честным:

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

Convenience functions `read_bytes`, `write_bytes`, `walk`, `glob` могут строиться сверху.

---

## 24. Нужен настоящий streaming

`open_read/open_write` должны означать реальный file-like/streaming contract там, где backend это способен дать.

Нельзя считать нормальным, что:

```text
open_read → read entire remote object into RAM → BytesIO
```

или:

```text
open_write → buffer entire result → upload on close
```

Для небольших Excel это работает, для широкого Strategy Box — ограничение.

Нужны:

- chunked streaming;
- seek capability where available;
- range reads;
- multipart/chunk uploads for large objects;
- explicit `commit()/abort()` вместо безусловного commit на `close()`.

---

## 25. Capability model вместо притворства POSIX

Разные storage backend имеют разные свойства. S3-подобный object store, например, не имеет настоящих каталогов и atomic rename; move реализуется через copy+delete. Поэтому общий API обязан **показывать capabilities**, а не скрывать фундаментальные различия.

Пример:

```python
@dataclass(frozen=True)
class StorageCapabilities:
    streaming_read: bool
    streaming_write: bool
    seek_read: bool
    range_read: bool
    atomic_replace: bool
    atomic_move: bool
    conditional_write: bool
    server_side_copy: bool
    native_checksum: bool
    multipart_write: bool
    signed_urls: bool
    directories_are_native: bool
```

Верхний слой выбирает безопасную стратегию исходя из capabilities.

---

## 26. Error taxonomy

Нужна единая семантика:

```text
StorageError
├─ StorageNotFound
├─ StoragePermissionDenied
├─ StorageAuthenticationRequired
├─ StorageUnavailable
├─ StorageConflict
├─ StorageUnsupported
├─ StorageInvalidPath
├─ StorageIntegrityError
└─ StoragePartialFailure
```

Главное правило:

> infrastructure error никогда не превращается молча в `[]`, `False`, `None` или фиктивный success, если контракт явно этого не требует.

---

## 27. Storage locator вместо случайной строки

На внутренних границах лучше использовать структурированный locator:

```python
@dataclass(frozen=True)
class StorageLocator:
    store_id: str
    path: str
```

Сериализуемое представление:

```text
store://workspace/output/report.xlsx
store://managed-artifacts/objects/sha256/ab/...
```

Это лучше абсолютных Windows paths, которые невозможно переносить на host/mobile.

---

# VIII. Нужен ли fsspec

## 28. Что полезно взять из fsspec

`fsspec` — зрелый Python filesystem abstraction с множеством backend-ов. Особенно релевантны:

- общий `AbstractFileSystem`;
- URL/protocol routing;
- file-like API;
- caching;
- async implementations;
- checksum/info capabilities;
- semi-atomic transaction context, где writes commit при успешном выходе и discard при исключении.

Это подтверждает правильность самого класса абстракции `FileStore`.

---

## 29. Стоит ли заменить собственный FileStore на fsspec

**Прямую замену сейчас я бы не делал.**

Причины:

1. Strategy Box нужен очень небольшой и строго контролируемый public contract.
2. Некоторые environment-specific providers имеют нестандартную семантику.
3. Ошибки, destructive policy и capability contracts должны быть согласованы с продуктом, а не целиком определяться сторонней библиотекой.
4. Artifact layer всё равно придётся строить отдельно.

Правильнее:

```text
Strategy Box FileStore Protocol
        ↑
        ├─ LocalFileStore
        ├─ environment provider
        └─ FsspecFileStoreAdapter (optional)
```

Так `fsspec` становится одним из способов быстро получить S3/SFTP/HTTP/другие backends, а не архитектурой всего продукта.

---

# IX. Content/Blob layer

## 30. Почему полезна content-addressability

Когда committed artifact immutable, его байты естественно идентифицировать digest-ом.

OCI использует descriptor вида:

```text
mediaType
size
digest
```

DVC использует content-addressable cache и хранит одинаковое содержимое один раз независимо от имени файла.

Для Strategy Box это даёт:

- integrity check;
- deduplication;
- независимость от имени;
- безопасный remote transfer;
- быстрый ответ «эти два outputs одинаковы?»;
- основу reproducibility;
- возможность GC по ссылкам.

---

## 31. Рекомендуемый digest

Для managed artifacts:

```text
sha256:<hex>
```

SHA-256 достаточно универсален, широко поддерживается и понятен внешним системам.

ETag backend-а можно сохранять дополнительно, но **не считать универсальным content hash**, потому что его семантика зависит от backend-а и способа upload.

---

## 32. CAS layout поверх обычного FileStore

Даже без S3 можно сделать простой content store поверх любого FileStore:

```text
.artifacts/
  blobs/
    sha256/
      ab/
        abcdef...  # immutable bytes
  manifests/
    sha256/
      12/
        123456...  # canonical JSON manifest
```

Это значит, что физический CAS не требует отдельного сервера.

---

## 33. BlobStore как внутренний Protocol

```python
class BlobStore(Protocol):
    def put(self, stream, *, expected_digest=None) -> BlobRef: ...
    def open(self, ref: BlobRef) -> BinaryIO: ...
    def stat(self, ref: BlobRef) -> BlobStat: ...
    def exists(self, ref: BlobRef) -> bool: ...
    def delete(self, ref: BlobRef) -> None: ...
```

Первая реализация:

```text
FileBlobStore(FileStore)
```

Позже:

```text
ObjectBlobStore(...)
RemoteNodeBlobStore(...)
```

Public domain code этого не замечает.

---

# X. Artifact model

## 34. Идентичность

Путь не является ID.

Минимум:

```python
ArtifactId = str  # opaque globally unique ID
```

Каждый committed artifact получает новый ID. Изменение содержимого создаёт новый artifact.

Если нужно понятие «один логический отчёт во времени», оно моделируется отдельно:

```text
ArtifactCollection / ArtifactSeries / alias
```

а не mutation старого object.

---

## 35. Пример ArtifactDescriptor

```python
@dataclass(frozen=True)
class ArtifactDescriptor:
    artifact_id: str
    kind: str
    name: str
    created_at: datetime

    manifest_digest: str
    media_type: str | None
    total_size: int

    state: str                 # committed / tombstoned / quarantined
    created_by_run_id: str | None
    created_by_actor_id: str | None

    schema_version: str
    labels: dict[str, str]
```

Не стоит превращать базовый descriptor в склад всех UI-полей. `favorite`, `selected`, `unread`, local preview state и т. п. должны жить в client projection/user state.

---

## 36. Artifact part

```python
@dataclass(frozen=True)
class ArtifactPart:
    logical_path: str
    role: str
    media_type: str | None
    blob: BlobRef
    size: int
    digest: str
```

Пример workbook bundle:

```text
artifact a-42
  ├─ report.xlsx        role=primary
  ├─ data.parquet       role=data
  └─ provenance.json    role=metadata
```

---

## 37. Manifest

Пример versioned JSON:

```json
{
  "schema": "stratbox.artifact-manifest/v1",
  "artifact_id": "a-42",
  "kind": "report",
  "name": "Escrow history",
  "parts": [
    {
      "path": "report.xlsx",
      "role": "primary",
      "media_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "digest": "sha256:...",
      "size": 481239
    }
  ]
}
```

Versioned JSON schema особенно важна для AppDock/Android/remote, потому что Python class не должен быть единственным межпроцессным контрактом.

---

# XI. Lifecycle артефакта

## 38. Минимальная state machine

```text
staging
   │ successful commit
   ▼
committed
   │
   ├────────→ superseded (logical relation, content remains valid)
   │
   ├────────→ quarantined (integrity/security problem)
   │
   └────────→ tombstoned
                 │ retention/grace/reference check
                 ▼
               GC physical blobs
```

`superseded` можно хранить не как state, а relation. Главное — committed bytes immutable.

---

## 39. Почему delete должен быть двухфазным

Если удалить physical path сразу, можно уничтожить payload, на который ещё ссылается:

- другой artifact manifest;
- old run;
- audit trail;
- remote client;
- reproducibility record.

Поэтому:

```text
logical delete / tombstone
        ↓
reference + retention check
        ↓
GC
```

---

# XII. Transactional write / commit protocol

## 40. Целевой API

```python
with artifact_store.begin_write(
    kind="report",
    name="Banking report",
    run_id=run_id,
) as draft:
    with draft.open_part("report.xlsx", role="primary") as f:
        build_workbook(f)

    artifact_ref = draft.commit()
```

Если блок завершился исключением и `commit()` не выполнен — draft abort.

---

## 41. Внутренний commit

Рекомендуемая последовательность:

```text
1. создать staging area / lease
2. записать все parts
3. закрыть streams
4. вычислить size + SHA-256
5. верифицировать ожидаемые ограничения
6. записать immutable blobs
7. сформировать canonical manifest
8. записать manifest
9. транзакционно зарегистрировать artifact в catalog
10. emit ArtifactCommitted event
11. очистить staging
```

Ключевой принцип:

> До шага 9 artifact логически не существует для остальных consumers.

Если catalog commit не прошёл, в content store могут остаться orphan blobs. Это безопаснее, чем видимый полуартефакт. Orphans удаляет GC.

---

## 42. Почему нельзя строить commit только на rename

На локальной FS `temp → atomic replace` часто является хорошим примитивом.

На object storage atomic rename может отсутствовать вообще. Поэтому верхняя транзакция должна строиться вокруг **publish manifest/catalog record**, а atomic rename использовать лишь как оптимизацию конкретного backend-а.

Это делает архитектуру действительно универсальной.

---

# XIII. Workspace и ArtifactStore должны сосуществовать

## 43. Правило «workspace mutable, artifact immutable»

Это центральная пользовательская модель.

### Пользователь импортирует файл

```text
workspace/manual.xlsx
     ↓ snapshot/import
artifact://input-1
```

### Операция строит отчёт

```text
artifact://input-1
     ↓ run-100
artifact://report-55
```

### Пользователь хочет открыть/изменить отчёт

```text
artifact://report-55
     ↓ materialize copy
workspace/output/report.xlsx
```

Если пользователь изменил materialized copy:

```text
workspace/output/report.xlsx  # mutable external state
```

Это уже не committed artifact `report-55`.

При желании изменения можно снова импортировать:

```text
workspace/output/report.xlsx
    ↓ import
artifact://report-56
    derived_from = report-55
```

---

## 44. Не каждый workspace-файл обязан становиться artifact

Это важно, иначе система станет тяжёлой.

Scratch, временные выгрузки и пользовательский мусор могут остаться обычными файлами.

Artifact создаётся когда объект нужно:

- зарегистрировать как результат;
- передать;
- воспроизвести;
- сохранить как вход вычисления;
- включить в lineage;
- показать в истории;
- использовать агентом;
- удерживать по retention policy.

---

# XIV. Source snapshots

## 45. Raw source должен быть immutable

Для аналитической системы источник имеет особую ценность. Если внешняя публикация завтра изменится по тому же URL, воспроизводимость требует знать **какие именно bytes были использованы**.

Целевая цепочка:

```text
SourceDescriptor
  source_id
  requested_url
  expected characteristics
        ↓
FetchRun
        ↓
SourceSnapshot
  fetched_at
  final_url
  response metadata
  etag / last_modified if available
  validation result
  artifact_ref ──────────→ immutable raw Artifact
```

---

## 46. SourceSnapshot и Artifact не надо сливать в один класс

Artifact отвечает за object lifecycle и bytes.

SourceSnapshot отвечает за:

- authority/source identity;
- network fetch;
- HTTP metadata;
- source validation;
- freshness/change semantics.

Связь через `ArtifactRef` сохраняет чистые boundaries.

---

# XV. Provenance и lineage

## 47. Минимальная модель

W3C PROV предлагает полезное фундаментальное разделение:

```text
Entity   — данные/артефакт
Activity — действие/расчёт/run
Agent    — человек/система/ИИ
```

Для Strategy Box естественное отображение:

```text
Artifact / SourceSnapshot  ≈ Entity
OperationRun / ScenarioRun ≈ Activity
User / System / AI Agent   ≈ Agent
```

Это не означает, что нужно внедрять полный W3C PROV stack. Достаточно совместимой модели мышления.

---

## 48. Run provenance

Минимальный record:

```python
@dataclass(frozen=True)
class RunProvenance:
    run_id: str
    operation_id: str
    operation_version: str | None
    started_at: datetime
    completed_at: datetime | None

    actor: ActorRef
    inputs: tuple[ArtifactRef, ...]
    outputs: tuple[ArtifactRef, ...]

    parameters_digest: str
    code_revision: str | None
    stratbox_version: str
    environment_id: str | None

    source_snapshots: tuple[str, ...]
    registry_versions: dict[str, str]
    warnings: tuple[str, ...]
```

Parameters можно хранить полностью там, где это безопасно; чувствительные значения должны redaction/hash policy.

---

## 49. Lineage graph

```text
raw source artifact A
         │ used_by
         ▼
      run R1
         │ generated
         ▼
canonical dataset B
         │ used_by
         ▼
      run R2
         │ generated
         ├────────→ report C
         └────────→ chart D
```

OpenLineage полезен как ориентир: он отдельно моделирует Job/Run/Dataset и явные input-output edges. Для Strategy Box это подтверждает ценность run-centric lineage.

---

## 50. Почему lineage нельзя выводить только из папок

Папка:

```text
output/2026/report.xlsx
```

ничего достоверно не говорит:

- каким кодом создана;
- из каких input;
- какой source snapshot использован;
- был ли результат изменён вручную;
- какой registry snapshot применялся.

Lineage — metadata graph, filesystem tree — лишь presentation.

---

# XVI. Artifact Catalog

## 51. Почему нужен индекс

Если manifests просто лежат в каталоге, чтобы найти «все Excel-артефакты сценария X за сентябрь» придётся обходить файловое дерево.

Catalog даёт индексы по:

```text
artifact_id
kind
created_at
run_id
operation_id
case_id
actor_id
media_type
digest
labels
tombstone
```

---

## 52. Что выбрать для desktop/host v1

**SQLite — хороший локальный catalog backend**, если база живёт на локальном диске конкретного node/process environment.

Плюсы:

- одна embedded DB;
- транзакции и atomic commit;
- индексы;
- FK/constraints;
- нормальные запросы;
- backup/export;
- минимум инфраструктуры.

Важное ограничение: SQLite WAL опирается на shared memory и официально не рассчитан на работу через network filesystem между разными hosts. Поэтому metadata database нельзя просто положить в сетевую папку и считать распределённой БД.

Правило:

```text
single node / desktop catalog → local SQLite
shared multi-node catalog     → host service / client-server DB
```

---

## 53. SQLite как index, manifest как portable truth

Очень полезная конструкция:

```text
Content Store:
  immutable artifact manifest

SQLite:
  searchable/indexed projection
```

Тогда:

- artifact можно передать вместе с manifest;
- DB можно пересобрать из manifests при необходимости;
- metadata transport не привязан навечно к SQLite;
- remote host позже может индексировать те же manifests в другой БД.

Не все user-specific поля обязаны входить в portable manifest. Favorite/pin/UI state остаются отдельными projections.

---

# XVII. Артефакты и текущая клиентская модель

## 54. Что должно быть canonical, а что presentation

Канонический artifact слой должен владеть:

- artifact ID;
- immutable manifest;
- content descriptors;
- provenance refs;
- lifecycle state;
- storage resolution;
- materialization.

Client/application слой владеет:

- отображением карточки;
- preview;
- favorite/pin;
- unread;
- selected item;
- context menu;
- user-specific labels;
- local download/open state.

Case/scenario может хранить только `ArtifactRef` + небольшую projection metadata.

---

## 55. Не дублировать canonical Artifact model в Windows и Android

Поскольку Android должен наследовать стандартные сегменты Strategy Box, canonical artifact contracts должны находиться в toolkit-neutral Python/core слое и иметь versioned JSON representation.

Windows/Android строят собственные view models:

```text
ArtifactDescriptor
      ↓ project
ArtifactCardViewModel
```

Это избавит будущий Android от копирования semantically-critical logic.

---

# XVIII. AppDock и удалённый execution

## 56. Артефакт как естественная граница local/remote

Сегодня path-centric local execution может вернуть:

```text
C:\...\output\report.xlsx
```

Для remote host это бессмысленно.

Правильный result:

```text
ArtifactRef("a-42")
```

Дальше клиент может:

- показать metadata;
- запросить preview;
- скачать primary part;
- materialize на локальный диск;
- передать artifact следующей операции;
- оставить payload на host и не качать тяжёлый dataset вообще.

---

## 57. Remote artifact transport

Будущий AppDock boundary может давать операции вида:

```text
resolve artifact
get descriptor
stream part
request materialization
publish artifact
```

При поддержке backend-а можно выдавать short-lived signed URL. При других backend-ах AppDock host проксирует поток.

Core не должен знать, какой именно механизм используется.

---

## 58. Mobile становится намного проще

Android surface обычно не нужен полный network filesystem.

Ему нужны:

```text
list recent artifacts
show metadata/preview
open/download selected artifact
approve downstream action
launch operation using artifact refs
```

Artifact API естественно подходит мобильному клиенту. FileStore API — гораздо хуже.

---

# XIX. ИИ-агенты

## 59. Агенту нельзя давать файловую систему как основной API

Если AI получает «вот root directory, делай что хочешь», система сталкивается с:

- слишком широкими permissions;
- path traversal/destructive risks;
- слабым audit trail;
- отсутствием semantic context;
- трудной remote portability;
- невозможностью понять, что агент считал входом и что создал результатом.

Целевой путь:

```text
AI Agent
   ↓
Operation Catalog / Artifact Catalog
   ↓
read permitted artifact metadata
   ↓
request controlled content access
   ↓
run permitted operation / create draft artifact
   ↓
commit artifact
   ↓
provenance + audit
```

---

## 60. Agent capabilities

Пример разрешений:

```text
artifact.search
artifact.inspect
artifact.read_content
artifact.materialize
artifact.create_draft
artifact.commit
artifact.derive
artifact.request_delete
operation.run
```

`artifact.delete_physical` агенту обычно вообще не нужен.

---

## 61. Scratch для агента

Агенту всё равно может понадобиться файловое scratch space.

Правильная модель:

```text
agent sandbox scratch
  mutable, temporary, limited quota
        ↓ explicit publish
Artifact draft
        ↓ commit
Committed Artifact
```

То, что агент временно создал десять промежуточных файлов, не означает, что все они стали артефактами продукта.

---

## 62. Provenance AI output

Для output полезно фиксировать:

- actor kind = AI;
- agent identity/version;
- operation/tool IDs;
- input ArtifactRefs;
- model/provider identity там, где это разрешено;
- parameter/config digest;
- approvals;
- результат проверки/validation.

Полные prompts, secrets и чувствительный контекст **не следует автоматически писать в manifest**. Для них нужна отдельная redaction/audit policy.

---

# XX. Security и governance

## 63. Artifact policy

У descriptor желательно иметь нейтральные policy fields/labels:

```text
classification
sensitivity
retention_class
owner_scope
share_policy
```

Конкретная корпоративная policy реализуется внешним environment layer.

---

## 64. Immutable does not mean undeletable

Immutable означает:

> committed content не редактируется in-place.

Lifecycle всё равно может разрешать:

- tombstone;
- retention expiry;
- legal/security deletion;
- garbage collection.

Удаление должно быть auditable и reference-aware.

---

## 65. Integrity verification

При чтении remote/untrusted payload:

```text
expected size
expected digest
actual size
actual digest
```

Несовпадение → `ArtifactIntegrityError`, а не warning.

OCI descriptors прямо используют digest и size для проверки content identity; этот pattern хорошо подходит Strategy Box.

---

# XXI. Кэш

## 66. Cache не равен ArtifactStore

Cache можно удалить.

ArtifactStore — persistent logical state.

Примеры cache:

- downloaded decompressed copy;
- parsed DataFrame serialization;
- preview image;
- remote artifact local copy;
- compiled SORS topology;
- HTTP response cache.

Если очистка cache уничтожает единственную копию committed artifact — это уже не cache.

---

## 67. Cache key

Хороший cache key строится из immutable identities:

```text
input artifact digest(s)
operation version
parameters digest
registry/source schema versions
```

Это намного надёжнее, чем cache «по имени файла и mtime».

---

# XXII. Directory artifacts и bundles

## 68. Не считать directory физической сущностью

На filesystem directory настоящий. На object store — обычно prefix.

Поэтому composite artifact моделируется manifest-ом:

```text
parts = [
  {path: "data/a.parquet", digest: ...},
  {path: "data/b.parquet", digest: ...},
  {path: "README.md", digest: ...}
]
```

`materialize()` уже решает, как построить реальную директорию.

---

## 69. Bundle и ZIP — разные вещи

Logical bundle:

```text
Artifact with multiple parts
```

ZIP:

```text
one serialized representation of that bundle
```

Не надо заставлять every multi-file artifact всегда физически становиться ZIP. ZIP можно генерировать как export/materialization.

---

# XXIII. DataFrame и datasets

## 70. Не все результаты должны сразу становиться Excel

Core уже движется к canonical data раньше presentation. Artifact layer должен поддержать это.

Например:

```text
OperationResult
  canonical_data: in-memory / structured result
  artifacts:
    - dataset artifact (Parquet)
    - report artifact (XLSX)
```

Excel — presentation artifact, а не единственный container данных.

---

## 71. Рекомендуемые storage formats

Архитектура не должна навязывать один формат, но для structured datasets полезны:

- Parquet — большие typed tables;
- CSV — переносимый human-readable interchange;
- JSON/JSONL — metadata/events/records;
- XLSX — user-facing report;
- ZIP — transport bundle.

Artifact manifest хранит media type/format и schema metadata отдельно от physical filename.

---

# XXIV. Operation Result и artifacts

## 72. Result envelope

Общий result не должен сводиться к paths.

```python
@dataclass
class OperationResult:
    status: str
    value: object | None
    artifacts: tuple[ArtifactRef, ...]
    warnings: tuple[Diagnostic, ...]
    failures: tuple[Diagnostic, ...]
    metrics: dict[str, object]
    provenance: RunProvenance | None
```

Rich domain result может иметь дополнительные поля.

---

## 73. Side effects должны быть декларативны

Operation descriptor уже естественно может объявлять:

```text
reads_artifacts
writes_artifacts
uses_network
uses_workspace
mutates_workspace
creates_managed_artifacts
destructive
```

Это пригодится:

- UI;
- AppDock permissions;
- AI tool exposure;
- preflight;
- remote execution planning.

---

# XXV. Public provider architecture

## 74. Что должен знать public core

Только нейтральные interfaces:

```text
FileStore
BlobStore (если материализуется как public extension point)
ArtifactCatalog
ArtifactStore / ArtifactService
StorageCapabilities
Storage errors
```

Их конкретные реализации обнаруживаются через runtime/provider mechanism.

---

## 75. Что нельзя переносить в public core

- названия конкретной внутренней сети;
- конкретные host/share identifiers;
- закрытые authentication mechanics;
- внутренние gateways;
- package names закрытых расширений;
- внутренние policy names.

Публичная документация может говорить:

```text
environment-specific storage provider
private capability pack
organization-specific secret provider
managed remote storage backend
```

Этого достаточно.

---

# XXVI. Предлагаемая структура `stratbox`

## 76. Целевая структура

С учётом того, что обратная совместимость не нужна, я бы сделал storage/artifacts/provenance полноценными top-level слоями вместо дальнейшего разрастания `base`:

```text
stratbox/
│
├─ storage/
│  ├─ contracts.py
│  ├─ capabilities.py
│  ├─ errors.py
│  ├─ locators.py
│  ├─ filesystem/
│  │  ├─ base.py
│  │  └─ local.py
│  └─ blob/
│     ├─ base.py
│     └─ filestore_cas.py
│
├─ artifacts/
│  ├─ models.py
│  ├─ manifest.py
│  ├─ catalog.py
│  ├─ service.py
│  ├─ writer.py
│  ├─ materialize.py
│  ├─ retention.py
│  └─ gc.py
│
├─ provenance/
│  ├─ models.py
│  └─ graph.py
│
├─ sources/
│  ├─ contracts.py
│  ├─ fetch.py
│  ├─ snapshots.py
│  └─ validation.py
│
├─ operations/
│  ├─ contracts.py
│  ├─ results.py
│  └─ registry.py
│
├─ registries/
├─ macrobanks/
└─ text/
```

Это лучше отражает фактический вес инфраструктурных concepts в продукте.

---

## 77. Почему `artifacts` не надо держать только в desktop repo

Artifact identity нужен:

- core operations;
- tests;
- CLI/headless;
- AppDock host;
- Windows;
- Android;
- AI agent runtime.

Следовательно, canonical model принадлежит core/platform-neutral layer.

Desktop repo должен хранить только application projection и presentation.

---

# XXVII. Предлагаемая структура client layer

## 78. Универсальный клиент

```text
application/
  artifacts/
    queries.py
    actions.py
    projections.py

presentation/common/
  artifacts/
    models.py
    preview.py
    formatting.py
```

Windows:

```text
presentation/qt_desktop/artifacts/
```

Android:

```text
presentation/android/artifacts/
```

Оба используют один `ArtifactDescriptor`/JSON contract.

---

# XXVIII. Metadata ownership

## 79. Три класса metadata

### A. Immutable canonical metadata

В manifest:

- artifact ID;
- parts;
- digests;
- size;
- kind;
- created_at;
- creation/run refs;
- schema version.

### B. Operational lifecycle metadata

В catalog:

- state;
- tombstone;
- storage locations;
- retention;
- indexes;
- GC state.

### C. User/UI metadata

В client/user state:

- favorite;
- pinned;
- unread;
- selected;
- local open history;
- custom display grouping.

Так manifest не загрязняется UI-состоянием.

---

# XXIX. Artifact kinds

## 80. Не делать огромную жёсткую enum

Базовый vocabulary может быть компактным:

```text
file
bundle
dataset
report
source_snapshot
image
archive
log
model
diagnostic
other
```

Плюс:

```text
media_type
semantic_type / labels
```

Например:

```text
kind=report
media_type=...xlsx
semantic_type=cbr.escrow.history
```

Это масштабируется лучше сотни enum values.

---

# XXX. Preview

## 81. Preview как отдельная производная возможность

Preview не следует хранить внутри основного artifact payload по умолчанию.

Сервис может создавать cache/derived artifact:

```text
XLSX → table summary / thumbnail
PDF  → first pages image
CSV  → schema + head
Image → thumbnail
ZIP  → contents index
```

AI и mobile часто смогут работать с preview/metadata без загрузки полного файла.

---

# XXXI. Поиск

## 82. Catalog query API

```python
artifact_catalog.search(
    kind="report",
    operation_id="escrow.history.export",
    created_after=...,
    labels={"period": "2026-09"},
)
```

Позже можно добавить full-text search по безопасным metadata.

Поиск по содержимому файлов — отдельная задача и не должен автоматически входить в первый artifact layer.

---

# XXXII. Retention и garbage collection

## 83. Retention classes

Пример нейтральных классов:

```text
ephemeral
cache
standard
important
source_snapshot
audit
pinned
```

Конкретные сроки задаёт policy layer.

---

## 84. Reference-aware GC

Blob удаляется только если:

```text
no live artifact manifest references it
AND grace period passed
AND no active lease/upload/download
AND policy allows deletion
```

Content-addressability делает этот процесс естественным.

---

# XXXIII. Recovery

## 85. Staging leases

Каждая незавершённая write session получает:

```text
draft_id
created_at
owner run/process
lease expiry
staging paths
```

После crash startup recovery может:

- завершить явно recoverable commit;
- либо abort и очистить старый staging.

Никогда нельзя автоматически считать staging artifact committed только потому, что какие-то файлы существуют.

---

# XXXIV. Concurrency

## 86. Logical atomicity важнее backend atomicity

Catalog transaction определяет момент публикации artifact.

Два writers могут одновременно upload одинаковый blob — CAS dedup сделает это безопасным при корректной conditional create/verification.

Artifact ID collision практически исключается opaque UUID-like identity.

---

## 87. Locks

Нужны только там, где есть mutable shared state:

- catalog migrations;
- GC leases;
- mutable aliases/collections;
- workspace mutations.

Immutable blobs и manifests можно проектировать максимально lock-free.

---

# XXXV. Версионирование contracts

## 88. Что versioned обязательно

```text
artifact manifest schema
provenance schema
source snapshot schema
catalog schema
remote artifact API contract
```

Отдельно versioned domain schema для datasets.

---

## 89. Schema evolution

Reader должен понимать свой набор поддерживаемых manifest versions.

При major incompatible изменении:

```text
v1 manifest остаётся immutable
new code может читать v1 через adapter
new writes создают v2
```

Здесь backward readability исторических артефактов важнее «обратной совместимости API» — это разные вещи. Даже если код проекта свободно ломает старые Python interfaces, уже созданные durable artifacts нельзя делать нечитаемыми без migration path.

---

# XXXVI. Что делать с текущими JSON history projections

## 90. Не превращать Artifact Catalog в общий монолит state database сразу

Текущие cases/events/logs/assignments имеют свою application семантику.

На первом этапе:

- Artifact Catalog хранит canonical artifact metadata;
- case history хранит `ArtifactRef`;
- отдельная migration к единому Run/Case database возможна позже.

Это снижает scope и позволяет быстро получить ценность.

---

# XXXVII. Сценарий end-to-end

## 91. Пример: загрузка официальной статистики → расчёт → Excel

```text
1. Operation A получает SourceDescriptor.

2. Fetch сохраняет bytes в artifact draft.

3. Validation проходит.

4. Commit:
   source raw Artifact A1
   SourceSnapshot S1 → A1

5. Operation B читает A1 через ArtifactStore.

6. Parser строит canonical dataframe.

7. Canonical dataset фиксируется как Artifact A2 (например Parquet).

8. Provenance:
   A1 --used_by--> Run B --generated--> A2

9. Operation C строит Excel report Artifact A3 из A2.

10. Windows показывает A3 в case.

11. Пользователь нажимает «Открыть».

12. ArtifactService materialize A3 в workspace/output/report.xlsx.

13. Android видит тот же A3 по ArtifactRef, даже если физически он остался на host.

14. AI получает разрешение read A2 и запускает следующую operation,
    не получая полный доступ к host filesystem.
```

Это и есть тот уровень универсальности, к которому логично вести Strategy Box.

---

# XXXVIII. Что не стоит делать

## 92. Антипаттерны

### 92.1. Path as identity

```text
"C:\\...\\report.xlsx" == artifact
```

Нет.

### 92.2. Один гигантский FileStore

Не добавлять туда provenance, tags, run IDs, favorites, approvals и AI permissions.

### 92.3. Silent fallback errors

Storage layer должен быть строгим.

### 92.4. Copy+delete как скрытая семантика `rename`

Если backend не умеет safe move, capability должен это показать. Copy+delete — отдельная операция с verification.

### 92.5. Artifact = ZIP

Bundle не обязан быть ZIP.

### 92.6. Mutable committed artifact

Любое изменение создаёт новую immutable identity.

### 92.7. SQLite database на сетевой шаре как «multi-user server»

Для shared multi-host нужна сервисная/серверная БД.

### 92.8. Agent root filesystem access by default

Agent должен получать semantic capabilities.

### 92.9. Sidecar metadata как единственный catalog

Sidecars полезны для portability/export, не для основного query/state layer.

### 92.10. Artifact model только в GUI

Canonical artifacts должны существовать headless.

---

# XXXIX. Вопрос: нужно ли сразу делать физический CAS

## 93. Моя рекомендация — да, но маленький

Можно было бы сначала записывать managed artifacts обычными именами и только считать hash. Но поскольку:

- обратная совместимость не требуется;
- слой сейчас проектируется концептуально;
- CAS поверх FileStore технически прост;
- source snapshots особенно выигрывают от immutable hash identity;
- будущий remote transport всё равно потребует integrity;

я бы сразу сделал **минимальный SHA-256 content store**.

Без S3, registry server и сложной распределённости.

Просто:

```text
BlobRef = sha256 + size
FileBlobStore = CAS layout over FileStore
Artifact manifest = immutable JSON
ArtifactCatalog = SQLite index
```

Это даст правильный фундамент почти без тяжёлой инфраструктуры.

---

# XL. Где физически хранить managed artifacts

## 94. На desktop/node

Логически:

```text
<managed-data-root>/
  workspace/
  artifacts/
    blobs/
    manifests/
  cache/
  staging/
  metadata/
    artifacts.sqlite
```

Фактические roots должны определяться runtime/AppDock/environment provider.

Важно: catalog DB желательно на локальном node storage. Payload blobs могут находиться в другом FileStore/backend.

---

## 95. Metadata и payload могут жить раздельно

Это нормальная архитектура и распространённый pattern. MLflow, например, явно разделяет backend store с параметрами/метриками/tags и artifact store для крупных файлов.

Для Strategy Box:

```text
ArtifactCatalog → small structured metadata
BlobStore       → large bytes
```

Это позволит позднее переносить blobs на remote/object storage без переписывания metadata model.

---

# XLI. Миграционный путь от текущего состояния

## 96. Этап 0 — зафиксировать vocabulary и ADR

До кода принять решения:

1. FileStore остаётся low-level.
2. Workspace и managed artifacts разделяются.
3. Committed artifact immutable.
4. Artifact ID не равен path.
5. SHA-256 является canonical content digest.
6. Artifact manifest versioned.
7. Catalog и payload разделены.
8. SourceSnapshot ссылается на ArtifactRef.
9. Operations возвращают ArtifactRefs.
10. Agent API работает с operations/artifacts.

---

## 97. Этап 1 — выпрямить FileStore

Добавить/переработать:

- строгую error taxonomy;
- `StorageCapabilities`;
- настоящий streaming contract;
- `commit/abort` semantics для writes;
- checksum/metadata hooks;
- безопасную cross-store copy primitive;
- typed locator/path;
- test contract suite для каждого provider.

Не добавлять artifact metadata в FileStore.

---

## 98. Этап 2 — BlobStore + manifest

Реализовать:

```text
BlobRef
BlobStore Protocol
FileBlobStore CAS
ArtifactManifest v1
manifest canonical serialization
SHA-256 verification
```

Покрыть tests:

- duplicate content;
- interrupted write;
- wrong digest;
- multi-file manifest;
- materialization.

---

## 99. Этап 3 — ArtifactCatalog + ArtifactService

SQLite schema:

```text
artifacts
artifact_parts
artifact_relations
artifact_locations
run_artifacts
labels
retention/tombstones
```

ArtifactService:

```text
begin_write
commit
abort
get
search
open_part
materialize
import_file
snapshot_workspace_file
tombstone
```

---

## 100. Этап 4 — подключить operations

Первыми мигрировать 2–3 операции с понятными outputs.

OperationResult начинает возвращать:

```text
artifacts: [ArtifactRef]
```

Path остаётся только как optional materialization/output compatibility на короткий период разработки; с учётом правила проекта его затем можно удалить.

---

## 101. Этап 5 — SourceSnapshot/provenance

Связать:

```text
source fetch
raw Artifact
SourceSnapshot
RunProvenance
canonical dataset Artifact
report Artifact
```

Это даст первый полноценный end-to-end lineage.

---

## 102. Этап 6 — client projection

Windows:

- artifact cards получают stable ID;
- open → materialize;
- explorer различает workspace files и managed artifacts;
- recent artifacts запрашиваются из catalog;
- case хранит ArtifactRef.

Android сможет использовать те же descriptors позднее.

---

## 103. Этап 7 — remote host

Ввести:

```text
ArtifactTransport / RemoteArtifactClient
ExecutionBackend returns ArtifactRefs
```

Не передавать remote paths как public API.

---

## 104. Этап 8 — AI permissions

Agent tools поверх:

- operation registry;
- artifact catalog;
- artifact read/derive/commit;
- explicit policy/approval.

---

# XLII. Тестовая стратегия

## 105. Contract tests FileStore

Каждая реализация должна пройти один набор тестов:

```text
read/write
streaming
stat/list
missing vs denied vs unavailable
capabilities truthfulness
commit/abort
safe delete/move
large file chunks
unicode paths
concurrent readers
```

Тесты, зависящие от capability, условные, но unsupported не должен превращаться в false success.

---

## 106. Artifact invariants

Property/invariant tests:

1. committed artifact никогда не меняет manifest digest;
2. wrong content не проходит digest verification;
3. failed write не создаёт visible artifact;
4. identical bytes дают один BlobRef;
5. deletion artifact не удаляет shared blob;
6. materialization reproduces exact bytes;
7. manifest round-trip deterministic;
8. provenance edges ссылаются только на существующие committed refs;
9. GC не удаляет referenced blobs;
10. catalog rebuild из manifests сохраняет canonical identity.

---

## 107. Failure injection

Особенно важны тесты crash points:

```text
after staging write
mid-upload
after blob commit
before manifest write
after manifest write
before catalog commit
after catalog commit
before staging cleanup
```

Система должна после каждого сценария приходить к понятному recoverable состоянию.

---

# XLIII. Observability

## 108. Storage/artifact events

Полезный neutral event vocabulary:

```text
artifact.draft_started
artifact.part_written
artifact.committed
artifact.materialized
artifact.tombstoned
artifact.gc_deleted
artifact.integrity_failed
storage.backend_unavailable
storage.authentication_required
```

Логи не должны раскрывать credentials или чувствительные locator details без необходимости.

---

# XLIV. Стоит ли делать единый `Resource` abstraction

## 109. Теоретически можно, практически пока не надо

Можно придумать:

```text
ResourceRef
├─ ArtifactRef
├─ WorkspaceRef
├─ SourceRef
└─ ExternalUrlRef
```

Это пригодится на operation boundary.

Однако не стоит строить giant Resource hierarchy раньше реальных consumers. Достаточно отдельных маленьких refs и union/type alias там, где операция принимает несколько видов входа.

Главная опасность архитектуры Strategy Box на этом этапе — чрезмерно универсальные абстракции раньше практической необходимости.

---

# XLV. Сравнение ролей по слоям

## 110. Ownership matrix

| Concern | `stratbox` | client (Windows/Android) | AppDock | environment provider |
|---|---|---|---|---|
| FileStore Protocol | **owns** | consumes | observes capability | implements/adapts |
| storage errors/capabilities | **owns** | renders | health/preflight | supplies truth |
| Blob/Artifact contracts | **owns** | consumes/projects | transports/exposes | may back storage |
| Artifact manifest schema | **owns** | reads | transports | neutral |
| Artifact catalog API | **owns** | queries | may proxy remotely | backend optional |
| workspace UX | contract only | **owns UX** | supplies roots | — |
| artifact preview UI | — | **owns** | — | — |
| source semantics | **owns** | displays | — | network capability only |
| provenance | **owns canonical** | projects | audit transport | — |
| remote execution | operation contract | client | **orchestrates/hosts** | capabilities |
| AI permission exposure | operation metadata | approvals/UI | **boundary/policy** | capabilities |
| corporate/internal mechanics | **never** | **never** | generic only | **owns privately** |

---

# XLVI. Почему это не «слишком сложно»

## 111. Минимальная реализация реально небольшая

MVP целевой модели требует всего нескольких частей:

```text
1. строгий FileStore
2. SHA-256 BlobRef
3. FileBlobStore CAS
4. ArtifactManifest
5. SQLite ArtifactCatalog
6. ArtifactService commit/materialize
7. ArtifactRef в OperationResult
```

Не нужны сразу:

- S3;
- PostgreSQL;
- Kubernetes;
- Kafka;
- отдельный artifact server;
- полноценный OpenLineage service;
- глобальная распределённая БД.

Архитектура становится шире, инфраструктура может оставаться маленькой.

---

# XLVII. Архитектурные решения, которые я рекомендую принять

## 112. Decision set

### D1. Оставить `FileStore`

**Да.** Он правильный фундамент physical storage abstraction.

### D2. Ограничить ответственность FileStore

**Да.** Только files/paths/streams/capabilities/errors.

### D3. Ввести `ArtifactStore`/`ArtifactService`

**Да, как следующий ключевой слой.**

### D4. Разделить Workspace и managed artifacts

**Обязательно.**

### D5. Committed artifacts immutable

**Обязательно.**

### D6. Path не является artifact identity

**Обязательно.**

### D7. SHA-256 для content identity

**Да.**

### D8. Минимальный CAS поверх FileStore с первого цикла

**Да.** Это небольшой дополнительный объём и сильный фундамент.

### D9. SQLite как локальный artifact catalog

**Да**, только на локальном node storage; shared multi-node → service/server DB.

### D10. Manifest хранить как portable immutable JSON

**Да.** Catalog — индекс, manifest — переносимое описание.

### D11. `SourceSnapshot` связывать с ArtifactRef

**Да.** Не с raw path.

### D12. Operation outputs возвращать ArtifactRefs

**Да.** Это основа remote/mobile/AI.

### D13. Provenance строить run-centric

**Да.** `inputs → Run → outputs`.

### D14. Agent access строить поверх Artifact/Operation API

**Да.** FileStore только как restricted capability/sandbox primitive.

### D15. fsspec использовать как optional adapter/inspiration

**Да.** Не делать зависимостью архитектуры.

### D16. AppDock не должен знать storage internals

**Да.** Только capabilities, references, transport, health и разрешённые actions.

---

# XLVIII. Самый важный эффект для Strategy Box

## 113. Сегодня продукт мыслит результат как файл

```text
run → output/report.xlsx
```

## 114. Целевая модель мыслит результат как доказуемый объект

```text
Run R
├─ used Artifact A
├─ used SourceSnapshot S
├─ parameters P
├─ code/version V
└─ generated Artifact B
      ├─ immutable ID
      ├─ manifest
      ├─ sha256
      ├─ metadata
      ├─ lineage
      └─ one or more materializations
```

Это качественно другой уровень продукта.

Именно такая модель позволяет Strategy Box стать не только desktop-программой, которая что-то выгружает в Excel, а **управляемой аналитической средой**, где результаты можно надёжно повторять, связывать, переносить между узлами, показывать на мобильном клиенте и безопасно отдавать ИИ-агентам.

---

# XLIX. Приоритетный roadmap

## 115. P0 — storage semantics

1. FileStore error model.
2. Capabilities.
3. Streaming.
4. Commit/abort write.
5. Contract tests.

## 116. P0 — artifact foundation

1. BlobRef SHA-256.
2. CAS over FileStore.
3. Manifest v1.
4. ArtifactRef/Descriptor.
5. SQLite catalog.
6. ArtifactService.

## 117. P1 — core integration

1. OperationResult artifacts.
2. SourceSnapshot → ArtifactRef.
3. Run provenance.
4. 2–3 pilot domains.
5. Materialization to workspace.

## 118. P1 — universal client

1. Canonical artifact refs instead of paths in cases.
2. Artifact query service.
3. Preview/materialization.
4. Toolkit-neutral projections.

## 119. P2 — remote/mobile

1. Artifact transport protocol.
2. ExecutionBackend returns refs.
3. Host-side payload retention.
4. Android artifact browser/download/open.

## 120. P2 — AI

1. Artifact search/read tools.
2. Draft/commit.
3. Operation invocation by ArtifactRef.
4. Policy/approval.
5. Agent provenance.

## 121. P3 — scale

1. client-server catalog backend.
2. object storage BlobStore.
3. signed URLs.
4. cross-node replication.
5. richer lineage query/visualization.

---

# L. Короткий ответ на исходный вопрос

## 122. Правильно ли выбрали FileStore?

**Да.** Он нужен и архитектурно оправдан.

Ошибка была бы лишь в одном случае: если считать, что FileStore и есть весь будущий слой работы с данными/результатами.

Целевая формула:

```text
FileStore
  = «как работать с физическим файловым пространством»

BlobStore
  = «как хранить immutable content objects»

ArtifactStore
  = «как создавать и разрешать устойчивые результаты»

ArtifactCatalog
  = «как находить и связывать результаты»

Provenance
  = «откуда результат взялся»

Workspace
  = «где человек свободно работает с файлами»
```

А для Strategy Box в целом:

```text
Sources → Snapshots → Artifacts → Operations → Artifacts
                    ↘ Provenance ↗

Workspace ←→ Materialization

Windows / Android / AI / Remote Host
            ↓
       ArtifactRefs
            ↓
       Artifact Service
            ↓
   Catalog + Content Store
            ↓
         FileStore
```

Это и есть наиболее универсальная и масштабируемая форма слоя файлов и артефактов для текущего направления продукта.

---

# LI. Внешняя техническая сверка

Ниже перечислены источники, использованные не как готовая архитектура для копирования, а как проверка отдельных engineering patterns.

## 123. fsspec

**Filesystem interfaces for Python**  
https://filesystem-spec.readthedocs.io/

Релевантно:

- единый filesystem interface для local/remote/embedded storage;
- protocol-based implementations;
- file-like access;
- caching/async;
- transaction context с deferred commit/discard.

Особенно:

https://filesystem-spec.readthedocs.io/en/latest/features.html

---

## 124. MLflow Artifact Stores

https://mlflow.org/docs/latest/self-hosting/architecture/artifact-store/

Релевантен принцип разделения:

```text
backend metadata store
artifact payload store
```

MLflow хранит крупные run artifacts отдельно от parameters/metrics/tags metadata.

---

## 125. OCI Content Descriptor / Image Spec

https://specs.opencontainers.org/image-spec/descriptor/

Релевантен компактный content descriptor:

```text
mediaType
digest
size
```

и content-addressed verification.

OCI layout также показывает полезное разделение content-addressable blobs и location-addressable refs/manifests.

---

## 126. DVC content-addressable cache

https://dvc.org/doc/user-guide/project-structure/internal-files

Релевантны:

- hash-addressed cache;
- dedup одинакового content;
- directory manifest, состоящий из hashes отдельных файлов;
- разделение workspace representation и internal content store.

---

## 127. W3C PROV

https://www.w3.org/TR/prov-dm/

Релевантна модель:

```text
Entity
Activity
Agent
wasDerivedFrom / wasGeneratedBy / used / attribution
```

Она хорошо отображается на Strategy Box artifacts/runs/actors.

---

## 128. OpenLineage

https://openlineage.io/docs/spec/

Релевантны:

- Run;
- Job;
- Dataset;
- input/output lineage;
- explicit run state events.

Полный OpenLineage stack для Strategy Box сейчас не требуется; полезна его модель границ.

---

## 129. Amazon S3 semantics

https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-files-synchronization.html

Релевантное архитектурное ограничение: object storage не обязан иметь native directories и atomic rename; move может означать copy+delete. Поэтому FileStore должен иметь capability model, а Artifact commit нельзя строить исключительно на filesystem rename.

---

## 130. SQLite atomicity / WAL

https://www.sqlite.org/atomiccommit.html  
https://www.sqlite.org/wal.html

Релевантно:

- transactional atomic commit;
- WAL concurrency на одном host;
- ограничение WAL для network filesystems.

Отсюда рекомендация держать desktop/node catalog локально и переходить к service/client-server DB для настоящего multi-host режима.

---

# LII. Внутренние материалы Strategy Box, использованные при синтезе

Исследование опиралось на предоставленные в проекте актуальные срезы от 2026-10-06:

- `stratbox_base_study_current_state_2026-10-06.md`;
- `stratbox-windows_current_state_full_research_2026-10-06.md`;
- базовое описание AppDock;
- внутреннее исследование environment-specific capability layer использовано только как источник общих требований к provider boundary, storage semantics, readiness и безопасности; конкретное устройство закрытой реализации в этом документе сознательно не раскрывается.

---

# LIII. Финальная рекомендация

Если свести всё исследование к одному архитектурному решению, я бы зафиксировал следующее:

> **Strategy Box должен сохранить FileStore как нейтральный физический filesystem contract, но поверх него построить отдельный immutable Artifact System с content-addressed payloads, versioned manifests, локальным metadata catalog, run-centric provenance и materialization в mutable Workspace. Все удалённые, мобильные и AI-сценарии должны оперировать ArtifactRefs и разрешёнными operations, а не сырыми путями.**

Это решение достаточно маленькое для ближайшей реализации и одновременно не упирается в архитектурный потолок при переходе к host execution, Android, нескольким storage backend, крупным данным и ИИ-агентам.
