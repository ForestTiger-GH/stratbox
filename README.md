# Stratbox

Stratbox provides reusable Python operations for acquiring, interpreting and
presenting banking and economic data. Applications pass their own providers,
dates and destinations.

- [Core API and domain operations](docs/current-how/universal-business-core.md)
- [Execution, admission and recovery](docs/current-how/core-execution-and-admission.md)
- [Installation and offline quickstart](docs/how/install-and-run-core.md)
- [Execution and storage boundaries](docs/architecture/core-operation-boundaries.md)
- [Strategy Box Knowledge Product](docs/README.md)

```sh
python -m pip install .
python -m pip install -e ".[test]"
python -B scripts/check_release_integrity.py
python -B scripts/check_internal_imports.py
python -B -m pytest -q
```
