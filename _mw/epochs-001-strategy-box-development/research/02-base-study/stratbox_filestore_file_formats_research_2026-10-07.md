# Strategy Box: FileStore, форматы файлов и целевой форматный контур

**Research branch:** вторая ветка исследований Strategy Box  
**Дата:** 2026-10-07  
**Статус:** Research Result — исследовательский материал проекта; в репозитории не размещался  
**Область:** `stratbox` + `stratbox-windows` + будущий `stratbox-android`; AppDock рассматривается только как внешняя продуктовая граница для сравнения подходов

---

# 0. Краткий вывод

Главный вывод исследования: **FileStore не должен “поддерживать XLSX, PDF, DBF, XBRL и т. п.” в смысле знания их внутреннего устройства.** FileStore должен оставаться нейтральным транспортом файлов и каталогов: пути, потоки, байты, stat, list, copy, move, delete, checksum, atomic write, materialization. Форматы должны жить этажом выше.

Целевая модель для Strategy Box:

```text
FileStore
  физически хранит и переносит любые байты
        ↓
Format Registry / Detection
  определяет тип, контейнер, MIME, сигнатуру, возможности
        ↓
Generic Codecs
  CSV / Excel / DBF / XML / JSON / archives / documents...
        ↓
Semantic Adapters
  XBRL / SDMX / конкретные схемы регуляторов
        ↓
Domain Operation
  заранее определённый алгоритм Strategy Box
        ↓
Canonical Result / Artifact
```

Это принципиально отличается от универсальной интеллектуальной файловой работы. Strategy Box не должен получать файл и “решать, что с ним сделать”. Операция заранее знает:

- какие форматы она принимает;
- какую схему ожидает;
- какие листы/таблицы/поля читает;
- какие проверки выполняет;
- какой результат обязана вернуть;
- какие форматы результата допустимы.

Поэтому задача на старте — не построить AI-файловый комбайн, а сформировать **достаточно широкий, но конечный сертифицированный форматный контур**.

Моя итоговая рекомендация:

1. FileStore сделать полностью format-agnostic.
2. Ввести единый `FormatRegistry` в `stratbox`; `stratbox-windows` и будущий Android должны читать именно его, а не держать собственные списки расширений.
3. Сразу заложить широкий реестр входных форматов: Excel-семейство, CSV/TSV, JSON/JSONL, XML, HTML/XHTML, DBF, ODS, PDF, DOCX, PPTX, TXT/MD, ZIP/RAR/7z/TAR/GZip, изображения, XBRL/iXBRL/xBRL-CSV/xBRL-JSON, SDMX-представления.
4. Отдельно предусмотреть современные машинные форматы (`Parquet`) и несколько классов редких источников как optional capabilities.
5. Принять принцип **read broad / write narrow**. На выходе по умолчанию: XLSX, CSV/TSV, JSON/JSONL, TXT/MD, ZIP; Parquet — для больших машинных наборов. Остальные writers — только под конкретную операцию.
6. Полностью отказаться от runtime auto-pip в продуктовой поставке. Все поддерживаемые capabilities должны устанавливаться заранее.
7. Все контейнерные и крупные форматы перевести с модели “прочитать всё в RAM” на materialize/stream.
8. XBRL и SDMX считать не расширениями файлов, а **семействами стандартов поверх XML/CSV/JSON/ZIP**.
9. PDF/DOCX/PPTX считать документными форматами с ограниченными детерминированными операциями, а не универсальным источником таблиц.
10. Встроить форматные требования в `OperationSpec`, чтобы UI сам показывал правильный file picker и отклонял несовместимые файлы ещё до запуска алгоритма.

---

# 1. Постановка задачи

Strategy Box — не универсальная файловая оболочка. Его основная модель — набор заранее определённых аналитических и операционных алгоритмов. Пользователь выбирает сценарий, задаёт параметры и получает заранее определённый класс результата.

Из этого следует важное ограничение:

> Поддержка формата в Strategy Box означает не “система умеет интеллектуально разобраться с любым файлом этого типа”, а “для этого формата существует заранее известный безопасный технический путь и хотя бы одна операция, которая понимает ожидаемую структуру”.

Пример:

```text
операция: cbr.forms.build
вход: ZIP с DBF конкретной формы Банка России
действие: извлечь → распознать схему → построить canonical long → проверить → экспортировать
выход: XLSX + provenance
```

Здесь ZIP и DBF — технические форматы. Семантика формы 0409101/0409802 — доменная логика.

Другой пример:

```text
операция: xbrl.report.extract_facts
вход: XBRL instance / report package
действие: открыть taxonomy → validate → extract facts → canonical fact table
выход: Parquet/CSV/XLSX + validation report
```

В этом случае простого XML parser недостаточно: нужен полноценный XBRL processor.

---

# 2. Что уже есть в `stratbox`

На исследованном актуальном `main` (`stratbox` 0.8.0) `FileStore` уже проведён по правильной границе:

```text
FileStore:
- open_read / open_write
- exists / is_file / is_dir
- stat / listdir
- makedirs
- remove / rmdir / rmtree
- rename
- read_bytes / write_bytes
- copy
- walk
- glob
```

Сам интерфейс прямо декларирует принцип: FileStore отвечает за файлы и каталоги, а `pandas/openpyxl` и другие форматы живут выше, в `ioapi`.

Это правильная база, её нужно усиливать, а не ломать.

## 2.1. Текущий `ioapi`

Фактически существуют модули:

```text
archives
bytes
csv
dbf
docx
excel
excel_xls
excel_xlsb
excel_xlsm
excel_xlsx
images
pdf
pptx
rar
txt
xml
zip
```

Текущее фактическое поведение:

| Формат | Read | Write | Фактическое состояние |
|---|---:|---:|---|
| bytes | да | да | базовый транспорт |
| CSV | да | да | через pandas; весь файл в памяти |
| XLSX | да | да | основной Excel |
| XLSM | да | формально да | обычная запись не гарантирует сохранность VBA |
| XLS | да | best effort | legacy engines |
| XLSB | да | нет | read-only |
| DBF | да | best effort | временный локальный файл; encoding по умолчанию cp866 |
| TXT | да | да | generic text |
| XML | да | да | ElementTree |
| ZIP | да | да | целиком в памяти |
| RAR | да | нет | `rarfile` + системный backend |
| PDF | текст | нет | pypdf, без OCR |
| DOCX | текст | простой DOCX | абзацы; таблицы/сложная структура не извлекаются |
| PPTX | текст | простой PPTX | текст shape; не полноценная модель презентации |
| images | PIL | PIL | Pillow |

## 2.2. Dependency gap

`pyproject.toml` сейчас гарантирует только часть фактических возможностей. В базовых dependencies есть `pandas`, `openpyxl`, `XlsxWriter`, `dbfread`, `beautifulsoup4`, а optional extra явно есть только для PDF среди форматных зависимостей.

Следовательно, уже сейчас существует разрыв:

```text
public API умеет формат
≠
installation contract гарантирует формат
```

Для управляемого desktop-продукта это нежелательно.

---

# 3. Что уже есть в `stratbox-windows`

Desktop surface содержит собственную карту типов файлов.

Сейчас Explorer отдельно распознаёт:

```text
.xlsx
.xls
.csv
.json
.txt
.log
.md
.pdf
.png
.jpg
.jpeg
.bmp
.webp
.svg
.zip
.7z
.rar
.tar
.gz
```

При этом `stratbox`:

- умеет DBF, но Explorer его специально не знает;
- умеет XML, но Explorer его специально не знает;
- умеет DOCX/PPTX, но Explorer их не классифицирует;
- умеет XLSM/XLSB, но Explorer их не классифицирует как Excel;
- умеет RAR, но не умеет 7z/TAR/GZ, которые Explorer уже отображает как архив;
- не имеет generic JSON codec, хотя Explorer знает JSON;
- не имеет generic HTML codec, хотя `beautifulsoup4` уже находится в dependencies;
- не имеет ODS;
- не имеет XBRL/SDMX;
- не имеет Parquet.

Artifact classifier при этом уже имеет третий, отличающийся список: Excel там включает `xlsx/xlsm/xlsb/xls`.

Это уже реальный архитектурный drift:

```text
core IO capabilities
≠
Explorer file types
≠
Artifact kinds
```

Если оставить три списка независимыми, после роста числа форматов они неизбежно разойдутся ещё сильнее.

---

# 4. Главный принцип: пять уровней поддержки файла

Предлагаю больше не использовать бинарное понятие “формат поддерживается / не поддерживается”.

У каждого формата должны быть независимые уровни capabilities.

## L0 — Opaque transport

FileStore умеет:

- хранить;
- копировать;
- перемещать;
- удалять;
- хешировать;
- отдавать байты/stream;
- материализовать локально.

На этом уровне **поддерживаются вообще все файлы**, независимо от расширения.

## L1 — Identification

Система умеет определить:

- extension;
- MIME;
- magic/signature;
- container type;
- предполагаемый `format_id`;
- конфликт extension ↔ content;
- размер;
- checksum.

Пример:

```text
name: report.xls
magic: ZIP/OOXML
detected: xlsx
status: EXTENSION_MISMATCH
```

## L2 — Generic technical decoding

Система умеет открыть содержимое без знания предметной семантики.

Примеры:

- XLSX → sheets/DataFrame;
- CSV → table;
- JSON → object;
- XML → tree;
- ZIP → members;
- PDF → page text;
- DOCX → document blocks;
- XBRL → facts через специализированный processor.

## L3 — Generic encoding/export

Система умеет безопасно создать файл.

Этот уровень должен быть существенно уже L2.

## L4 — Domain semantic support

Конкретная операция понимает, что именно означает содержимое.

Примеры:

- конкретная форма ЦБ;
- конкретный workbook SORS;
- конкретный FRG family;
- конкретный XBRL taxonomy/filing programme;
- конкретный SDMX dataflow.

Именно L4 превращает файл в функциональность Strategy Box.

---

# 5. Макроэкономический и банковский профиль форматов

Набор форматов Strategy Box должен определяться реальными источниками, а не популярностью офисных расширений.

## 5.1. Банк России: XLSX

Текущий встроенный `cbr_file_collector` содержит 41 источник и практически весь этот набор представлен `.xlsx`.

Это делает XLSX форматом №1 для статистического контура Банка России.

Типичные задачи:

- read sheet;
- выбрать sheet по имени/сигнатуре;
- найти заголовок;
- читать merged/hidden layout;
- нормализовать dates/numbers;
- сравнивать schema versions;
- создавать XLSX output.

## 5.2. Банк России: ZIP + DBF

Официальная страница отчётности кредитных организаций на 30.09.2026 прямо публикует формы 101, 102, 123, 135, 0409802, 0409803, 0409805 и финансовую отчётность как **DBF в архиве**.

Это означает:

```text
ZIP + DBF = обязательный P0 форматный путь
```

Причём для старых/регуляторных DBF важна кодировка. Описание формата 0409101 Банка России указывает DOS-кодировку символьных полей, что подтверждает необходимость cp866 как реального профиля, а не экзотического fallback.

## 5.3. XBRL

Банк России продолжает развивать XBRL. В 2026 году опубликованы новые версии таксономий, а на официальной странице отдельно присутствуют материалы XBRL-CSV.

XBRL нельзя реализовывать как:

```python
xml.read_root("file.xbrl")
```

Потому что реальный XBRL включает:

- instance facts;
- contexts;
- units;
- dimensions;
- taxonomy/DTS;
- schemas `.xsd`;
- linkbases `.xml`;
- formula/validation;
- taxonomy packages;
- report packages;
- Inline XBRL;
- xBRL-CSV;
- xBRL-JSON.

Следовательно, нужен отдельный semantic adapter.

## 5.4. Международная макростатистика: SDMX

ECB и IMF используют SDMX как основной программный стандарт обмена статистикой.

ECB API официально поддерживает:

- SDMX-ML XML;
- SDMX-JSON;
- CSV;
- специализированный CSV для pivot;
- gzip HTTP compression.

IMF Data API использует SDMX 2.1/3.0, а IMF SDMX Central работает с CSV, JSON, XML и XLSX.

Следовательно, для международного макроконтура обязательны:

```text
CSV
JSON
XML
GZip
SDMX semantic layer
```

SDMX, как и XBRL, является не “расширением”, а семантическим стандартом поверх нескольких representations.

## 5.5. World Bank и подобные источники

World Bank API поддерживает JSON/JSON-stat и download в CSV/XML/Excel, причём downloads могут приходить ZIP-контейнером.

Это дополнительно подтверждает необходимость связки:

```text
HTTP
→ detect content
→ archive
→ csv/xml/xlsx/json
→ domain normalization
```

---

# 6. Рекомендуемый канонический форматный контур

Ниже — перечень, который я рекомендую **заложить сразу в registry**, даже если некоторые parsers будут реализованы вторым этапом.

Обозначения:

- **P0** — базовый обязательный контур Strategy Box;
- **P1** — установить архитектурное место сразу, реализация после P0;
- **P2** — редкий/специализированный формат, подключать по реальному источнику.

## 6.1. Табличные и структурированные форматы

| format_id | Расширения | Read | Write | Приоритет | Рекомендация |
|---|---|---:|---:|---|---|
| `excel_xlsx` | `.xlsx` | да | да | **P0** | основной human-readable tabular format |
| `excel_xls` | `.xls` | да | нет по умолчанию | **P0** | legacy input |
| `excel_xlsb` | `.xlsb` | да | нет | **P0** | большие/старые corporate workbooks |
| `excel_xlsm` | `.xlsm` | да | только dedicated preserving path | **P0** | macros не исполнять |
| `ods` | `.ods` | да | да | **P0** | важно для Linux/R7/OpenDocument |
| `csv` | `.csv` | да | да | **P0** | основной interchange |
| `tsv` | `.tsv`, `.tab` | да | да | **P0** | часто встречается в статистике |
| `json` | `.json` | да | да | **P0** | API/metadata |
| `jsonl` | `.jsonl`, `.ndjson` | да | да | **P0** | streams/logs/large records |
| `xml` | `.xml` | да | да | **P0** | reporting/statistics base |
| `dbf` | `.dbf` | да | только domain-specific | **P0** | ЦБ/legacy |
| `html` | `.html`, `.htm` | да | ограниченно | **P0** | tables/pages/static exports |
| `xhtml` | `.xhtml` | да | нет generic | **P0** | iXBRL/structured reports |
| `parquet` | `.parquet` | да | да | **P1** | machine canonical/large data |
| `feather` | `.feather`, `.arrow` | да | да | P2 | промежуточный local format |

### Почему ODS нужен раньше, чем кажется

Для Windows-only прототипа ODS можно отложить. Для Strategy Box как продукта с перспективой Astra Linux/R7 его лучше заложить сразу.

ODS — структурированный spreadsheet format, а не “документ для чтения человеком”. Поэтому он ближе к XLSX и полезнее, чем generic ODT/ODP.

---

# 7. Текстовые и web-форматы

| format_id | Расширения | Read | Write | Приоритет | Комментарий |
|---|---|---:|---:|---|---|
| `text` | `.txt` | да | да | **P0** | generic text |
| `markdown` | `.md`, `.markdown` | да | да | **P0** | можно реализовать поверх text |
| `log` | `.log` | да | да | **P0** | operational artifact |
| `csv/tsv` | см. выше | да | да | **P0** | encoding/delimiter profile |
| `html` | `.html`, `.htm` | да | ограниченно | **P0** | DOM/tables |
| `xhtml` | `.xhtml` | да | нет generic | **P0** | iXBRL |
| `rtf` | `.rtf` | ограниченно | нет | P2 | legacy documents |

Отдельный Markdown parser для базового IO не обязателен. В большинстве Strategy Box операций `.md` — обычный UTF-8 text artifact.

HTML, напротив, требует отдельного codec, потому что нужны:

- DOM;
- text extraction;
- tables;
- charset;
- links;
- static HTML validation.

JavaScript execution и browser rendering в `stratbox` не нужны. Если сайт отдаёт данные через JS, лучше использовать underlying API/endpoint.

---

# 8. Офисные документы

| format_id | Расширения | Baseline capability | Приоритет |
|---|---|---|---|
| `pdf` | `.pdf` | metadata + page text + page count | **P0** |
| `docx` | `.docx` | structured blocks/text/tables | **P0** |
| `pptx` | `.pptx` | slides/text/tables/notes metadata | **P0** |
| `doc` | `.doc` | opaque/open only | P2 |
| `ppt` | `.ppt` | opaque/open only | P2 |
| `odt` | `.odt` | text/blocks when needed | P1 |
| `odp` | `.odp` | text/slides when needed | P2 |

## 8.1. PDF

PDF в банковской/макроэкономической работе очень важен:

- методологии;
- отчёты;
- пресс-релизы;
- аналитические обзоры;
- финансовая отчётность;
- приложения к нормативным документам.

Но generic `pdf.read_text()` — это **не generic data parser**.

Нужно различать:

```text
PDF capability A: text-layer extraction
PDF capability B: known-layout table parser
PDF capability C: OCR
PDF capability D: report generation
```

Для Strategy Box P0 достаточно A. B реализуется в конкретном domain. OCR включается только в конкретную операцию, где заранее определено, что сканы являются допустимым источником.

Не следует создавать кнопку “проанализировать PDF” как generic core function — это уже модель AppDock/AI surface, а не Strategy Box.

## 8.2. DOCX

Текущий `read_text()` читает только paragraphs. Для заявленного generic DOCX support этого мало.

Минимальный P0 extractor должен уметь детерминированно выдавать:

```text
paragraph
heading level
table
table cell
header/footer — optional
hyperlink — optional
section/page break — optional
```

Но бизнес-операция должна сама определить, какие элементы ей нужны.

Generic writer “каждая строка = абзац” лучше не считать production capability. DOCX output должен строиться шаблонным exporter-ом конкретного отчёта.

## 8.3. PPTX

Текущий text extractor полезен как smoke utility, но не как полноценный format support.

Для P0 достаточно:

- slide count;
- title;
- text boxes;
- table cells;
- notes — при необходимости;
- embedded media metadata.

Генерация презентаций должна идти через конкретные шаблоны/operations, а не через generic `write_text()`.

---

# 9. Excel-семейство: целевая политика

Excel — крупнейший форматный класс Strategy Box, его нужно специфицировать отдельно.

## 9.1. XLSX

**Полная P0 read/write support.**

Нужны два уровня:

```text
DataFrame mode
Workbook mode
```

DataFrame mode — для простых таблиц.

Workbook mode — для реальных источников:

- несколько sheets;
- merged cells;
- hidden rows/columns/sheets;
- styles как признаки layout;
- named ranges;
- formulas;
- cached formula values;
- comments;
- hyperlinks;
- dates;
- filters;
- frozen panes.

## 9.2. Формулы

`openpyxl` не является Excel calculation engine.

Поэтому operation contract должен явно задавать:

```text
formula_mode:
- formula
- cached_value
- either
```

Нельзя молча считать формулу вычисленным значением.

## 9.3. XLS

XLS нужен как **read-only legacy input**.

Generic write в XLS лучше убрать из целевого API. Причины:

- устаревший формат;
- ограничения;
- старые writer engines;
- нет необходимости генерировать новые `.xls`.

Выход всегда XLSX.

## 9.4. XLSB

Read-only.

XLSB реально встречается в больших банковских файлах. Поддержка полезна, но генерация XLSB Strategy Box не нужна.

## 9.5. XLSM

Read безопасно.

Generic rewrite — опасен, потому что обычный DataFrame path может удалить/испортить VBA.

Целевая политика:

```text
xlsm:
  read_table = yes
  execute_macros = NEVER
  generic_write = no
  preserving_update = only dedicated operation
```

## 9.6. Password/encryption

Зашифрованный Excel должен давать явный status:

```text
PASSWORD_REQUIRED
```

Никаких silent failures и никаких попыток подбора пароля.

Optional future capability может использовать `msoffcrypto-tool`, если появится реальная потребность.

---

# 10. CSV/TSV и кодировки

CSV выглядит простым, но для банковских источников он является одним из самых конфликтных форматов.

Format profile должен хранить:

```text
encoding
delimiter
quotechar
decimal
thousands
header row
skip rows
null markers
date columns
```

## 10.1. Кодировки

Нужно явно поддержать как минимум:

```text
utf-8
utf-8-sig
cp1251
cp866
windows-1252
latin-1 fallback — только осознанно
```

Текущий подход `errors="replace"` для structured input нежелателен: он может тихо заменить символы и продолжить расчёт.

Целевое правило:

> Для аналитического structured input декодирование strict by default.

Fallback chain допустим только если он указан format/source profile и записан в provenance.

## 10.2. Delimiter

Нужны:

```text
,
;
\t
|
```

Авто-sniff разрешён как fallback, но domain source должен по возможности задавать delimiter явно.

---

# 11. DBF

DBF остаётся обязательным.

## 11.1. Read

Нужно сохранить:

- cp866/cp1251 profiles;
- numeric/date/logical fields;
- blank semantics;
- schema metadata.

## 11.2. Sidecar files

Некоторые DBF-варианты используют memo sidecars:

```text
.dbt
.fpt
```

Поэтому форматная модель должна уметь описывать **file bundle**, а не только single file.

Это пригодится также для Shapefile.

## 11.3. Write

Текущий generic DataFrame→DBF writer потенциально теряет:

- исходные типы;
- field widths;
- decimals;
- encoding;
- field names;
- null semantics;
- dialect details.

Поэтому generic DBF writer лучше убрать из production API.

DBF export должен существовать только если конкретный target contract требует точную DBF schema.

---

# 12. JSON и JSONL

Странно, что desktop уже знает JSON, а `stratbox.ioapi` пока не имеет generic JSON.

JSON должен стать P0.

Нужны:

```text
read_object
write_object
read_jsonl
write_jsonl
```

Полезные параметры:

- UTF-8 only по умолчанию;
- `ensure_ascii=False`;
- deterministic key ordering для manifests;
- Decimal/date serialization policy.

JSON хорошо подходит для:

- manifests;
- provenance;
- operation results;
- registries;
- API snapshots;
- metadata.

JSONL — для:

- событий;
- больших record datasets;
- incremental outputs.

---

# 13. XML, XSD и XML security

Generic XML P0 нужен отдельно от XBRL.

Нужно поддержать:

```text
.xml
.xsd
```

Для XML parser политика должна быть безопасной:

- external entities off;
- network resolution off by default;
- no arbitrary DTD fetch;
- explicit namespace handling;
- optional schema validation в domain.

`xml.etree.ElementTree` подходит для простого XML, но XBRL и сложная schema validation требуют специализированного инструмента.

---

# 14. XBRL как отдельное семейство

## 14.1. Почему это P0 архитектурно

Банк России активно развивает XBRL и XBRL-CSV. Кроме того, глобальная корпоративная отчётность всё активнее существует в XBRL/iXBRL.

Даже если первые операции Strategy Box используют только DBF/XLSX, **место XBRL нужно заложить сейчас**, иначе generic XML/ZIP design потом придётся ломать.

## 14.2. Что считать XBRL family

```text
.xbrl / XML instance
Inline XBRL: .html / .xhtml
xBRL-CSV
xBRL-JSON
taxonomy .xsd/.xml
Taxonomy Package ZIP
Report Package ZIP
```

XBRL International указывает, что taxonomy обычно состоит из множества `.xsd` и `.xml`, а Taxonomy Package является ZIP-контейнером.

В 2026 году развивается Taxonomy Packages 1.1; новая спецификация вводит `.xbrt` как специальное расширение для taxonomy package. Для Strategy Box это пока лучше держать как **watchlist capability**, а не основной production input Банка России.

## 14.3. Рекомендуемый engine

Вместо собственной реализации XBRL core целесообразно использовать **Arelle** как optional backend.

Arelle:

- open source;
- Python API;
- XBRL 2.1;
- Dimensions;
- Formula;
- Taxonomy Packages;
- Report Packages;
- iXBRL;
- xBRL-CSV;
- xBRL-JSON;
- validation.

Это намного надёжнее собственной реализации DTS discovery и validation.

## 14.4. Целевой интерфейс

```text
XbrlOpenRequest
XbrlOpenResult

XbrlValidationResult
XbrlFact
XbrlFactTable
XbrlTaxonomyIdentity
XbrlPackageIdentity
```

Domain operation затем решает, какие facts нужны.

---

# 15. SDMX как отдельное семейство

SDMX нельзя добавлять как `ioapi.sdmx_file`.

Целевая структура:

```text
formats/sdmx/
  client
  detect
  csv
  json
  xml
  structures
  normalize
```

Представления:

```text
SDMX-CSV
SDMX-JSON
SDMX-ML
```

Нужны:

- dataflow identity;
- structure/DSD identity;
- dimensions;
- attributes;
- observations;
- time period;
- revision metadata.

Canonical output Strategy Box может быть обычным DataFrame/Parquet, но provenance должен сохранять исходный SDMX flow/structure.

---

# 16. HTML

HTML важен в трёх разных сценариях:

1. официальный источник публикует таблицу прямо на странице;
2. downloaded file на самом деле оказался HTML error page;
3. iXBRL использует HTML/XHTML как report representation.

Поэтому generic HTML codec должен уметь:

- detect charset;
- parse DOM;
- extract text;
- extract tables;
- inspect `<title>`;
- classify likely error/login page;
- не выполнять JavaScript.

Текущий `cbr_file_collector` уже имеет правильную идею: если ожидается data file, HTML payload нужно отклонять.

Эту проверку следует поднять в общую `SourceValidation`.

---

# 17. Архивы и compression

Архивный слой нужно расширить существенно.

## 17.1. P0 контейнеры

```text
.zip       read/write
.rar       read-only
.7z        read-only
.tar       read
.tar.gz    read
.tgz       read
.gz        read/write single stream
```

Также желательно:

```text
.bz2
.xz
```

как P1, потому что это дешёвая поддержка стандартной библиотеки Python.

## 17.2. Выходной формат

Для Strategy Box canonical archive output:

```text
ZIP
```

Нет причины генерировать RAR/7z.

## 17.3. Текущая проблема

ZIP и RAR сейчас работают по схеме:

```text
FileStore.read_bytes()
→ весь archive в RAM
→ extract all members в RAM
```

Это годится для небольших файлов, но плохо масштабируется на реальные архивы.

Нужен streaming/materialization path.

## 17.4. Archive safety

Обязательны:

- защита от `../` path traversal;
- абсолютных paths;
- Windows drive paths;
- symlink/hardlink extraction;
- max member count;
- max uncompressed bytes;
- max compression ratio;
- max nesting depth;
- duplicate member policy;
- encrypted member detection;
- explicit `PASSWORD_REQUIRED`;
- checksum optional;
- extraction plan before write.

Пример:

```text
archive.inspect
  → members + sizes + flags
archive.plan_extract
  → validated paths
archive.extract
  → FileStore/temp
```

Не нужно извлекать архив сразу при первом открытии.

## 17.5. Nested archives

Допускать ограниченно.

Рекомендация:

```text
default max_nested_depth = 2
```

Большая глубина должна задаваться конкретной операцией.

---

# 18. 7z и RAR

## RAR

Сохранить read-only support.

Нужно учитывать, что Python wrapper часто требует внешний binary/backend. Capability check должен выполняться при startup/preflight, а не во время неожиданного пользовательского запуска.

## 7z

Добавить через `py7zr` как optional dependency.

Для российского corporate file exchange 7z достаточно распространён, чтобы поддерживать его с первого полноценного desktop release.

---

# 19. GZip и HTTP compression

GZip нужен не только как файл `.gz`.

ECB и другие statistical APIs могут возвращать compressed response через HTTP `Content-Encoding`.

Network layer должен:

- понимать Content-Encoding;
- сохранять raw compressed payload, если политика raw preservation это требует;
- уметь отдать decoded content;
- записывать compression в SourceSnapshot.

---

# 20. Images

Изображения не являются основным аналитическим форматом Strategy Box, но они возникают:

- charts;
- scanned pages;
- screenshots in reports;
- logos/templates;
- embedded report resources.

P0 recognition:

```text
.png
.jpg
.jpeg
.webp
.bmp
.tif
.tiff
.svg
```

Generic capability:

- dimensions;
- mode;
- metadata;
- read/write bytes;
- Pillow object for raster.

OCR **не включать в generic image codec**. OCR — отдельная operation capability.

SVG нужно считать XML-based image и не исполнять embedded scripts.

---

# 21. Parquet

Parquet не является главным текущим source format Банка России, однако его стоит добавить как P1 почти сразу.

Причины:

- columnar;
- сохраняет типы лучше CSV;
- эффективен для больших canonical datasets;
- уменьшает RAM/IO;
- подходит для повторных запусков;
- удобен для кешей SORS и больших временных рядов.

Рекомендуемый backend:

```text
pyarrow
```

Поскольку dependency тяжёлая, её лучше вынести в extra:

```text
stratbox[columnar]
```

Canonical rule:

```text
human output → XLSX
machine large output/cache → Parquet
portable simple output → CSV
```

---

# 22. SQLite / database files

`.sqlite`, `.sqlite3`, `.db` стоит заложить как P1/P2 capability, но с жёсткой оговоркой.

Нельзя безопасно использовать SQLite database напрямую поверх произвольного remote FileStore как обычный сетевой файл.

Целевая модель:

```text
FileStore object
→ materialize local read-only
→ sqlite3 connection
→ query
```

Write-back — отдельная операция с atomic replacement.

Для первого релиза полноценный SQLite codec не обязателен.

---

# 23. Statistical packages

Редкие, но возможные международные наборы:

```text
.dta       Stata
.sav       SPSS
.sas7bdat  SAS
.xpt       SAS transport
```

Это P2.

Их не нужно устанавливать “на всякий случай”, но registry должен позволять потом добавить `stat_packages` extra без redesign.

---

# 24. GIS / regional data

Для региональной макроаналитики в будущем возможны:

```text
.geojson
.gpkg
.shp + .shx + .dbf + .prj
.kml
```

Приоритет P2.

Важно заранее понимать, что Shapefile — **bundle format**, как DBF+memo.

Если Strategy Box начинает строить географические карты регионов, этот capability становится P1.

---

# 25. Что сознательно не нужно в стартовом semantic scope

Не стоит делать generic parser для каждого файла, который Windows умеет открыть.

Стартово можно оставить opaque:

```text
.doc
.ppt
.mdb
.accdb
.psd
.ai
.cdr
.dwg
.dxf
.msg
.eml
```

Если конкретная бизнес-задача потребует формат, добавляется отдельный adapter.

FileStore при этом и так сможет хранить эти файлы.

---

# 26. Форматная политика “read broad / write narrow”

Это один из главных выводов.

## 26.1. Вход

Широкий:

```text
XLSX / XLS / XLSB / XLSM / ODS
CSV / TSV
JSON / JSONL
XML / XSD
HTML / XHTML
DBF
PDF
DOCX
PPTX
TXT / MD
ZIP / RAR / 7z / TAR / GZ
XBRL family
SDMX representations
images
Parquet optional
```

## 26.2. Выход

Узкий:

### Human tabular

```text
XLSX
```

### Portable data

```text
CSV / TSV
JSON / JSONL
```

### Machine large

```text
Parquet
```

### Text/report source

```text
TXT / MD / HTML
```

### Package

```text
ZIP
```

### Special report output

```text
DOCX/PPTX/PDF
```

только через конкретный template/report operation.

## 26.3. Форматы, которые Strategy Box не должен generic-write

```text
XLS
XLSB
XLSM
DBF
RAR
7z
XBRL
```

Запись любого из них допустима только при наличии конкретного target contract.

---

# 27. Единый `FormatRegistry`

Нужен один source of truth.

Пример conceptual descriptor:

```python
FormatSpec(
    id="excel_xlsx",
    family="spreadsheet",
    extensions=(".xlsx",),
    mime_types=(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ),
    capabilities={
        "identify",
        "read_table",
        "read_workbook",
        "write_table",
        "write_workbook",
    },
    reader="...",
    writer="...",
    dependency_group="excel",
    canonical_output=True,
    container="zip_ooxml",
    security_profile="office_no_execution",
)
```

Дополнительные поля:

```text
title
extensions
mime_types
magic signatures
container type
read/write flags
streaming support
seekable required
dependency group
default encoding
canonical output
lossless roundtrip
security flags
platform restrictions
max recommended size
artifact kind
icon key
```

---

# 28. Detection: одного расширения недостаточно

Нужно проверять четыре слоя:

```text
1. filename/extension
2. HTTP Content-Type
3. magic/signature
4. container inspection / internal manifest
```

Примеры:

### XLSX/DOCX/PPTX

Все начинаются как ZIP.

Нужно посмотреть OOXML internal parts.

### ODS

Тоже ZIP container, но с OpenDocument `mimetype`.

### XBRL Taxonomy Package

Тоже ZIP, но имеет XBRL package metadata.

### Download error

URL называется `.xlsx`, а сервер вернул:

```html
<html>Access denied...</html>
```

Это должно стать `CONTENT_TYPE_MISMATCH`, а не ошибкой openpyxl через три слоя позже.

---

# 29. Format identity vs semantic identity

В SourceSnapshot нужно хранить обе сущности.

```text
physical_format_id = excel_xlsx
semantic_source_type = cbr.corp_debt_by_activity
```

или:

```text
physical_format_id = dbf
container_format_id = zip
semantic_source_type = cbr.form.0409101
```

или:

```text
physical_format_id = xml
semantic_format_id = xbrl
filing_program = ...
taxonomy_version = ...
```

Это критично для provenance.

---

# 30. Новый low-level объект `FileInfo`

Нынешнего `FileStat` мало для форматного контура.

Предлагаемый объект выше FileStore:

```text
FileInfo
  path
  name
  extension
  size
  mtime
  sha256
  mime_type
  detected_format_id
  container_format_id
  encoding
  detection_confidence
  mismatch_flags
```

FileStore остаётся простым; `FileInspector` строит `FileInfo`.

---

# 31. Materialization layer

Это одна из самых важных технических доработок.

Сейчас несколько codecs сами делают:

```text
read all bytes
→ tempfile
→ library reads tempfile
```

Это дублируется в DBF/RAR и неизбежно появится в XBRL/7z/SQLite.

Нужен единый слой:

```python
with materialize_read(path, store=fs) as local_path:
    ...
```

и:

```python
with materialize_write(target, store=fs) as local_path:
    ...
# commit only on successful context exit
```

Плюсы:

- одна политика temp;
- большие файлы;
- cleanup;
- checksum;
- atomic commit;
- abort;
- reuse локального файла несколькими parser stages;
- библиотеки, которым нужен seekable path.

---

# 32. FileStore: что добавить

FileStore должен остаться format-agnostic, но получить несколько инфраструктурных capabilities.

Рекомендуемый target:

```text
open_read
open_write
exists
is_file
is_dir
stat
listdir
makedirs
remove
rmdir
rmtree
rename
copy
walk
glob

read_bytes
write_bytes

checksum
copy_to_local
copy_from_local
atomic_write / temp_commit
capabilities
```

Дополнительно полезно:

```text
supports_streaming
supports_seek
supports_atomic_rename
supports_server_side_copy
max_object_size? optional
```

---

# 33. `ioapi` лучше сделать registry-driven

Текущий подход:

```text
excel.py:
  if .xlsx -> ...
  if .xlsm -> ...
  if .xls -> ...
  if .xlsb -> ...
  else -> assume xlsx
```

Последний fallback опасен.

Неизвестное расширение не должно молча считаться XLSX.

Целевое поведение:

```text
unknown
→ UnsupportedFormatError
```

либо explicit caller override:

```text
format_id="excel_xlsx"
```

То же относится к `archives.py`, где любой не-RAR путь сейчас фактически идёт в ZIP.

---

# 34. Error model форматов

Нужен единый набор ошибок/статусов:

```text
UnsupportedFormat
FormatMismatch
CorruptFile
PasswordRequired
EncryptedUnsupported
DependencyUnavailable
InvalidEncoding
SchemaMismatch
ValidationFailed
ArchiveUnsafe
ArchiveLimitExceeded
UnsupportedFeature
MaterializationFailed
PartialExtraction
```

Domain Result может преобразовать их в понятные user-facing failures.

---

# 35. OperationSpec должен знать форматы

В `stratbox-windows` уже есть schema-driven параметры операций.

Следующий шаг:

```text
OperationParamSpec(path_file):
  accepted_format_ids
  accepted_extensions
  allow_archives
  archive_member_formats
  max_size
  multiple
```

Например:

```text
cbr.forms.import:
  accepts:
    - zip
    - dbf
```

```text
xbrl.extract:
  accepts:
    - xbrl_instance
    - inline_xbrl
    - xbrl_report_package
```

```text
frg.parse:
  accepts:
    - excel_xlsx
    - excel_xlsb
```

UI тогда не “угадывает”, а рендерит контракт core.

---

# 36. `stratbox-windows`: убрать hardcoded file map

Текущий `_FILE_TYPE_MAP` нужно заменить на read-only projection `FormatRegistry`.

Explorer должен отображать:

```text
file_type_label
icon_key
format_id
supported_by_any_operation
```

Но важное правило:

> Explorer показывает любой файл, даже если Strategy Box не умеет его анализировать.

Для неизвестного:

```text
format_id = unknown
artifact kind = file
```

При этом file picker конкретного scenario фильтрует допустимые форматы.

---

# 37. Artifact model нужно расширить

Сейчас artifact kind слишком общий:

```text
file
folder
excel
zip
log
report
dataset
unknown
```

Этого мало.

Лучше разделить:

```text
Artifact:
  semantic_kind = dataset/report/log/source/archive/...
  format_id = excel_xlsx
```

Например:

```text
semantic_kind = dataset
format_id = parquet
```

или:

```text
semantic_kind = report
format_id = pdf
```

Добавить:

```text
size
sha256
mime_type
format_id
schema_id
source_links
```

---

# 38. Будущий `stratbox-android`

Android не должен копировать список расширений.

Shared contract:

```text
FormatSpec
Artifact format_id
Operation accepted_format_ids
```

Android может иметь свои platform capabilities:

```text
can_preview_pdf = yes
can_edit_xlsx = no
can_download = yes
can_upload = yes
```

Но semantic compatibility с core остаётся общей.

---

# 39. Dependency groups

Вместо случайных optional installs предлагаю такие extras.

## `stratbox[excel]`

```text
openpyxl
XlsxWriter
xlrd
pyxlsb
odfpy
```

Generic XLS writer (`xlwt`) не нужен.

## `stratbox[documents]`

```text
pypdf
python-docx
python-pptx
Pillow
```

## `stratbox[archives]`

```text
rarfile
py7zr
```

TAR/GZip/BZip2/XZ — standard library.

## `stratbox[xbrl]`

```text
arelle-release
```

## `stratbox[columnar]`

```text
pyarrow
```

## `stratbox[stats]`

будущий P2:

```text
pyreadstat
```

## Desktop distribution

Полноценная Strategy Box desktop поставка может устанавливать заранее:

```text
excel + documents + archives + xbrl + columnar
```

если размер дистрибутива приемлем.

---

# 40. Runtime auto-install нужно убрать из production

Сейчас часть ioapi умеет `auto_install`.

Для notebooks это удобно.

Для Strategy Box как детерминированного продукта это плохая модель:

- результат зависит от сети;
- version drift;
- installation side effect во время операции;
- проблемы permissions;
- сложная observability;
- невозможно заранее гарантировать capability.

Целевой production принцип:

> Operation может использовать только capabilities, подтверждённые при установке/preflight.

Если dependency отсутствует:

```text
CAPABILITY_UNAVAILABLE
```

и понятная диагностика.

---

# 41. Security profile по форматам

## Office

- никогда не исполнять VBA/macros;
- external links не обновлять автоматически;
- embedded OLE не выполнять;
- encrypted → explicit status.

## CSV

CSV formula injection при открытии в Excel:

```text
=...
+...
-...
@...
```

Для экспортов, которые заведомо открываются человеком в Excel, нужен optional `excel_safe_strings` policy.

Нельзя применять его к числовому scientific data по умолчанию, потому что это изменяет значения. Политика должна быть явной.

## XML/XBRL

- XXE off;
- external network fetch controlled;
- taxonomy URL cache/allowlist;
- resource limits.

## HTML/SVG

- не исполнять scripts;
- не загружать external content при parse.

## Archives

- path traversal;
- bombs;
- nested limits;
- encrypted handling.

## PDF

- JavaScript/attachments не исполнять;
- parser только читает разрешённые структуры.

---

# 42. Large-file policy

Текущий memory-first IO нужно постепенно ограничить.

Предлагаемые режимы:

```text
small:
  bytes/BytesIO

medium:
  seekable temp file

large:
  stream/chunk
```

`FormatSpec` может хранить:

```text
preferred_access = bytes | seekable_file | stream
```

Примеры:

```text
CSV large → stream/chunks
XLSX → seekable temp
RAR/7z → seekable temp
XBRL package → materialized directory/cache
PDF → seekable bytes/file
Parquet → seekable/local materialized
```

---

# 43. SourceSnapshot должен фиксировать format provenance

Предлагаемый минимум:

```text
source_id
requested_url
final_url
fetched_at

filename
content_type_header
content_encoding_header

size_bytes
sha256

declared_extension
detected_format_id
container_format_id
character_encoding

validation_status
validation_warnings

source_schema_version
```

Тогда parser получает проверенный snapshot, а не просто `bytes`.

---

# 44. Тестовый контур

Для каждого P0 format нужны fixture tests.

## 44.1. Common tests

```text
correct extension
uppercase extension
wrong extension
no extension
corrupt file
zero bytes
large file
Unicode filename
Cyrillic filename
remote FileStore
local FileStore
```

## 44.2. Text/CSV

```text
utf-8
utf-8-sig
cp1251
cp866
;
,
tab
quoted newline
decimal comma
NBSP
```

## 44.3. Excel

```text
xlsx multi-sheet
merged cells
hidden sheet
date cells
formula/cached value
xls
xlsb
xlsm with VBA — verify no execution
ods
password protected
```

## 44.4. Archives

```text
zip
rar
7z
tar
tar.gz
nested zip
../ traversal
absolute path
duplicate member
huge compression ratio
encrypted
```

## 44.5. DBF

```text
cp866
cp1251
dates
numeric decimals
blank/null
memo sidecar
```

## 44.6. XBRL

```text
instance
taxonomy package
report package
iXBRL
xBRL-CSV
validation errors
offline taxonomy cache
```

---

# 45. Что в текущем коде я бы изменил сразу

С учётом правила проекта, что обратная совместимость не требуется, лучше сразу привести слой к целевой модели.

## 45.1. Оставить

- FileStore interface как нейтральную основу;
- LocalFileStore;
- bytes;
- основной XLSX stack;
- CSV;
- XML;
- PDF text extraction как одну capability;
- ZIP/RAR идею;
- optional dependency groups.

## 45.2. Переписать

### `excel.py`

Убрать fallback unknown → XLSX.

### `archives.py`

Перейти с `rar else zip` на registry dispatch.

### CSV/TXT

Убрать silent `errors="replace"` из structured paths.

### ZIP/RAR

Убрать `extract_all_to_memory` как основной API.

### DBF

Read оставить; generic write убрать или сделать явно `unsafe_legacy_export`.

### XLS

Generic write убрать.

### XLSM

Generic write убрать.

### DOCX/PPTX

Считать текущие writers прототипами; production writers должны быть report/template-specific.

### PDF

Не подавлять extraction failures бесследно. Возвращать per-page diagnostics.

---

# 46. Новая рекомендуемая структура `stratbox`

Один из чистых вариантов:

```text
stratbox/
  base/
    filestore/
      ...
    files/
      inspect.py
      materialize.py
      formats.py
      errors.py

    ioapi/
      bytes.py
      text.py
      delimited.py
      json.py
      xml.py
      html.py

      spreadsheets/
        xlsx.py
        xls.py
        xlsb.py
        xlsm.py
        ods.py

      dbf.py

      documents/
        pdf.py
        docx.py
        pptx.py

      archives/
        zip.py
        rar.py
        sevenzip.py
        tar.py
        compression.py

      images.py
      parquet.py

  formats/
    xbrl/
      ...
    sdmx/
      ...
```

Здесь:

- `base.ioapi` — физический codec;
- `formats.xbrl/sdmx` — semantic standard;
- `macrobanks.*` — бизнес-смысл конкретного источника.

---

# 47. Почему XBRL/SDMX не стоит класть в `macrobanks` конкретного домена

Оба стандарта шире одной банковской задачи.

XBRL может использоваться:

- Банком России;
- SEC;
- ESEF;
- корпоративными disclosures;
- страховыми/финансовыми организациями.

SDMX:

- ECB;
- IMF;
- OECD;
- национальные статистические службы;
- центральные банки.

Поэтому semantic engines должны быть reusable, а конкретный source adapter — доменным.

---

# 48. Канонический стартовый список

Если нужен **один практический список расширений, который Strategy Box должен знать с самого начала**, я бы зафиксировал:

```text
# Spreadsheets
.xlsx
.xls
.xlsb
.xlsm
.ods

# Delimited / structured text
.csv
.tsv
.tab
.json
.jsonl
.ndjson
.xml
.xsd
.html
.htm
.xhtml

# Regulatory / reporting
.dbf
.xbrl

# Documents
.pdf
.docx
.pptx

# Text
.txt
.md
.log

# Archives / compression
.zip
.rar
.7z
.tar
.gz
.tgz
.bz2
.xz

# Images
.png
.jpg
.jpeg
.webp
.bmp
.tif
.tiff
.svg

# Machine datasets
.parquet
```

Плюс registry-level semantic aliases:

```text
xbrl_instance
inline_xbrl
xbrl_csv
xbrl_json
xbrl_taxonomy_package
xbrl_report_package

sdmx_csv
sdmx_json
sdmx_ml
```

И future/watchlist:

```text
.xbrt
.feather
.arrow
.sqlite
.sqlite3
.db
.geojson
.gpkg
.shp
.dta
.sav
.sas7bdat
.xpt
.odt
.odp
.rtf
```

---

# 49. Что обязательно поддержать технически к первому зрелому релизу

## Полная read/write

```text
XLSX
ODS
CSV
TSV
JSON
JSONL
XML
TXT
MD
ZIP
```

## Полный read + ограниченный/special write

```text
PDF
DOCX
PPTX
HTML
DBF
Parquet
```

Parquet write можно считать полноценным после подключения `pyarrow`.

## Read-only by default

```text
XLS
XLSB
XLSM
RAR
7z
TAR variants
```

TAR можно писать технически, но продуктовой необходимости обычно нет.

## Semantic engines

```text
XBRL
SDMX
```

---

# 50. Что должно быть реализовано в UI

## File picker

Не общий:

```text
"Все поддерживаемые файлы"
```

а operation-specific:

```text
CBR reporting archives (*.zip *.dbf)
Excel workbooks (*.xlsx *.xlsb *.xls)
XBRL reports (*.xbrl *.xml *.xhtml *.html *.zip)
```

## Explorer

Показывает всё.

## Inspector

Для известного формата показывает:

```text
Format
Size
Modified
SHA256
Detected MIME
Sheets/pages/members — если дешёво получить
```

## Unsupported

Не ошибка FileStore.

Пример:

```text
Файл доступен в рабочем пространстве.
Strategy Box не имеет операций для формата .psd.
```

---

# 51. AppDock и Strategy Box: граница

В Strategy Box format registry конечен и детерминирован.

AppDock по своей природе шире: он управляет внешними приложениями, рабочими средами, файлами, результатами и будущими агентными действиями. Поэтому AppDock может иметь универсальный file intelligence layer и подключаемые processors.

Strategy Box должен быть проще:

```text
Command
→ declared input contract
→ declared parser
→ declared algorithm
→ declared output contract
```

Это не слабость, а преимущество:

- воспроизводимость;
- auditability;
- тестируемость;
- отсутствие неожиданного AI interpretation;
- понятные зависимости;
- стабильная автоматизация.

---

# 52. Рекомендуемая последовательность разработки

## Этап A — единая модель

1. `FormatSpec`.
2. `FormatRegistry`.
3. `FileInspector`.
4. format detection.
5. единый error model.
6. единый materialization layer.

## Этап B — закрыть current drift

1. Перевести current ioapi в registry.
2. Перевести Windows Explorer на registry.
3. Перевести Artifact classifier на `format_id`.
4. Синхронизировать dependencies.

## Этап C — обязательные недостающие codecs

1. JSON/JSONL.
2. HTML.
3. TSV.
4. ODS.
5. 7z.
6. TAR/GZip.
7. Parquet.

## Этап D — hardened archives/files

1. streaming/materialization.
2. archive safety.
3. checksums.
4. atomic writes.
5. file size policies.

## Этап E — XBRL

1. optional Arelle backend.
2. taxonomy cache.
3. package support.
4. fact model.
5. validation result.
6. first CBR/global reporting operation.

## Этап F — SDMX

1. common SDMX client.
2. CSV/JSON/XML representations.
3. DSD/dataflow identity.
4. first ECB/IMF source operation.

## Этап G — documents

1. DOCX structured reader.
2. PPTX structured reader.
3. PDF diagnostics.
4. concrete report exporters.

---

# 53. Приоритеты P0/P1/P2

## P0

Архитектура и реальная ежедневная банковская/макро работа:

```text
FileStore bytes/streams
FormatRegistry
Detection
Materialization

XLSX
XLS
XLSB
XLSM
ODS

CSV
TSV
JSON
JSONL
XML
HTML

DBF

ZIP
RAR
7z
TAR/GZ

PDF
DOCX
PPTX
TXT/MD

XBRL architecture + backend
SDMX architecture
```

## P1

```text
Parquet
ODT
BZ2/XZ polished support
SQLite read-only materialized
GeoJSON
richer image metadata
```

## P2

```text
SPSS/SAS/Stata
Shapefile/GeoPackage full stack
RTF
DOC/PPT legacy conversion
Access MDB/ACCDB
other specialist formats
```

---

# 54. Самые важные конкретные решения

1. **FileStore не знает форматов.**
2. **Один FormatRegistry на весь Strategy Box.**
3. **Windows и Android не держат собственные extension maps.**
4. **Unknown file — нормальное состояние, а не ошибка.**
5. **Operation объявляет accepted formats.**
6. **Unknown Excel extension больше не fallback в XLSX.**
7. **Generic XLS/XLSM/DBF write убрать.**
8. **ZIP — единственный canonical multi-file archive output.**
9. **Archive extraction — plan/validate/stream, не all-to-memory.**
10. **XBRL и SDMX — semantic families.**
11. **Arelle — предпочтительный XBRL backend.**
12. **ODS добавить из-за Linux/R7-перспективы.**
13. **Parquet добавить как machine canonical format.**
14. **CSV/DBF encoding — explicit и audit-able.**
15. **Runtime auto-pip в продукте отключить.**
16. **Macros никогда не исполнять.**
17. **Password-protected file → PASSWORD_REQUIRED.**
18. **Content-Type/extension/magic mismatch фиксировать до parser.**
19. **Raw source сохранять отдельно от canonical data.**
20. **Format identity включать в provenance и artifacts.**

---

# 55. Итоговая целевая схема

```text
                       STRATEGY BOX

┌───────────────────────────────────────────────────────────┐
│                    Domain Operations                       │
│ CBR / banks / macro / XBRL / SDMX / FRG / reports         │
└─────────────────────────────┬─────────────────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────┐
│                    Semantic Adapters                       │
│ XBRL | SDMX | source schemas | regulatory schemas         │
└─────────────────────────────┬─────────────────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────┐
│                     Generic IO Codecs                      │
│ Excel | ODS | CSV | JSON | XML | HTML | DBF | PDF ...    │
│ archives | documents | images | parquet                   │
└─────────────────────────────┬─────────────────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────┐
│       FormatRegistry + Detection + Materialization         │
└─────────────────────────────┬─────────────────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────┐
│                         FileStore                          │
│ paths | bytes | streams | stat | copy | atomic commit     │
│                FORMAT-AGNOSTIC                            │
└───────────────────────────────────────────────────────────┘
```

Эта схема соответствует природе Strategy Box: заранее определённые аналитические действия поверх предсказуемого набора источников, при этом форматный фундамент достаточно широкий, чтобы проекту не пришлось перестраивать FileStore через полгода после появления очередного XLSB, XBRL package, ODS или 7z.

---

# 56. Источники и проверенные материалы

## Внутренние исследовательские материалы проекта

1. `stratbox_base_study_current_state_2026-10-06.md`
2. `stratbox-windows_current_state_full_research_2026-10-06.md`
3. `AppDock - Базовое описание.docx`

Также выполнена повторная проверка актуального `main` репозиториев `ForestTiger-GH/stratbox` и `ForestTiger-GH/stratbox-windows` на 2026-10-07, включая:

- `stratbox.base.filestore.base`;
- `stratbox.base.ioapi/*`;
- `stratbox.macrobanks.cbr_file_collector.registry`;
- `stratbox.macrobanks.frg`;
- `stratbox-windows/application/workspace/file_types.py`;
- `stratbox-windows/application/artifacts/models.py`.

## Банк России

- Отчетность кредитных организаций:  
  https://www.cbr.ru/banking_sector/otchetnost-kreditnykh-organizaciy/

- Открытый стандарт отчетности XBRL:  
  https://www.cbr.ru/projects_xbrl/

- Таксономия XBRL:  
  https://www.cbr.ru/projects_xbrl/taxonomy_xbrl/

- Правила формирования отчетности в формате XBRL:  
  https://www.cbr.ru/projects_xbrl/taxonomy_xbrl/pravila-formirovaniya-otchetnosti-v-formate-xbrl-i-ee-predstavleniya-v-bank-rossii/

## XBRL International

- XBRL Specifications:  
  https://specifications.xbrl.org/specifications.html

- Taxonomy Packages guidance:  
  https://www.xbrl.org/guidance/taxonomy-packages/

- Taxonomy & Report Packages:  
  https://specifications.xbrl.org/spec-group-index-taxonomy-packages.html

## Arelle

- Documentation:  
  https://arelle.org/arelle/documentation/

- Product/features:  
  https://arelle.org/

## ECB

- SDMX web services:  
  https://data.ecb.europa.eu/help/getting-data-web-services-sdmx-0

- Content negotiation / formats:  
  https://data.ecb.europa.eu/help/api/content-negotiation

## IMF

- IMF Data API:  
  https://data.imf.org/en/Resource-Pages/IMF-API

- IMF SDMX Central:  
  https://sdmxcentral.imf.org/

## World Bank

- API basic call structures and download formats:  
  https://datahelpdesk.worldbank.org/knowledgebase/articles/898581-api-basic-call-structures

---

# 57. Финальный вывод

Форматный слой Strategy Box стоит сделать **шире текущего набора конкретных операций, но уже универсального AI-file layer AppDock**.

Правильный баланс выглядит так:

```text
FileStore:
  любой файл

Format Registry:
  широкий заранее известный перечень

Codecs:
  ограниченный сертифицированный набор

Domain Operations:
  только заранее определённые структуры и алгоритмы

Outputs:
  узкий канонический набор
```

Если эту границу провести сейчас, Strategy Box сможет спокойно расширяться от сегодняшних XLSX/DBF/ZIP к XBRL, SDMX, ODS, 7z и Parquet без новой переделки файловой архитектуры и без превращения core в универсальную платформу обработки документов.
