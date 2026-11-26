# Install and invoke Stratbox

Stratbox requires Python 3.10 or later. Install the package into the interpreter that runs the caller. In a notebook, use `%pip` in the target kernel. The base package imports domain and standard command metadata without optional numerical or workbook engines.

```sh
python -m pip install 'stratbox[http,dataframe,excel]'
```

Select extras for the actual work: `http` supplies Requests transport; `dataframe` supplies pandas/numpy; `excel`, `excel-legacy` and `excel-binary` supply workbook engines; `dbf`, `rar`, `pdf` and `documents` supply additional formats. `sors-restoration` supplies the coupled numerical solver dependencies. A provider satisfying a neutral interface can replace a built-in environment service.

```python
from pathlib import Path
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material

original = Material(Path('statistics.json').read_bytes(), 'application/json', 'fns.sme')
with StrategyBox() as box:
    result = box.invoke('scenario.series.refresh', target='fns.sme',
        inputs={'material': original, 'issue': '2026-11-10'})
    if result.outcome != 'succeeded':
        raise RuntimeError(result.diagnostics)
    dataset = result.output('dataset')
    print(dataset.source_id, len(dataset.rows), dataset.identity)
    result.close()
```

An explicitly supplied input selects the corresponding entrance. It does not require acquisition. The same scenario can observe and acquire a source when those steps are requested. Runtime settings, providers and destinations remain application configuration.

Use [source routes](../current-how/independent-domain-data-routes.md) for scientific scope, [SDK execution](../current-how/capability-session.md) for concurrency and result lifetime, and the [offline CLI example](../../examples/source_route.py) for arbitrary supplied source files.

From a checkout, install `-e '.[test]' build` and run `python scripts/local_release_check.py`. The command checks ownership and links, runs the complete local test suite, builds wheel/source archives and verifies isolated installed imports and exact packaged resources.
