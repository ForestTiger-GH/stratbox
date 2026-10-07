# Strategy Box engineering workspace

`_mw/` — центральное инженерное рабочее пространство проекта Strategy Box, физически размещённое в репозитории `stratbox`.

Здесь живут Research, исходные материалы, provenance и будущие Work-артефакты, которым нужен отдельный от продуктовой реализации жизненный цикл. Workspace может охватывать несколько репозиториев Strategy Box, при этом код, документация и текущая продуктовая семантика каждого компонента остаются у его собственного owner.

AppDock является отдельным внешним проектом. В `_mw/` может исследоваться только интеграционная граница Strategy Box с AppDock, когда это нужно для работы Strategy Box.

Главная точка входа — `_mw/AGENTS.md`. Этот файл является паспортом рабочего пространства и содержит его текущую архитектуру и owner map.

## Текущая структура

```text
_mw/
├── AGENTS.md
├── README.md
└── epochs-001-strategy-box-development/
    └── research/
        ├── 01-old-notes/
        │   └── README.md
        ├── 02-base-study/
        │   ├── README.md
        │   └── ... Research Results
        └── 03-consolidation-research/
            └── README.md
```

`epochs-001-strategy-box-development` — единственная активная эпоха.

- `01-old-notes` сохраняет исторические заметки и прежние материалы как provenance.
- `02-base-study` собирает свежую базовую картину текущего Strategy Box по фактическим implementation owners и тематические Research Results.
- `03-consolidation-research` сводит накопленный Research corpus перед отдельным Knowledge assembly: согласует темы, термины, противоречия, provenance, устойчивые выводы и пробелы, оставаясь Research-контуром.

Отдельные дублирующие Research-каталоги по каждому репозиторию Strategy Box по умолчанию не создаются. Новая поверхность появляется только при реальной отдельной ответственности, потребителе или жизненном цикле.
