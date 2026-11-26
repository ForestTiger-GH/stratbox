# Stratbox

Stratbox provides standard, composable actions for statistical publications and
numerical data. The same command contracts serve notebooks, applications and
machine clients. Domain records supply the methods and exact rules for each
continuing table series.

The package has five owners:

- `capabilities`: standard commands, operations, scenarios, cascades, preparation
  and plans.
- `core`: direct execution, bounded resources, technical providers, effects,
  journals and notification delivery.
- `domains`: explicit immutable publisher catalogs and narrow scientific methods.
- `shared`: values, identity, dates, qualifications and reference contents.
- `sdk`: one public discovery and invocation facade.

```python
from stratbox.sdk import StrategyBox

with StrategyBox() as box:
    commands = box.discover(kind="command", limit=20)
    escrow = box.sources.source("cbr.project_finance.escrow")
```

- [Standard definitions and execution ownership](docs/architecture/capability-execution.md)
- [Direct calls, prepared plans and result lifetime](docs/current-how/capability-session.md)
- [Independent typed processing stages](docs/current-how/standard-data-stages.md)
- [Static domain catalogs and scientific coverage](docs/current-how/independent-domain-data-routes.md)
- [Installation and local verification](docs/how/install-and-run-core.md)
- [Maintained analytical knowledge](docs/README.md)

```sh
python -m pip install -e ".[test]" build
python scripts/check_release_integrity.py
python scripts/check_internal_imports.py
python scripts/check_readme_links.py
python scripts/reference_assets.py --reference all
python -m pytest -q
python scripts/local_release_check.py
```
