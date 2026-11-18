# Bank references

`registry.py` reads an explicitly selected packaged edition and creates the bank profile. It requires a Bank of Russia workbook plus distinct alias, default-selection and legacy-selection resources.

`names.py` performs pure lexical bank-name normalization; its `normalize_bank_name(..., aliases=...)` variant applies a caller-supplied name policy. `registry.normalize_registered_bank(...)` loads the packaged alias policy explicitly.

```python
from stratbox.shared.reference.banks import registry
from stratbox.shared.reference.banks.names import normalize_bank_spelling

name = normalize_bank_spelling("ПАО Сбербанк")
profile = registry.read()  # Requires dataframe/excel extras.
```

Update the manifest whenever a resource edition changes. See the [reference update procedure](../../../../../docs/current-how/reference-snapshots-and-update.md).
