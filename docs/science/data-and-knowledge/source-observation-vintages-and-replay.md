# Наблюдения за источниками, редакции публикаций и проверяемость статистических расчётов

**Научная задача:** что действительно можно установить о банковском/макроэкономическом показателе спустя время, когда URL мог не измениться, данные — исправиться, а метод вычисления — эволюционировать. **Статус:** самостоятельная научно-инженерная модель, дополняющая [идентичность источников](source-identity-and-reproducibility.md); типы `FetchReceipt`, `RunProvenance` и уровни R0–R4 — *исследовательские кандидаты*, не существующий универсальный runtime API и не принятое Product Decision. **Эпистемическое ограничение:** точность и достаточность evidence подтверждаются на уровне конкретного действия; hash не удостоверяет экономическую интерпретацию.

## 1. Вопрос аналитика: что именно было известно, увидено и рассчитано

Для ретроспективной проверки результата недостаточно знать название XLSX и дату статистического ряда. Различаются публикация источника, правило получения файла, факт получения, конкретные байты, использованная редакция справочника и версия вычисляющего метода. Эти объекты могут изменяться независимо.

Практический набор вопросов: **какую публикацию** использовал аналитик, **когда** она была наблюдаема системе, **какие байты** фактически пришли, **какие версии правил** действовали, **можно ли получить те же inputs**, **выполнено ли проверочное повторение**. Если сохранено лишь время загрузки, доказательная глубина ограничена. Если сохранён hash, подтверждается byte identity, но ещё отсутствует старый payload для replay. Если повтор вычисления выполнен, он не подтверждает правильность исходной методологии автоматически.

В исходном [исследовании темы 09](https://github.com/ForestTiger-GH/stratbox/blob/388e3d61ec01350d3b7d35ea4a97a21db0b36f97/_mw/epochs-001-strategy-box-development/research/04-ai-raised-topics/09_Источники_данных_версии_и_воспроизводимость_Strategy_Box_2026-10-10.md#L14-L35) **передан как комментарий разработчика** следующий приоритет: простая отметка фактического времени загрузки, ответственность эксперта за актуальность и смысл, отсутствие дорогого глобального реестра всех статистических показателей и опциональная ссылка на существующую методику производного расчёта. **Оригинал аннотированного пользовательского документа для этой атрибуции пока недоступен; здесь подтверждено содержание Research, а не независимая сверка слов пользователя.** Следствие для архитектурного исследования: provenance полезнее строить вокруг фактически использованных входов, сохраняя выборочную управляемую регистрацию и отдельную оценку стоимости постоянного мониторинга тысяч ресурсов.

## 2. Шесть идентичностей и седьмой результат

| Сущность | Что идентифицирует | Пример доказательства / риск |
| --- | --- | --- |
| **Authority** | Орган/издателя и происхождение публикации | Официальная страница; всё ещё не доказывает, что конкретные bytes пришли именно от неё |
| **SourceDefinition** | Правило discovery/acquisition и локатор | Повтор по URL может получить иную редакцию или HTML-ошибку |
| **FetchReceipt** | Конкретную попытку и наблюдённый ответ | `observed_at`, status, canonical/actual locator и HTTP hints; timestamp не идентифицирует bytes |
| **SourceSnapshot/ByteIdentity** | Фактически полученный byte string | `sha256`, размер, проверка формата, при наличии immutable retained object |
| **RegistryRevision** | Редакцию/согласованный пакет справочников и mappings | Для ОКВЭД несколько ресурсов должны относиться к одному принятому комплекту |
| **TransformationRevision/MethodRef** | Версию метода, кода, параметров, существенных зависимостей | Те же XLSX при разных формулах АПК способны дать разные результаты |
| **DerivedResult/Artifact** | Вычисленное значение или материализованный файл | Имеет связь с реально потреблёнными inputs и вычислением, но не подменяет source |

Здесь `FetchReceipt` и `SourceSnapshot` — различимые роли, **не требование создавать две таблицы на каждый файл**. Компактный run manifest может содержать эти поля вместе. Вложенный ZIP-контейнер и его оригинальные члены имеют разные byte identities; fingerprint только собранного архива не заменяет fingerprint скачанных файлов.

### Временные оси

1. **`observed_at/fetched_at`:** момент фактического получения/наблюдения, фиксируемый при получении bytes; обычно UTC с явно указанной точностью.
2. **`source_published_at`:** заявленная дата публикации издателем; может быть UNKNOWN и не совпадает с временем скачивания.
3. **`reference_period`:** дата или период, к которому относится банковская/макроэкономическая величина.
4. **`effective_from/to`:** время действия классификатора, нормативной методики, mapping или статуса объекта.
5. **`computed_at/exported_at`:** время расчёта и создания результирующего артефакта.

Показатель следует понимать как значение за экономический период `t`, *возможно пересмотренное* в редакции, известной на дату `v`. Это статистический **vintage**, наглядно представленный историческими редакциями [ALFRED](https://alfred.stlouisfed.org/) и [FRED vintage API](https://fred.stlouisfed.org/docs/api/fred/series_vintagedates.html). Общая bitemporal DB от этого логически не требуется: для конкретного результата могут хватить fetched_at/reference_period/источниковой версии.

## 3. Локатор, побайтовая тождественность, экономический смысл и равенство результата

Тот же URL и filename означают только локаторное сходство. Разные `SHA-256` реально прочитанных bytes доказывают их различие. Одинаковый digest при корректной процедуре hashing делает байтовую тождественность практически крайне убедительной, но **не удостоверяет** издателя или достоверность наблюдения.

Две XLSX могут быть семантически эквивалентны при разном ZIP metadata, порядке, форматировании или encoding. Без явной схемы сравнения нельзя объявить semantic equality только потому, что values кажутся похожими. Наоборот, равный числовой результат может возникнуть при разных данных и формулах. Отсюда пять независимых видов «одинаковости»: URL, bytes, statistical semantics, method revision, output value.

Для расчётов одной экономической величины следует сохранять достаточно информации, чтобы отличить изменение **входных bytes** от изменения **метода**. Пример: официальный файл за июль, скачанный в августе, позже заменён по прежнему имени в октябре. Timestamp двух запусков говорит, *когда* обращались; два SHA доказывают наличие двух byte revisions; старые retained bytes нужны для точного воспроизведения прежнего результата. Эксперт всё равно решает, принимать ли пересмотренные данные.

Второй пример: один и тот же input XLSX, но метод расчёта АПК в двух versions использует разный состав кодов. SHA одинаков, outcome различается по `method_ref` и `core_revision`. Третий, особенно важный для статистической доказательности: опубликованное округлённое значение `6` с шагом 1 описывает допустимый latent interval `[5.5,6.5)`, а не точный скрытый итог. Byte-identity никак не повышает силу доказательств реконструкции, основанной на assumptions. См. [сила статистических утверждений](publication-rounding-and-claim-strength.md).

## 4. Как обнаружить замену по неизменному URL

Минимальный проверяемый процесс — это не регистрировать ссылку, а сделать наблюдение:

```text
request/response
  → UTC observed_at и логический источник
  → фактический locator/статус ответа
  → реальные response bytes + SHA-256 + размер
  → минимальная container/format и domain validation
  → source receipt + связь с конкретным Run
  → (optional) сравнение предыдущего receipt того же source meaning
  → (optional) immutable retained raw, если нужен replay
```

Hash имеет смысл вычислять **на фактических байтах, использованных расчётом**. Иначе изменение входного файла между `stat` и `read` приведёт к checksum одной версии и parsed values другой. Для локального Excel предпочтительно materialize/read-once/hash-on-read, а для потокового network input — инкрементальный SHA-256 с памятью `O(1)` относительно длины потока. Размер данных `N` даёт `O(N)` операций hashing; полный архив всех повторных снимков стоит `O(N)` хранения на сохранённую редакцию.

### HTTP validators — полезные подсказки, не универсальные хэши

`ETag` может быть strong либо weak, `Last-Modified` выражает серверное представление времени. [RFC 9110 §8.8](https://www.rfc-editor.org/rfc/rfc9110.html#section-8.8) **не** делает их вычисленным клиентом SHA-256. `HEAD` может экономить запросы, но не доказывает identity нового payload. Conditional GET с `304 Not Modified` позволяет обращаться к **сохранённому известному** представлению только если прежние bytes действительно доступны и сопоставимы. `304` без исходного объекта — ситуация **INPUT_UNAVAILABLE**, а не удачный download.

| Наблюдаемая комбинация | Корректный вывод | Ошибка ложного подтверждения |
| --- | --- | --- |
| Тот же URL/имя, иной SHA | Иная редакция bytes | «Источник официально исправил статистику» без domain authority |
| Новое имя, прежний SHA | Та же byte identity | «Новые данные» только по filename |
| ETag иной, SHA прежний | Серверное метаданное изменилось | «Публикация исправлена» |
| ETag прежний, SHA иной | Реальные bytes различны; конфликт metadata/negotiation | «Содержимое прежнее» по ETag |
| `304` и нет cached payload | Нечего повторно использовать | «Файл скачан» |
| `200`, а внутри HTML | FORMAT_MISMATCH либо validation error | Пустой успешный XLSX |
| Есть raw, schema parser устарела | SCHEMA_MISMATCH, сохранить evidence | «Нет наблюдений» |
| Старый source отказывается отвечать | FETCH_FAILED; старая копия может иметь иную freshness | Автоматически объявить old cache новым |
| ZIP rebuilt с иной metadata | Byte revision нового контейнера | Без domain comparison объявить изменения самих рядов |

Подлинность — **другая ось**. Фактический checksum удостоверяет лишь сохранённый объект относительно прежнего digest. Чтобы утверждать происхождение, нужны publisher identity, корректное сетевое доверие/redirect provenance и, где публикуются, подписи или официальные checksums. Сетевой redirect/caching path следует отличать от публичного канонического source locator; sensitive network identifiers, secrets и query tokens не входят в общую карточку provenance.

## 5. Минимальное свидетельство фактически использованного входа

Успешно полученный byte-oriented input может не входить в глобальный реестр, но полезен компактный `BASIC` source receipt. Семантические обязательства для выбранного профиля:

| Поле | Смысл и квалификация |
| --- | --- |
| `observed_at` | Время **фактического** acquisition, не последующего экспорта |
| `source_label/source_id` | Описывает исходную публикацию; глобальный ID необязателен |
| `source_locator` | Безопасный URI либо workspace-relative path; origin отдельно от runtime маршрута |
| `sha256 + size` | Практическая byte identity, если байты доступны; `null` с причиной лучше вымышленного digest |
| `outcome + validation` | Различает успешную загрузку, transport failure и ошибку формата/смысла |
| `reference_period` | Economic period при наличии в предметном контракте |
| `retained_ref` | Опциональная ссылка на сохранённый immutable payload с явным lifetime |

Для производного результата требуются `operation_id`, конкретный Run/Case при наличии, фактически влияющие параметры, core **build revision**, ссылки на реально использованные inputs и соответствующие RegistryRevisions. `method_ref` достаточно гибок: может ссылаться на доменную `operation@commit`, существующий методологический документ `path@revision#anchor`, официальный specification в действовавшей редакции или сочетание оснований. В простом raw collector методическая ссылка может отсутствовать; обязательная энциклопедия формул принесла бы больше стоимости, чем доказательств.

Нельзя включать в общий provenance credentials, authorization headers, чувствительные path, кэшированные имена секретных ресурсов и полные raw inputs только ради полной «наблюдаемости». Человеческая `method_note` полезна как qualification, но не подменяет машинную проверку. `run_id` идентифицирует попытку лучше timestamp: несколько параллельных задач могут иметь одинаковую секунду загрузки.

## 6. Шкала доступности доказательств повторения (исследовательская R0–R4)

Уровни ниже показывают **какую проверку возможно честно обещать**, а не отраслевой стандарт:

| Уровень | Содержание обещания | Что отсутствует или ограничивает |
| --- | --- | --- |
| **R0 undocumented** | Итог существует без восстановимых оснований получения/метода | Нет прослеживаемого inputs |
| **R1 traceable observation** | Известны source/observation time/операция | Прежние bytes могут быть заменены на том же URL |
| **R2 byte-verifiable** | Зафиксированы SHA/size/validation для сравнения предоставленной копии | Старый raw payload необязательно сохранён |
| **R3 replay-capable** | Retained inputs, registry/method/code revisions, значимые параметры и необходимые версии среды доступны | Реального повторного прогона и сравнения ещё могло не быть |
| **R4 replay-verified** | Повтор исполнен, выходы сопоставлены по заранее выбранной семантике; есть test witness | Успешное совпадение не доказывает корректность экономической формулы |

Это шкала **возможности и факта replay**, которую нельзя сворачивать в одну общую оценку качества вместе с: (а) **integrity** полученного payload; (б) **semantic assurance** интерпретации и допущений. Даже R4 SORS может вернуть вывод низшего assumption tier, если повторился прежний способ оценки. Исторический статус R3 должен быть квалифицирован как `replay unavailable now`, если raw пользователь позднее удалил; digest и факт старого Run сохраняются.

Для численно чувствительного replay одной версии Python package может оказаться мало: значимы solver, `numpy`/`pandas`, float/Decimal, seeds, locale, timezone, schema, registries и implementation config. Однако базовый профиль не обязан для каждого XLSX сохранять полный `pip freeze`. Это риск-ориентированное расширение для методов с высокой ценой отклонения.

## 7. Прямая проверка текущего core: где след обрывается

[HTTP downloader](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/base/net/http.py) возвращает `DownloadResult` с status, response bytes, error, final URL и headers. В общем интерфейсе нет единого обязательного timestamp и byte snapshot identity. Само наличие retry/backoff и min-size контроля не доказывает provenance конкретного расчёта.

[Collector contracts](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_file_collector/contracts.py) содержат source ID/URL, file name/size/used/final URL и typed failures, но `CbrCollectedFile` не фиксирует hash/observed_at/raw revision. [Collector downloader](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_file_collector/downloader.py) фильтрует известный HTML вместо файла и слишком маленький payload; это не domain semantic validation. [Collector save](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_file_collector/save.py) создаёт ZIP или отдельные файлы из полученных bytes, с overwrite, но не сохраняет обязательный fingerprint каждого member. Следовательно, реальное ядро содержит хорошие точки для capture, **не готовый универсальный receipt**.

В [escrow sources](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/escrow/sources.py) `_source_id_from_absolute_url` вычисляет SHA-1 от **строки URL**, не от body. Один URL при заменённых bytes сохраняет тот же source_id. [CBR industry sources](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/macrobanks/cbr_industries/sources.py) выводят временные подсказки из filename, которые не являются byte revision. [Registry selector](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/registries/_loader.py) выбирает packaged resources по `mtime`; выбор последнего по файловому времени не удостоверяет официальную редакцию. Банковские aliases/replacement/lists и ОКВЭД `data/meta/structure` могут независимо изменяться и требуют согласованного bundle identity, если их смысл влияет на результат.

Домены различаются: collector остаётся raw preservation; escrow зависит от discovery/layout parse; cbr_forms совмещают physical/semantic schema; cbr_industries рассчитывают derived industry groups; SORS ведёт собственный богатый evidence/proof/crosswalk/solver lineage, который базовый receipt **не должен заменять**. FRG может классифицировать/очищать рабочие файлы без факта внешней публикации, поэтому нельзя каждому FRG trace приписывать `source_published_at`. Локальный пользовательский XLSX должен fingerprint-иться при фактическом чтении и маркироваться как `user_provided`.

### Что именно должен помнить registry

Для классификаторов существенны и official data revision, и policy overlays. В [банковском registry](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/registries/cbr_banks.py) выделяются имя/aliases/списки; [ОКВЭД2 loader](https://github.com/ForestTiger-GH/stratbox/blob/8459dc58922b7e8df853cf1d9e8131fa9e132580/src/stratbox/registries/rosstat_okved2.py) читает `data/meta/structure` отдельно. Для корректного replay важна **конкретная сочетанная редакция** и compatibility, а не автоматически «самый новый» файл. Core code revision может удостоверять packaged resources лишь при соответствующем build/manifest contract; он **не** фиксирует статистический файл, скачанный после установки.

## 8. Разделение владельцев, стоимости и хранения

**Ядро** — capture фактического payload/timestamp, fingerprint, semantic source bindings, метод и registry refs, доменная validation. **Приложение** — связывание результата с Run/Case, persistence, выбор аудитории и пользовательские проекции. **UI** — короткая карточка времени/источника/availability с отдельной подробной страницей. **Внешняя управляющая платформа** — installed build identity/managed storage capabilities, но не экономический SourceSnapshot. Это распределение — объяснённый *целевой вариант*, не описание готового общего Data/StateStore API.

Продуктовый data root может содержать raw inputs/XLSX, private operational state — историю небольших receipts; одно не обязано жить внутри другого. При сохранении raw важно последовательно отличать `FETCHED → HASHED → VERIFIED_FORMAT → STORED → PUBLISHED`, а после неизвестного storage acknowledgement — `OUTCOME_UNKNOWN`, а не подтверждать `RETAINED` вслепую. [LDD staged publication](../../ldd/artifacts/staged-publication.md) ещё является кандидатом.

Модель может иметь `CapturePolicy: off/basic/replay` с разной глубиной сохранения. Базовый timestamp может возникать при фактической загрузке, а optional `RunProvenance` храниться в памяти Python либо рядом с результатом в одном маленьком JSON. Не нужно создавать отдельный методический файл на каждый Excel лист, глобальную SQL БД для всех наблюдений или машинную регистрацию каждого поля таблицы. Отправка чужих конфиденциальных input bytes во внешний Git без разрешения недопустима.

## 9. Стандарты и альтернативы без автоматического импорта инфраструктуры

Подходы различаются по назначению. [W3C PROV-DM](https://www.w3.org/TR/prov-dm/) полезен моделью source *Entity* → computation *Activity* → output *Entity*, с причастными *Agents*; его RDF/OWL сериализация для каждого Excel не обязательна. [FAIR principles](https://www.nature.com/articles/sdata201618) и [Ten Simple Rules](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1003285) поддерживают identity/metadata/reproducibility, но не требуют одного сервиса. [SDMX](https://sdmx.org/standards-2/) и [DDI Lifecycle](https://docs.ddialliance.org/DDI-Lifecycle/guide/Structural%20Features/Versioning/) помогают, когда источник реально использует versionable статистические структуры. [Frictionless Data Package](https://specs.frictionlessdata.io/data-package/) может быть переносимым manifest набора ресурсов, [RO-Crate](https://www.researchobject.org/ro-crate/specification/1.2/introduction.html) — исследовательским bundle, [OpenLineage](https://openlineage.io/docs/spec/facets/) — adapter событий для крупного процесса, [DataCite](https://schema.datacite.org/versions.html) — публикационным DOI-пространством. Они решают **разные** задачи и не образуют обязательный единый stack.

DVC, lakeFS, Delta Lake, ReproZip могут усиливать retention и environment replay при другой масштабе и цене сопровождения, но сегодня не требуется обязательный content-addressed data lake ради нескольких XLSX. Ограничение «метаданные должны быть небольшими» не означает сокращать специализированные доказательства SORS до одного `ok`.

**Наиболее экономный доказательный профиль, по научной оценке:** `observed_at + source label/locator + SHA-256/size при byte input + validation/outcome + selected method/registry refs`, optional retained raw, без обязательной полной базы всех статистических публикаций. Это предложение, не утверждённый runtime contract.

## 10. Негативные тесты и условия опровержения

| Опыт / отказ | Что должно остаться различимым |
| --- | --- |
| Два `200` по неизменному URL, bytes разные | Две наблюдаемые SHA/времени, одна locator identity |
| Два имени, bytes те же | Два locator-а, одна byte identity |
| ETag прежний, тело другое | Content checksum имеет отдельный вес от server hint |
| `304` без прежнего payload | Невозможность повторного анализа |
| `200` + HTML вместо XLSX | Ошибка domain validation, не пустой результат |
| Прежняя raw копия удалена | R3 перестаёт быть доступным; остался доказательный digest |
| Изменение файла при hash/stat/read | Hash согласован с реально использованным payload |
| ОКВЭД `data` и `structure` из разных revisions | Ошибка bundle validation, без тихой подмены |
| Input SHA один, method revisions разные | Два вычислительных метода и соответствующая provenance |
| Авария после staging до publish | `STAGED` не выдаётся как `PUBLISHED` |
| Python notebook без GUI | Provenance доступен из core result без user chat |
| Два одновременных Run с одним временем | Отдельные run identities |
| Токен внутри URL | Shared receipt sanitized |
| SORS с иным assumption tier | Равный SHA не повышает статистическую доказательность |
| Две XLSX-упаковки для одинаковых чисел | Разные byte identities, semantic equivalence требует проверки |
| Разница часов двух клиентов | UTC и scope/clock uncertainty фиксируются честно |
| ACK storage потерян | OutcomeUnknown и reconciliation |
| Пакет с тем же version, но иным registry content | Build fingerprint/manifest различает |

Эта матрица **не отчёт о выполненных испытаниях**. Рекомендуемое ядро пилота: различие одинакового URL и разных bytes, одинаковых bytes по разным URL, HTML ошибку, отсутствие raw для replay, разные method revisions, Python-only operation, sanitization и пакетные manifest revisions. Fault injection при внешнем effect необходим до обещания R3.

## 11. Реальные нерешённые вопросы и условия пересмотра

Не приняты: обязанность SHA для каждого источника; допустимая clock uncertainty; срок и класс retention; место public/private receipt; правила `SourceDefinition` без глобального каталога; предельный объём domain provenance; политика `method_ref`; способ идентифицировать matched publisher version; критерии semantic result equality для R4; версии packaged registries; этапы общего host/AI/web UX; storage/publish durability и фактическое измерение затрат.

Ключевой конфликт более ранних предложений «единый каталог/source governance для всего» с более поздним потребительским интересом в *минимальном следе реально использованных inputs* разрешается **разделением обязанностей**: curated catalog допускается для повторяемых важных источников, но receipt конкретной операции не зависит от полной регистрации всех источников. Самостоятельная ответственность эксперта за статистическую интерпретацию сохраняется.

**Reopen:** изменение текущего downloader/registry load, внедрение реального receipt/retained storage, изменившиеся HTTP publisher validators, новый потребитель с обязательным replay, прямые user/Product Decisions о полноте источников, доступный независимый integration test, новые официальные публикационные версии. Любая фактическая гарантия касается конкретной source version, build и runtime profile.
