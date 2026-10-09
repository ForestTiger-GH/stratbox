# Windows — компонентное целевое представление

**Implementation owner:** `ForestTiger-GH/stratbox-windows`. **Status:** отдельное приложение подтверждено; перспективный shared execution `CANDIDATE`.

**Назначение:** понятный пользовательский доступ к рабочему пространству, каталогам операций, сценариям, кейсам, логам, результатам и связанным действиям. Настоящие функции и ограничения зафиксированы отдельно в [Current HOW](../../current-how/windows-application.md).

**Наблюдаемый компонент:** Windows Qt surface, управляемый activation context, сценарный chat/inspector, локальная JSON история и последовательное выполнение. Названия режимов «Фоновые», «Поручения» и «Участники» в UI сами по себе **не обещают** полноценный scheduler, сетевое взаимодействие или серверные права.

**Целевые candidate properties:** platform-neutral semantics для forms/operations/scenario projections; пользовательский статус не опережает подтверждённый run/effect outcome; UI не хранит единственный durable execution truth при переходе к shared-node; явные диагностика и восстановление; настройки только с понятным пользователю эффектом.

**Поверхность/ядро:** Windows client может сохранять свой presentation toolkit, не навязывая его core и будущим поверхностям. Точный backend API, state schema и mode управления требуют отдельных решений и проверки.
