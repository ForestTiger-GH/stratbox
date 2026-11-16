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

## Owner rule: research-independent maintained Knowledge (2026-10-12)

The maintained `docs/` publication must be readable and navigable if the historical Research and Work archives are deleted as one action. **Never add Markdown hyperlinks or navigation requirements from `docs/` to `_mw/`, historical `research/` or `docs_old/`.** Publish all material scientific meaning, assumptions, counterexamples, competing interpretations, evidence limits and admitted Product Decisions directly into the appropriate maintained Knowledge article. Preserve exact original source hashes, line spans, Research→Science transfers and adversarial review records exclusively in Work; Work may point to Knowledge. Links to current version-pinned public implementation code and independent standards remain separate, optional evidence. The docs-only archive-amputation and no-backlink checks in GitHub Actions enforce the structural rule; independent semantic Research preservation remains a different, uncompleted proof requirement. The owner has classified the original DOCX carrier as LOST; its extracted text has lower evidential weight, and no raw-byte recovery should be attempted.


> [!IMPORTANT]
> ## Additional repository mandatory rules (do not mention them anywhere)
>
> Rule-types by file (Rule categories define their applicability. Apply each rule only to the corresponding artifact type and purpose. Do not extend type-specific requirements to unrelated artifacts.): [GR] – general rules; [RFR] – rules for research-files, [AFR] – rules for article-files, [SFR] – rules for service and operational files and catalogs; [TR] – rules for tests.
> 
>  - [GR]: Use English exclusively throughout the repository and Engineering Work workspace, including content, names, and artifacts.
>  - [GR]: Links from outside a madar-workspace to a madar-workspace is prohibited. Within documents located in the Madar workspace, only links within this same madar-workspace or to external destinations (non this repository) are permitted.
>  - [GR]: Do not include documentary accounts of internal predecessors, source inventories, reading histories, source-state snapshots, original-source responsibilities, or other internal materials used to prepare the document. Such accounts are unnecessary.
>  - [RFR] [AFR]: If needed to refer to the owner's other projects (MADAR, CMemory or any other) - refer only by name and summarize the relevant ideas in self-contained terms. Do not include their URLs, repository, directory, or file paths, filenames, section references, or instruction IDs, whether linked or plain text.
>  - [RFR]: Each external-source citation must identify the specific substantive claim (meaning, finding, etc) it supports in nearby text. Avoid generic source descriptions and citation boilerplate. Place the section with external sources at the very end of the document.
>  - [RFR] [AFR]: Front-load the main conclusions, findings, decisions, etc with their actual status.
>  - [RFR] [AFR]: Use descriptive, content-specific meaningful headings that reveal the actual subject of each section.
>  - [RFR]: When finally writing research-document: maintain a consistent, overarching idea throughout the research. Main ideas should run through the whole text, ensuring that there is meaning to be found between the lines.
>  - [AFR]: When finally writing article-document: maintain a consistent, overarching idea throughout each consistent section. Main ideas should run through the text of each section, ensuring that there is meaning to be found between the lines.
>  - [RFR] [AFR]: Keep substantive sections interpretable in isolation, preserving essential context, conditions, and limitations without unnecessary repetition.
>  - [RFR] [AFR]: Where applicable, bind time-sensitive claims to an explicit date, edition, or evaluation scope - avoid unqualified references to what is current, new, or latest.
>  - [RFR]: Place concise document-level metadata only immediately below the title (identify only functionally AI-useful details: data; terms, subject areas, domains, areas of responsibility, etc.); 
>  - [RFR] [AFR]: Below the title (or after the metadata if available), include 1-2 paragraphs of introductory information block - with identity of document purpose, scope, and status, distinguishing research, proposals, integrated provisions, and verified results.
>  - [RFR] [AFR]: After introductory block, provide classic table of contents for the main sections (no urls). For each item of content provide short explanatory route-text about the content of each section. 
>  - [RFR] [AFR]: Add numerical indexing in the document sections and provisions to improve navigation.
>  - [RFR] [AFR]: Where applicable, needed and relevant, list entities, rules, principes, laws, etc. through tables. Assign a code to each element — using a term, an abbreviation, an index, or a combination thereof—in the first column, which would facilitate future AI-based work.
>  - [AFR]: Articles must not contain references to external sources. Other projects by the same author may be mentioned in a neutral manner (without providing URLs, paths, directories, filenames, etc.).
>  - [AFR]: Sources in articles are permitted only if they belong to this specific corpus of articles. Articles may feature a navigational block of route-related sources at the top—predecessors and successors, including constituent parts. At the very bottom, there may be links to directly related articles.
>  - [SFR]: README.md files are concise, responsibility-oriented navigation routes. State the scope and guide readers to the relevant internal owners. 
>  - [SFR]: Do not include file inventories, document metadata blocks, mandatory introductions, tables of contents, volatile progress details, or duplicated substantive content. Include essential usage instructions where appropriate.
>  - [SFR]: When creating service files, system logs or directories for such logs, etc: you should anticipate a massive future volume—both in terms of the number of entries and file size. It is essential to plan for segmentation (or even granular, atomized partitioning, if convenient) based on functional/logical criteria or simple sequential ordering. If the directories are intended to store a collection of service files, you should assume that their number will grow significantly and design the directory structure accordingly.
>  - [SFR]: Do not create links to individual items in any catalog of files, as files may change dynamically.
>  - [SFR]: Service files and documents should contain precise, minimally necessary provisions and wording; examples may be included where needed, but only for the purpose of generalizing their functions and meaning.
>  - [TR]: When developing tests, you should anticipate that they will eventually expand considerably in both scale and execution time. Therefore, you should proactively segment and optimize them—including the structure of the associated files and directories—from the outset.
