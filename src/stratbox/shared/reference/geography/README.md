# Territorial labels and reviewed identity rules

`normalize_region_label()` creates a stable Unicode comparison key while preserving qualifiers and distinctions. `RegionNameResolver` then checks exact reviewed name rules with optional source family, date, subject kind, explicitly namespaced source code and statistical perimeter context.

```python
from stratbox.shared.reference.geography import RegionNameResolver

match = RegionNameResolver().resolve("город Москва")
assert match.subject.id == "RU-MOW"
```

Status may be `exact`, `alias`, `unmatched`, `ambiguous` or `out_of_scope`. The starter reference is deliberately incomplete; it contains no inferred equivalence between a region and an inclusive/exclusive statistical aggregate. Source-specific geographic row numbers remain the property of their respective domain parsers.

[Full interpretation contract](../../../../../docs/current-how/geography-name-resolution.md)


A packaged result carries a verified reference snapshot and a content
fingerprint of the full rule set. Programmatically supplied rules carry
their own fingerprint and provenance kind; they cannot use the ID of a
packaged reference. Source/perimeter/date-restricted rules fail closed when
the corresponding context is absent. One validation routine applies to
both CSV and supplied rules, and indexed matching remains independent of
pandas.
