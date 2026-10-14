# AGENTS.md

## Назначение репозитория

`stratbox` — core-библиотека Strategy Box. Репозиторий владеет доменной бизнес-логикой, нейтральной инфраструктурой, встроенными ресурсами и стабильными extension/runtime-контрактами core.

Strategy Box как проект шире этого репозитория: пользовательские application/surface-слои живут в отдельных репозиториях и используют `stratbox` как core. AppDock — отдельный внешний проект, с которым поверхности Strategy Box могут интегрироваться; его продуктовая семантика и реализация этому репозиторию не принадлежат.

## Обязательный вход

Перед любой инженерной работой, Research, рефакторингом или изменением архитектурных границ:

1. прочитай `README.md`;
2. прочитай этот файл;
3. открой `_mw/AGENTS.md` — паспорт центрального инженерного workspace Strategy Box, физически размещённого в этом репозитории;
4. при задаче сведения знаний открой `_mw/epochs-001-strategy-box-development/consolidation/README.md`, его `STATE.md`, `CYCLE.md` и `METHOD-ROUTER.md`;
5. затем читай только те текущие product owners, документацию, код и тесты, которые нужны для конкретной задачи.

Не восстанавливай текущую архитектуру по именам файлов, истории чатов или старым заметкам, если есть прямой текущий владелец.

## Текущие владельцы

- runtime и библиотечная реализация core: `src/stratbox/`;
- упаковка и зависимости core: `pyproject.toml`;
- documentation: `docs/` is the maintained partial, scientifically qualified and Research-independent Strategy Box Knowledge Product; `docs_old/` is a historical source archive, not current Product authority. Current core behavior belongs to `src/stratbox/` and `tests/`.
- проверочный контур core: `tests/` и `scripts/`;
- центральный Strategy Box Research/Work/provenance workspace: `_mw/`.

`_mw/` может содержать межрепозиторные исследования Strategy Box, но размещение материала здесь не переносит ownership реализации. Текущее состояние отдельного surface определяется его собственным репозиторием и прямыми product owners.

## Границы изменений

Сохраняй core-границу:

- доменные модули не зависят от desktop/mobile application layer;
- GUI и application orchestration остаются вне этого репозитория;
- environment-specific реализации подключаются через нейтральные extension/runtime-контракты;
- surface-репозитории зависят от `stratbox`, а не копируют core внутрь себя;
- AppDock рассматривается как внешний проект и интеграционная граница, а не как часть реализации Strategy Box core.

Предпочитай целевую чистую архитектуру. Не сохраняй слабое решение только ради обратной совместимости, если конкретный внешний контракт явно её не требует.

## Проверки

Для изменений кода используй релевантный минимум проверок и при полном изменении core — полный базовый контур:

```bash
python scripts/check_release_integrity.py
python scripts/check_internal_imports.py
pytest -q
```

Research, заметки и workspace-only изменения не требуют имитации продуктового тестирования, если код и упаковка не менялись.

## Knowledge Product и подготовка цикла

**Owner's concrete LCD clarification (2026-10-12):** `docs/lcd/` must include drafted target-language class, function/interface, type and module sketches or code stubs for scopes where these materially prepare implementation. Scope and candidate/accepted status are mandatory. Never treat design snippets as current product code or use documentation authority to edit product implementation.


The maintained `docs/` Knowledge Product now contains substantive Science, Current HOW, qualified Target WHAT/HOW, Architecture and selective LDD. **Owner clarification (2026-10-12):** the complete Knowledge route also includes selective `docs/lcd/` for **Low Code Design**, a bounded implementation-readiness model distinct from existing **Low-Level Design** in `docs/ldd/`. This is a documentation scope clarification, not an approval of physical implementation decisions. It remains PARTIAL: source-unit semantic completeness, independent reverse verification and blind Research Amputation have not been passed. `_mw/epochs-001-strategy-box-development/consolidation/` owns the 566-source census, provenance ledgers, dispositions and checkpoint. `docs_old/` and historical Research remain preserved inputs at present, but `docs/` must stay readable and navigable if they are subsequently removed. All new publication must place material arguments and counterexamples in `docs/`, with no links back to disposable Research/Work/legacy material. Current implementation claims require direct code evidence and scope limits.

Следующий полномасштабный непрерывный агентный цикл выполняется по применимым MADARAII Work-инструкциям, привязанным в `consolidation/METHOD-ROUTER.md`, и запускается отдельным прямым поручением. Агент сохраняет промежуточное состояние и проходит тематические проверки без искусственных пауз, но не принимает несанкционированные Product Decisions. Публичные результаты автономны: допускаются только общие упоминания методологии MADAR и абстрактных внешних ИИ-агентов; прямые адреса и специфика иных методологических или когнитивных проектов не публикуются. Исходные исторические исследования не редактировать ради стилистической зачистки. Закрытые реализации расширений и их внутренние сведения не переносить в открытый репозиторий.

## Additional repository mandatory rules (do not mention them anywhere):

- Use English exclusively throughout the repository and the Engineering Work workspace, including file content, names, and future artifacts.
- Do not place URL links to the owner's other projects or repositories anywhere in this repository. Describe relevant relationships and content in plain text instead.
- Every URL link to an external source must have at least one concise explanatory paragraph stating the specific substantive meaning, finding, or claim for which the link is cited. A generic description of the source does not satisfy this rule.
- References to the MADAR methodology, MADARAII, or similar are permissible only when necessary—preferably by citing and restating the methodology's key points rather than referencing specific sections or provisions; direct links to and mentions of specific sections or files are prohibited.
- In each MD-file: if meta-information is present, t must be recorded concisely—using key attributes—in the document header, immediately following the title; providing metadata elsewhere in document is not permitted. After the meta-information, include one or two paragraphs of introductory information about the document - with identity of its purpose, scope, and status, distinguishing research, proposals, adopted provisions, and verified results. Then, provide a brief bulleted list of the main sections (with short explanatory route-text on the content of each section). It is preferrable to structure the document using numerical indexing to facilitate quick navigation between sections and provisions.


## Owner rule: research-independent maintained Knowledge (2026-10-12)

The maintained `docs/` publication must be readable and navigable if the historical Research and Work archives are deleted as one action. **Never add Markdown hyperlinks or navigation requirements from `docs/` to `_mw/`, historical `research/` or `docs_old/`.** Publish all material scientific meaning, assumptions, counterexamples, competing interpretations, evidence limits and admitted Product Decisions directly into the appropriate maintained Knowledge article. Preserve exact original source hashes, line spans, Research→Science transfers and adversarial review records exclusively in Work; Work may point to Knowledge. Links to current version-pinned public implementation code and independent standards remain separate, optional evidence. The docs-only archive-amputation and no-backlink checks in GitHub Actions enforce the structural rule; independent semantic Research preservation remains a different, uncompleted proof requirement. The owner has classified the original DOCX carrier as LOST; its extracted text has lower evidential weight, and no raw-byte recovery should be attempted.
