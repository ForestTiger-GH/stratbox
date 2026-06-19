# Strategy Box App Surface

Strategy Box теперь строится как scenario-first рабочая поверхность поверх AppDock-managed среды.

## Главная модель

- `OperationSpec` — атомарный внутренний шаг.
- `ScenarioSpec` — пользовательская рабочая единица.
- `ScenarioRunCase` — конкретный запуск сценария, который отображается в центральном чате одной динамической карточкой.
- `OperationalEvent` — структурированное событие для логов, фона, системы и будущего ИИ-слоя.
- `ArtifactRecord` — результат с происхождением: сценарий, кейс, операция, автор и путь.
- `LogRecord` — технический лог, связанный с шагом и кейсом.
- `AssignmentRecord` — поручение, связанное с пользователем, сценарием, кейсом или артефактом.
- `BackgroundProcessState` — runtime-состояние фонового процесса для chips и событий.

## UI

Desktop surface использует новый shell:

- верхняя полоса с пользовательским меню;
- mode rail слева;
- левая панель режимов: проводник, отдельные сценарии, сценарные блоки, фоновые процессы, участники, поручения;
- центральный сценарный чат;
- нижний composer выбранного сценария;
- правая выезжающая inspector-панель.

Правая панель открыта по умолчанию, но архитектурно является вспомогательным drawer-layer. Она уезжает за правую грань окна и освобождает центр. Внутри панели находятся вкладки: кейс, логи, артефакты, параметры и узел. Панель теперь case-aware: выбор карточки в центре фильтрует логи и артефакты по выбранному кейсу.

## Иконки

Сейчас mode rail использует текстовые placeholder-символы. Для финального премиального вида нужно заменить их на SVG/PNG outline-иконки в `src/app/resources/icons/`:

- `mode_workspace.svg` — проводник / папки;
- `mode_atomic_scenarios.svg` — отдельные сценарии / действие;
- `mode_scenario_blocks.svg` — сценарные блоки / цепочка;
- `mode_background.svg` — фоновые процессы / часы;
- `mode_people.svg` — участники;
- `mode_assignments.svg` — поручения;
- `inspector_case.svg` — кейс;
- `inspector_logs.svg` — логи;
- `inspector_artifacts.svg` — артефакты;
- `inspector_parameters.svg` — параметры;
- `inspector_node.svg` — состояние узла;
- `status_running.svg`, `status_success.svg`, `status_warning.svg`, `status_error.svg` — статусы;
- `artifact_file.svg`, `artifact_excel.svg`, `artifact_zip.svg`, `artifact_folder.svg` — типы артефактов.
