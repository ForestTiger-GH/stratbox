# Архитектура CBR SORS Restoration

```text
cbr_sors_restoration/
├── sources/       парсинг и canonical source bundle
├── registries/    география, ОКВЭД2, публикационные категории
├── strict/        официальный quantity graph, closure, feasibility, min/max
├── crosswalk/     условный flow graph старой классификации → ОКВЭД2
├── linear/        нейтральные LP-контракты и официальный highspy adapter
├── contracts.py   публичные конфигурации
├── results.py     доказательные result-контракты
├── pivots.py      табличные представления
└── export.py      XLSX-экспорт
```

## Направление зависимостей

```text
sources → strict
sources + strict bounds → crosswalk
strict не зависит от crosswalk
```

## Crosswalk-компиляция

Для одного сценария:

```text
packaged atom/class edge registry
→ explicit allowed flow columns
→ legacy publication rows
→ national OKVED2 rows
→ FD section rows
→ strict component bound rows
→ deterministic bound closure
→ feasibility
→ target min/max
```

Основной crosswalk problem не содержит ненулевой objective. Любая оптимизация профиля относится к будущему отдельному benchmark-слою и не участвует в принятии восстановленных значений.

## Размерность

Число переменных равно:

```text
atomic_regions × allowed_atom_class_edges × 4 components
```

Это меньше полного декартова произведения атомов и классов и сохраняет точное происхождение каждого допустимого потока.
