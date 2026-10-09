# LDD candidate — атомарно наблюдаемая публикация аналитического артефакта

**Identity:** `LDD-SB-ARTIFACT-PUBLISH-01`. **Status:** CANDIDATE / `TW-C06` ещё не принят.  
**Scope:** один file-like результат аналитического Run в разрешённом workspace.  
**Not in scope:** автоматическое исправление доменных данных, гарантия внешнего cloud commit, формат конкретной СУБД и унифицированная версия FileStore backend.

## Основные инварианты будущего контракта

- Различать вычисленный в памяти результат, файл в промежуточной области, доказанную целостность bytes и доступность опубликованного результата.
- Запрещено показывать `COMMITTED` до успешной проверки фактических bytes и записи видимого каталожного состояния.
- Успешная локальная запись не должна маскировать неизвестный эффект удалённого переноса/rename.
- Один `artifact_id` связывает содержимое, разрешённый owner scope, источник/метод и жизненный цикл публикации; путь — locator, допускающий изменение.
- `cleanup` не может уничтожить единственную ещё необходимую копию для восстановления, пока отсутствует достаточное подтверждение publish.

## Предлагаемая модель

```text
DRAFT
  → STAGING
  → STAGED_BYTES
  → VERIFIED_BYTES
  → PUBLISH_PENDING
  → COMMITTED
```

**Альтернативные результаты:** `ABORTED` до внешнего эффекта; `FAILED` при подтверждённой невыполнимости записи; `OUTCOME_UNKNOWN` при неоднозначности remote-finalize; `QUARANTINED` при mismatch bytes/manifest. Локальная metadata record и физический файл могут иметь разные наблюдаемые промежуточные состояния: терминальность записи об исполнении **не** гарантирует завершённого artifact commit.

| Откуда | Событие/guard | Куда | Необходимое доказательство |
| --- | --- | --- | --- |
| DRAFT | валидирован output scope и permission | STAGING | plan revision, actor scope и выбранный staging locator |
| STAGING | полная запись и закрытие output stream | STAGED_BYTES | writer result, bytes count, закрытый handle |
| STAGED_BYTES | размер и digest подтверждены, schema/domain validation пройдены | VERIFIED_BYTES | manifest + data verification evidence |
| VERIFIED_BYTES | создано durable publish intent | PUBLISH_PENDING | idempotent publish identity |
| PUBLISH_PENDING | atomically-visible materialization плюс каталогизированный publish record | COMMITTED | commit receipt + immutable content locator |
| Любой pre-commit | обоснованный отменённый или fail outcome | ABORTED/FAILED | причина, область возможных уже совершённых эффектов |
| PUBLISH_PENDING | remote ACK потерян | OUTCOME_UNKNOWN | записанная неопределённость и reconciliation link |
| VERIFIED_BYTES/PUBLISH_PENDING | digest mismatch или неверная версия | QUARANTINED | actual vs intended digest, запрещён consumer view |

**Предположение:** не каждый backend умеет атомарный rename, compare-and-swap или content-addressed storage. В таком случае требуется явный более слабый профиль либо адаптер с доказуемым видимым commit-barrier; нельзя заявлять одинаковую атомарность для всех FileStore реализаций.

## Конфликтующие обращения и повторы

Предлагаемый publish key = `(workspace_scope, logical_artifact_id, generation)`; фактический serializer/namespace требует авторизации. Повтор той же immutable manifest-generation возвращает существующий commit либо выполняет reconciliation. Повтор с изменённым digest под тем же generation отклоняется. Параллельный writer может работать с другим staging key, но не публиковать тот же generation без сравнения версии. При потере lease прежний worker не вправе публиковать устаревший generation.

Это **техническая гипотеза**, а не уже принятая гарантия exactly-once внешнего хранилища.

## Восстановление после сбоя

| Crash window | Durable trace | Recovery action |
| --- | --- | --- |
| До staging | Нет bytes, может быть plan | Повторный ввод/перепланирование |
| После частичной записи | Incomplete staging + некоммитнутый intent | Диагностика и quarantine/cleanup по retention policy |
| После верификации, до publish | Manifest + verified temporary bytes | Проверить fingerprint и permission перед продолжением |
| После remote finalize без ответа | `OUTCOME_UNKNOWN` | Разрешённый lookup/finalize reconciliation, без blind duplicate |
| После bytes commit до catalog commit | Blob существует без visible artifact record | Детерминированная reconcile/GC политика, не скрытая `COMMITTED` |
| После catalog commit и до UI refresh | Persistent record подтверждён | UI читает каталог, не запускает повторный publish |

## Test vectors, необходимые перед admission

1. Записать XLSX и остановить writer посередине: нет committed entry.
2. Инжектировать `PermissionDenied` при rename: staging сохранён или явный failure, source bytes не потеряны.
3. Смоделировать ACK loss при финализации и повтор того же key/digest: нет второго visible generation.
4. Параллельно отправить same key/different digest: version conflict.
5. Восстановить после падения между bytes и catalog commit: нет ложной карточки `COMMITTED`.
6. Провести смену прав пользователя между staging и publish: финальное разрешение перепроверено.
7. Искусственно нарушить digest: объект в карантине, payload недоступен как готовый.
8. Проверить низкоресурсный storage и большие файлы без обязательной полной RAM-буферизации.

**Blocking decisions:** Q-02 (storage and retention), Q-03 (effect permissions), Q-05 (Artifact identity), Q-06 (внешние capabilities). **Engineering selection freedom:** формат manifest, конкретный DB transaction engine, internal temporary path, hash algorithm с подтверждённой стойкостью и совместимостью. Данные, уже сохранённые пользователем, требуют отдельного миграционного/архивного решения; отсутствие обязательства на старый API не разрешает их молча уничтожать.

**Next revalidation:** adopted WHAT/HOW revision, backend capability conformance, actual fault injection, exact storage semantics и Product Authority.
