# OKVED2 classification

`registry.read()` parses the `data` asset as CP1251, semicolon-separated CSV without a header, preserving code and section order. `read_meta()` and `read_structure()` expose separately declared source materials. All assets are checked against their manifest records before parsing.

```python
from stratbox.shared.reference.okved2 import registry

codes = registry.read()  # Requires pandas.
```

The classifier material alone does not establish a domain-specific industry selection, aggregation or published economic perimeter.
