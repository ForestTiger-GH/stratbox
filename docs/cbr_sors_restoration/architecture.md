# Архитектура

```text
cbr_sors_restoration/
├── sources/       Excel adapters, source GRID, validation
├── registries/    geography, OKVED2, publication categories
├── strict/        quantities, relations, closure, compiler, planning, batches
├── linear/        official HiGHS adapter and elastic conflicts
├── bridge/        mapping resources and conditional model
├── results.py     stable result contracts
├── pivots.py      region/class Pivot API
├── export.py      XLSX export
└── operations.py  strict orchestration
```

Границы ответственности:

- `sources` знает расположение данных в книгах;
- `registries` задаёт канонические идентичности;
- `strict` знает доказательную математику;
- `linear` не знает предметных смыслов;
- `bridge` зависит от strict-result, strict от bridge не зависит;
- `pivots` и `export` работают только с готовыми GRID-контрактами.
