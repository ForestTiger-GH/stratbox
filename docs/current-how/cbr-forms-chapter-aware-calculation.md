# CBR forms: chapter-aware balance-sheet models

The Bank of Russia reporting form 0409101 DBF has these significant fields:
`REGN` identifies a bank, `PLAN` identifies the account-plan chapter,
`NUM_SC` is the account or aggregate code, `A_P` is the asset/liability side,
and `IITG` is the closing balance.

**A number is not a unique account identity without its chapter.**
For example, code 45.2 may appear in the balance-sheet chapter А and in
other chapters. Form 101's analytical model calculates balance-sheet
indicators from chapter А only; the other chapters must not create false
conflicts or inflate balances. The form adapter therefore requires `PLAN`
and the formula evaluator filters the declared chapter before keying
accounts by bank, code and side. Distinct values within the same
bank/chapter/code/side still fail rather than being silently combined.

The original publication layout is described by the Bank of Russia:
https://www.cbr.ru/Content/Document/File/158506/101-20240101.pdf

Current typed pipeline:
`select_sources` → `acquire` → `parse_form` → `build_form_data` →
`build_form_views` → `render_workbook`.

Successful source acquisition includes the official RAR media type
`application/rar` and validates the archive signature. Missing publication
dates (`http.status_404`) are separate from missing financial observations
and must be reported in the consumer's manifest, not interpreted as zero.

Verification performed on actual January 2024 and July 2026 CBR RAR
publications for all six supported forms (101, 102, 123, 135, 802, 805),
through parsing, semantic calculation and XLSX rendering in Python 3.12
and Python 3.13. The checks cover those release dates; later changes to
the CBR physical format require revalidation.