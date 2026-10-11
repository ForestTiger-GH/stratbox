# Состояние, storage и восстановление: согласование позднего исследования с прежним корпусом

**Статус:** BOUNDED PRODUCER RECONCILIATION, не независимая проверка и не Product Decision. **Дата:** 2026-10-11. **Источник:** `SB-SRC-0556` (04 research, exact blob `f919df034a2e15ae8947d51aaec9cd564fe462ad`, frozen `stratbox@388e3d61ec01350d3b7d35ea4a97a21db0b36f97`), полный текст L1–L785. **Результат extraction:** 76 адресованных provisional material units `SB-U-0556-001..076` в [ledger](../units/LATE-04-STATE-0556.jsonl). Все единицы имеют предварительную тематическую публикационную цель в [Science](../../../../docs/science/state-and-recovery/authority-durability-and-recovery.md); окончательная проверка source→Science остаётся OPEN.

## Существенный хронологический конфликт

Предшествующее исследование `03-consolidation-research/strategy_box_03_topic_05_state_persistence_collaboration_consolidated_research_2026-10-09.md` в разделах 0.1, 5.1–5.5 и 6.4, будучи гипотезой, предпочитало **node authority + локальный транзакционный SQLite** как старт первой зрелой модели. Поздний оригинал `SB-SRC-0556` не отвергает node/application authority, но передаёт более точное человеческое ограничение: минимальный надёжный переход **может обойтись без SQLite**, если будет один writer, один versioned atomically committed state document, отдельный user preference store и verified recovery; внешний AppDock должен предоставить/конфигурировать среду и в будущем договороспособный DB-provider. Выбор физического backend-а остаётся **открытым**, а не автоматически решается количеством повторений предложения SQLite.

Линия доказательств для исходной проблемы сильнее обоих design defaults: напрямую проверенный Windows `HistoryPersistenceService` при exact baseline `959e9c4ce1441124af5111c1e025041714e04d3b` сохраняет пять раздельных JSON, подавляет повреждение в `[]` и не оформляет один общий commit; `runtime/config.py` обрабатывает невалидный пользовательский конфиг иным образом. Это прямое описание текущего code path, не происшествие data-loss в эксплуатации. Универсальный DB API внешней платформы, производительность новой системы и RPO/RTO не подтверждены прямыми испытаниями.

## Дисциплина различений, сохранённая в научном владельце

- Авторитетное прикладное состояние, platform/node/activation projection, пользовательские настройки, stage/physical artifact, source snapshot, кэш, presence и журналы имеют разные семантические owners, recovery и durability tiers; хранение рядом не объединяет их.
- `G0` ephemeral, `G1` reconstructible, `G2` durable record и `G3` effect-coupled — исследовательская типология, а не утверждённые SLA. Crash recovery, backup recovery, effect reconciliation также разные обязательства.
- Атомарный state-file replace, атомарный command admission и публикация сетевого/файлового эффекта имеют **три отдельные commit boundaries**. Ни наличие SQLite, ни атомарный replace не дают одну транзакцию с XLSX.
- Shared user chat может иметь одну history authority и множественные per-principal read cursors. Параллельные clients не должны превращаться в независимых писателей одного network-shared JSON/SQLite.
- `FAILED` / `INTERRUPTED` / `OUTCOME_UNKNOWN` имеют разные основания. Lost ACK и возможный внешний эффект не допускают слепой automatic retry.
- Append-only журнал с segments и snapshots возможен, но усложняет framing, integrity, compaction и mid-log corruption; Event history не делает полный event sourcing обязательным.
- SQLite локального узла и PostgreSQL service — разные условные профили. WAL напрямую на сетевой папке не является корректным multi-host API. Durability `synchronous` зависит от режима и FS; внешний managed root не доказывает power-loss resilience.
- Restore с новой `store_generation` и запретом stale writer — иной смысл, чем reset UI; одноразовая migration пользовательских данных совместима с отказом от backward API compatibility.
- Ручное удаление пользователем XLSX допускает видимый `missing` при сохранении исторической записи о Run; без отдельной политики нет обязанности искать/восстанавливать файл.

## Полнота одной этой bounded работы

Прочитан один 785-строчный первичный Research original. Подробная Science статья содержит механизм, аргументы, отвергнутые упрощения, матрицы отказов, внешние прямые технические опоры и статус альтернатив. 76 единиц получили `science_destination`; сам ledger признаёт `provisional_extracted_and_published_not_reverse_verified`. **Нельзя считать 76 равными заведомо исчерпывающему числу смысловых единиц**, пока отдельный reviewer не проверит исходник по строкам и каждую публикационную цель на полноту аргументации. Каждое упоминание человеческого комментария в исследовании остаётся вторичным carrier до отдельного точного чтения авторизованного DOCX; этот источник нельзя объявлять полностью ассимилированным по одному Research-пересказу.

Смежные Research 02 о background, execution, multiuser, artifacts, formats и 03 topic 05 создают *зависимое* свидетельство; они не являются семью независимыми direct implementation checks. Дополнительный опубликованный Science [Capability definitions](../../../../docs/science/capabilities/definitions-plans-and-execution-truth.md) использует ранее extracted темы, но их обратное распределение по всем смысловым единицам остаётся несертифицированным.

## Product route и незакрытые вопросы

Тематические вопросы из 04/03 `Q03-01..16` дополняют прежние `SB-Q-01,02,04,05,06,07,09,10`: кто владеет state и shared write, где размещается authorised storage, должен ли provider provision DB, сроки хранения, параметры без секретов, local vs host job lifetime, RPO/RTO, backup/restore owner, network access, момент SQL migration, source snapshot retention, user deletion artifacts, audit, HA, restore fencing и remote preference guarantees. **Все перечисленные решения остаются неутверждёнными**, а документация Science изучает альтернативы, не утверждает API signatures.

**Следующая проверка:** независимый проход `SB-SRC-0556` и ledger→новая Science статья, затем прямое сравнение с полным оригиналом 03 topic05 (не только доступными extract/headings), другие 11 late original 04 исследования и документы 01/02/03. Состояние корпуса, показатели и отложенные независимые gates задаёт [STATE.md](../STATE.md).
