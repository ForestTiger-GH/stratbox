# Наблюдаемость, отказ, восстановление — HOW-O

**Status:** candidate operational contract `TH-SB-2026-10-09-CANDIDATE-1`; **нельзя использовать как утверждённый production runbook** до определения гарантий и фактической среды.

## Нормальный диагностический путь

Пользовательский `Run`/Case представляет предметный результат, `Job` — ход исполнения, `Attempt` — техническую попытку, `LogRecord` — диагностику, `Artifact` — проверенный вывод. Внешняя платформа имеет собственные node/session/health and problem surfaces; их статус не становится terminal outcome доменной операции.

Для эксплуатационной достаточности кандидатный событийный набор содержит: registration/admission, start, stage/progress, effect-start, effect receipt (если доступен), completion, degraded/unknown, recovery decision, version/source manifest. События нормализуются к безопасным кодам; raw trace/correlation context сохраняется в защищённом локальном техническом логе и не выводится всем участникам автоматически.

## Минимальные различения отказов

| Режим | Сигнал клиенту | Допустимая эксплуатационная реакция |
| --- | --- | --- |
| Источник отсутствует | NotFound с достоверной областью проверки | Пересмотреть source locator; не подставлять `0` |
| Источник недоступен | Transport/Permission/Unavailable | Диагностировать транспорт/право, не выдавать пустую таблицу за корректный результат |
| Output storage заполнен | Write failure, неполный staging | Оставить черновик скрытым, устранить причину, проверка целостности |
| Фоновый worker исчез | Attempt stale, Job/Run UNKNOWN или eligible retry после reconciliation | Проверить durable owner и effects до нового выполнения |
| Параллельный редактор изменил план | Revision conflict | Прочитать новую версию и заново запросить подтверждение |
| Конфиденциальная подробность в ошибке | Safe summary + restricted technical evidence | Redaction до event/user notification |
| Диагностика недоступна | Telemetry degraded | Не менять автоматически истинный статус завершённого расчёта |

## Восстановление: три независимых класса

**Исполнение:** после рестарта восстановить durable jobs и attempts, отличить потерянные workers от подтверждённо завершённых, проверить внешние receipts и lease generations. Без достоверного признака повтор может быть запрещён или потребовать оператора.

**Данные и артефакты:** проверить согласованность registry, source snapshots, bytes, manifests и retention; не объявлять завершённым файл до проверенного publish. Резервная копия БД без обязательных bytes не доказывает восстановление всего продукта.

**Пользовательская поверхность:** восстановить представление и параметры сеанса отдельно от authority state. Повреждённая local projection допускает явную деградацию/пересоздание **лишь если** это именно необязательная проекция, а её источник истины существует и доступен.

## Конкретная эксплуатационная последовательность (условная)

1. Зафиксировать impacted scope и запросить read-only health/diagnostics.
2. Определить принадлежность ошибки: domain result, application job/condition, platform activation/health, storage.
3. Сверить code/source/schema/config revisions и timestamp; определить, было ли подтверждение внешнего эффекта.
4. При UNKNOWN заблокировать blind destructive retry, сохранить evidence, запустить допущенную проверку/ручной recovery.
5. Только после проверки обозначить recovery completed/failed/partially recovered и разрешить возобновление.
6. Отправить другим пользователям лишь audience-filtered condition, если это действительно общий сбой, а policy разрешает совместное уведомление.

## Условия допускa

Реальные `RPO`, `RTO`, log retention, metrics/SLO, обязательность audit sink, access control, частота heartbeat и адрес support-bundle **не установлены** и требуют Product/операционных решений. Для конкретного локального Windows среза подтверждена файловая история и operation logs, но **не** все описанные recovery действия. Каждая команда и результат должны быть верифицированы именно на поставляемой конфигурации. 
