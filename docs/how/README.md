# Target HOW — механизмы Strategy Box

**Candidate design baseline:** `TH-SB-2026-10-09-CANDIDATE-1` на ограниченной предметной модели [Target WHAT](../what/README.md), `TW-SB-2026-10-09-CANDIDATE-1`.  
**2026-10-12 authority update:** [Host target](../what/strategy-box/host-deployment-commitment.md) is now **admitted as necessary and planned** for both Web/domain and Windows/AppDock-hosted connections. Host-specific HOW details remain candidate until deployment/security/storage choices are approved.

**Admission:** только независимость аналитического ядра и правильное распределение действующих реализаций являются принятой границей. Механизмы долговременного исполнения, сохранности артефактов и совместной работы остаются **условным проектом**, поскольку связанные требования `TW-C01..07` и эксплуатационные профили ещё не получили Product Decision.

Этот раздел разделяет техническую реализацию (**HOW-R**), правильное применение (**HOW-A**) и эксплуатацию/восстановление (**HOW-O**) как три связанные обязанности:

- [Two host deployment and client attachment profiles](hosting/host-and-client-deployment.md) — scoped HOW-R/A/O candidate implementing admitted HOST-O1..O7.
- [Исполнение, состояния и внешние эффекты](execution/execution-and-effects.md) — кандидатная модель HOW-R.
- [Работа аналитика и внешнего разрешённого потребителя](application/invoke-and-interpret.md) — HOW-A, включая ошибки использования.
- [Наблюдаемость, диагностика и восстановление](operations/diagnosis-and-recovery.md) — HOW-O, включая деградацию и ограничения.
- [Проверяемые контракты и negative vectors](verification/acceptance-vectors.md) — связь с требованиями и наблюдаемыми результатами.

**Неизменная граница:** библиотека доменной аналитики остаётся самостоятельным вычислительным владельцем, а конкретные интерфейсы пользовательских приложений и платформенного запуска оформляются отдельно. Полноценное внедрение схем, гарантий хранения, ошибок и распределённого запуска требует явного принятия необходимых Target WHAT-свойств. Инженерный код и deployed environment этим документом не меняются.

**Точность ссылок:** HOW самостоятельно содержит достаточные условия применения и отказа.**Implementation-near refinement:** [LCD — Low Code Design](../lcd/README.md) may be activated downstream of admitted WHAT, this HOW and [Product Architecture](../architecture/README.md) to close material construction choices for a bounded scope. Existing [LDD](../ldd/README.md) supplies selective detailed mechanisms; neither document family creates implementation authority or proof of executable code.

**Точность ссылок:** HOW самостоятельно содержит достаточные условия применения и отказа. В нём нет требуемого для эксплуатации перехода через научные исследования.
