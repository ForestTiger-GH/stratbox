# Качества, ограничения и открытые обязательства Target WHAT

**Status:** mixed — явные границы `BOUNDARY_ACCEPTED`, качество runtime пока `CANDIDATE`. Читатель должен видеть, что именно сможет проверить после Product admission.

## Подтверждённые направления и ограничения

1. **Headless аналитическая граница.** Предметные расчёты core не должны требовать Windows UI; их использование в Python остаётся самостоятельным.
2. **Раздельный implementation ownership.** Windows UI и приложенческий слой не меняют семантику расчёта core через копию алгоритма. Внешние platform contracts не становятся кодом ядра.
3. **Переносимость смыслового слоя.** Повторно используемые элементы application/surface проектируются отдельно от платформенно-зависимого рендеринга для будущих клиентов, включая Android.
4. **Безопасность публичного знания.** Опубликованные контракты остаются нейтральными по среде и не распространяют защищённые сведения.
5. **Отсутствие обязательства сохранять устаревший API.** Breaking changes допустимы по решению владельца; отдельная политика обработки существующих пользовательских данных, артефактов и сохранённого состояния определяется явно.

## Кандидатный реестр проверяемых качеств

| Область | Возможное product property / negative case | Решение |
| --- | --- | --- |
| Data trust | Версия source/registry и evidence tier доступны для существенного вывода; неверное превращение missing в zero выявляется | NEEDS PRODUCT DECISION |
| Execution | Восстанавливаемый Run/Job status, корректный результат отмены и retry; сбой UI не создаёт ложный успех | NEEDS PRODUCT DECISION |
| Data persistence | Повреждение авторитетного состояния даёт диагностируемый отказ/degraded, а не тихую перезапись | NEEDS PROFILE/OWNER |
| Effects | Опасный effect требует полномочия, scoped confirmation и receipt; нет непроверенного destructive success | NEEDS RISK POLICY |
| Collaboration | Фильтрация объектов и событий до публикации внешнему клиенту | CONDITIONAL shared-node profile |
| Artifacts | Полная запись+проверка bytes перед terminal published status | NEEDS ARTIFACT POLICY |
| Observability | User-safe problem conditions отдельно от защищённых raw logs | NEEDS PRIVACY/PLATFORM CONTRACT |
| Performance | Диапазон размеров источников, время расчёта, память, GUI responsiveness заданы по профилям | NEEDS MEASUREMENT |
| Accessibility | Keyboard/focus/contrast/readable state независимо от цвета/анимации | NEEDS TEST PROFILE |
| Operability | Recovery test для state+files, честный RPO/RTO и контроль обновления | NEEDS DEPLOYMENT POLICY |

Таблица намеренно **не задаёт числовые пороги**: подходящий уровень должен опираться на реальные устройства, исследованные нагрузки, риск, операционный сценарий и подтверждённые внешние обязательства.

## Приёмка WHAT и зависимостей

На данном baseline доступны проверяемые общие границы и набор candidate properties, но **нет** полного Product Commitment Census для всех source decisions и профильного наблюдаемого поведения будущей системы. Поэтому этот набор пригоден для предметного обсуждения Target WHAT, а не для заявления о готовой полной спецификации. Решение, меняющее смысл продукта, заносится в полномочный target owner и только после этого создаёт обязательство HOW.
