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
- документация: `docs/` — новый единый публикационный корпус Strategy Box (пока только bootstrap), `docs_old/` — архив прежней документации; текущая проверяемая реализация core — `src/stratbox/` и `tests/`;
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

В `docs/` создаётся самостоятельная документационная система единого Strategy Box; `_mw/epochs-001-strategy-box-development/consolidation/` владеет рабочей процедурой, доказательствами сохранения значимого смысла, source census и checkpoint state. Прежние `docs/` перенесены в `docs_old/` без изменения исходных файлов. Пока `docs/` содержит только точки входа: принимать их за готовые научные или продуктовые спецификации запрещено.

Следующий полномасштабный непрерывный агентный цикл выполняется по применимым MADARAII Work-инструкциям, привязанным в `consolidation/METHOD-ROUTER.md`, и запускается отдельным прямым поручением. Агент сохраняет промежуточное состояние и проходит тематические проверки без искусственных пауз, но не принимает несанкционированные Product Decisions. Публичные результаты автономны: допускаются только общие упоминания методологии MADAR и абстрактных внешних ИИ-агентов; прямые адреса и специфика иных методологических или когнитивных проектов не публикуются. Исходные исторические исследования не редактировать ради стилистической зачистки. Закрытые реализации расширений и их внутренние сведения не переносить в открытый репозиторий.

## Language of future repository work (2026-10-11 owner instruction)

All **newly authored or materially revised** repository outcomes, documents, research, Science modules, evidence ledgers, checkpoints, release notes and commit messages must be written **in English**. Preserve existing historical source text and exact original references without retroactive translation unless separately commissioned. This is a documentation/communication convention, not a Product Decision or permission to rewrite protected material.

## Owner rule: research-independent maintained Knowledge (2026-10-12)

The maintained `docs/` publication must be readable and navigable if the historical Research and Work archives are deleted as one action. **Never add Markdown hyperlinks or navigation requirements from `docs/` to `_mw/`, historical `research/` or `docs_old/`.** Publish all material scientific meaning, assumptions, counterexamples, competing interpretations, evidence limits and admitted Product Decisions directly into the appropriate maintained Knowledge article. Preserve exact original source hashes, line spans, Research→Science transfers and adversarial review records exclusively in Work; Work may point to Knowledge. Links to current version-pinned public implementation code and independent standards remain separate, optional evidence. The docs-only archive-amputation and no-backlink checks in GitHub Actions enforce the structural rule; independent semantic Research preservation remains a different, uncompleted proof requirement. The owner has classified the original DOCX carrier as LOST; its extracted text has lower evidential weight, and no raw-byte recovery should be attempted.
