# Системный контекст Strategy Box

**Baseline:** Target WHAT `TW-SB-2026-10-09-CANDIDATE-1`; Target HOW `TH-SB-2026-10-09-CANDIDATE-1`; Architecture `PA-SB-2026-10-09-CANDIDATE-1`.

## Акторы и внешние контуры

- **Аналитик** задаёт источники, периоды и параметры банковско-макроэкономических расчётов, интерпретирует данные/артефакты.
- **Operator/maintainer** диагностирует сборку и состояние работы, применяет разрешённые меры восстановления.
- **Разрешённый машинный потребитель** использует только назначенный набор доступных capabilities; наличие такого потребителя не создаёт самостоятельных прав.
- **Издатели внешней статистики** публикуют данные, определения, единицы и ревизии; они не входят в программную систему.
- **Внешняя managed platform** устанавливает/запускает окружение и передаёт подтверждённый activation/session context; не владеет аналитическими методами.

## Логические части целевого продукта

```text
human or permitted machine consumer
       |
       v
Windows surface / conditional future surface
       |
       v
application semantics and execution authority (logical candidate)
       |                                  \
       v                                   -> platform integration adapter -> external managed platform
analytic core: sources, registries, domain operations
       |
       v
controlled storage/data and published artifacts
```

Связь c managed platform **не** утверждает готовность Data/Control Plane или сетевого API на текущей версии. Core может использоваться как библиотека самостоятельно без application/surface. Зависимость клиента от общего application contract нужна в будущем только при фактическом принятии shared execution.

## Варианты

**Local single-user:** действующая Windows поверхность и Python core без подтверждённого durable shared service. **Shared-node/hosted:** условный профиль с самостоятельной authority и network access; обязательны отдельное принятие, контракт платформы и проверка security/operability. **Mobile:** условное lightweight представление, без гарантии выполнения расчётов на устройстве.

**Изменения:** внешний контракт обновляется только по direct version evidence; новая surface или service boundary появляется лишь по доказанной задаче deployment, isolation, ownership или lifecycle.
