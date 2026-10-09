# Распределение ответственности — кандидатная реализационная архитектура

**Status:** `PA-SB-2026-10-09-CANDIDATE-1`. Статусы `EXISTING` отражают прямых implementation owners; `CONDITIONAL` обозначает логическое целевое размещение, требующее Product Authority.

| Семантическая ответственность | Implementation owner / статус | Обязательная граница и failure ownership |
| --- | --- | --- |
| Предметные модели, публикации, канонизация, вычисления | `stratbox`, EXISTING | Внешний caller не меняет доказательную силу результата; ошибки источников остаются доменными |
| Общие нейтральные порты (FileStore, сетевой IO, styles) | `stratbox`, EXISTING | Конкретный backend владеет transport errors, не переписывает доменную методологию |
| Catalog/domain Operation contracts | Core logical owner, PARTLY EXISTING | Поддерживаемый use case отделён от UI/scheduler; будущий uniform API — CANDIDATE |
| Run/Job identity, admission, lifecycle и effect reconciliation | Application authority, CONDITIONAL | Единственная точка переходов состояния после принятия shared profile; физическое размещение OPEN |
| Durable application state, аудит и permissions | Application authority, CONDITIONAL | Права проверяются перед действием, storage policy требует Product Decisions Q-02/Q-03 |
| Сценарная композиция, формы, пользовательские projections | Windows app currently; shared semantics as candidate | UI получает read model и не заменяет core или authority |
| Windows native rendering, interaction, accessibility | `stratbox-windows`, EXISTING | Клиент отображает confirmed/reported statuses, отличает degraded/unknown |
| Android/Web rendering | Future owners, CONDITIONAL | Появляются только после принятия отдельного профиля/репозитория |
| Platform node, activation, managed lifecycle | AppDock external owner, EXISTING only where versioned contracts prove | Platform health, install/recover distinct from analytic Job result |
| Artifacts source/provenance semantics | Domain core, EXISTING partly | Core отвечает за аналитический смысл, исходники и применимость результата |
| Artifact catalog, visibility, retention | Application authority, CONDITIONAL | Не путать raw bytes, artifact manifest, пользовательское право доступа |
| Storage bytes / workspace access | Neutral storage adapter and actual environment, variant-bound | Границы файлового namespace и integrity проверяются на actual backend |
| Safe log/event projection | Domain/application scoped owners, CONDITIONAL | Технические трассы/секреты не попадают в общий пользовательский feed |

## Сквозные инварианты и ответственность

**Создание Excel по доменным данным:** core владеет расчетом и видом data result; вызывающая application authority (если она введена) принимает команду, решает статус и право публикации; storage adapter записывает bytes; Windows показывает только то, что действительно сохранено и опубликовано. Если запись неполна — core мог завершить вычисление, но artifact publication остаётся failed/unknown.

**Отказ рабочего окружения:** platform владеет своим node health; application диагностирует affected Jobs, core не выдаёт transport failure за отсутствие статистических данных. Каждая поверхность показывает разрешённую, audience-safe информацию.

**Смена версии источника:** domain owner определяет влияние на метод и данные; application управляет ретенцией и доступностью ранее сформированных results, если этот компонент утверждён; клиент показывает version/freshness, а не скрытно заменяет историю.

## Неурегулированные распределения

- Логическая shared authority может быть модулем, процессом или отдельной поставкой: `UNRESOLVED_BLOCKING`, Q-01/Q-02.
- Транзакционная граница между Job state, effect receipts и manifest publication не установлена: `UNRESOLVED_BLOCKING`, Q-02/Q-05.
- AppDock-specific remote APIs требуют свежей версии платформенного owner: `EXTERNAL_DEPENDENCY`, Q-06.
- Вопрос того, кто вправе утверждать risk grade и аудит операций: `PRODUCT_POLICY`, Q-03.
- Точная схема shared presentation models: `BOUNDED_OPEN`; нельзя преждевременно закрепить конкретный toolkit.

Кандидат годится для установления ответственности и выявления gaps, **но не допускает production deployment** без Target HOW/WHAT admission.
