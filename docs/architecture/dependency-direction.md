# Направление зависимостей и безопасные границы

**Architecture candidate:** `PA-SB-2026-10-09-CANDIDATE-1`.

## Базовые инварианты

1. Доменный core не импортирует UI и application orchestration. Core API можно проверить независимо от Qt, desktop launcher и managed lifecycle.
2. Пользовательская поверхность обращается к application use cases или непосредственно разрешённым core operations в current local profile, но не копирует предметные алгоритмы.
3. Application model зависит от абстрактного core/domain API; платформенные активационные сведения доступны только через адаптер конкретного внешнего контракта.
4. Инфраструктурные реализации среды могут заменяться посредством нейтрального API. Доступность расширения, право активации и полномочие совершить рискованное действие — разные факты.
5. Техническая ошибка источника должна сохранять собственную причину при прохождении в operation result, UI и диагностику; каждый слой может создать своё представление, но оно сохраняет различение failure/empty/unknown.

## Проверочные диаграммы зависимости

```text
           Windows UI / conditional future renderers
                           |
                     app contracts
                       |       \
                   core ports   platform-adapter port
                       |                |
                  domain core       external platform contracts
```

Существующая прямая зависимость внутри Windows `runtime.bootstrap → presentation.qt_desktop` является **Current HOW drift относительно предлагаемого общего application contract**, а не доказательством уже достигнутой независимости. Старый smoke test ожидает другую версию manifest, поэтому соответствующая интеграция нуждается в реальной CI-проверке перед release.

## Контракт границы успеха/сбоя

| Граница | Что должен сохранить downstream |
| --- | --- |
| Source → core | Версию, измерение, единицу, источники, неопределённость, отсутствие/ошибку |
| Core → application | Типизированный результат, diagnostics, scope и possible side effects |
| Application → surface | Durable status, valid actions, permission-filtered details, unresolved effects |
| Application ↔ storage | Проверяемую запись, версию/идентичность и recovery proof |
| Application ↔ external platform | Только подтверждённые versioned interface и safe health/problem projection |

## Техническая свобода

Реализация может выбрать язык/СУБД/IPC/UI toolkit и способ публикации при условии прохождения принимающих контрактов. Изменение семантического authority ownership, общих идентификаторов, допустимой неоднозначности эффектов или privacy boundary требует пересмотра соответствующих Product/Architecture Decisions, а не локального refactor.

**Reopen:** изменение прямых product-owner paths, опубликованного интерфейса external platform, принятие shared-node и offline профилей либо тестовый контрпример на границе ошибок.
