# Statistical workbook interpretation

A statistical series declares worksheet anchors, row and column meaning, period rules, metrics, units, scale and geographic perimeter. `command.workbook.decode` preserves physical evidence; domain `command.table.extract` and `command.table.interpret` apply the reviewed table rules. Recognition alone establishes no statistical meaning.

Source dates and periods are parsed independently of filenames and acquisition time. Wrong anchors, conflicting source claims, ambiguous worksheet selection and unsupported semantics fail explicitly. Zeros, blanks, withheld values and other publisher markers retain distinct statuses and literal evidence.

Validation checks actual observation coordinates. Alignment applies declared dictionaries and reference rules without erasing publisher coordinates. Change comparison preserves before/after source evidence and separates byte, physical-cell, semantic and lexical differences.

Portable dataset encoding records source uses, exact material identity and interpretation basis. Offline replay uses declared codecs and repeats semantic checks when entering a target. See [shared contracts](shared-semantic-contracts.md) and [standard routes](cbr-data-pipeline.md).
