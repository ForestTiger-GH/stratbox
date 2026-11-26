# Territorial naming rules

`normalize_region_label()` builds a comparison key. `RegionNameResolver` applies
reviewed rules with source, date, subject-kind, source-code and perimeter context.
A naming match preserves those qualifications; it does not establish an
unreviewed territorial or aggregation crosswalk.

[Rule loading](registry.py) verifies packaged inputs.
[Resolution](resolver.py) handles exact, alias, unmatched, ambiguous and
out-of-scope outcomes. Domain parsers retain their own source row identities.

See [the geography interpretation contract](../../../../../docs/current-how/geography-name-resolution.md).
