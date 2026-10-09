# Current HOW — observed Strategy Box mechanisms

**Status:** three bounded static implementation slices available. Full Current HOW reconstruction, deployed-state verification and independent assurance remain open.

- [Analytical core runtime and network transport](core-runtime-network.md) — provider composition and typed HTTP download outcomes.
- [Windows application lifecycle, scenarios and local history](windows-application.md) — activation, case execution, JSON history and background status scaffold.
- [FRG cleanup plan and destructive effect handling](frg-cleanup-effects.md) — plan/apply separation, per-row results and explicit failure/partial-effect limits.

**Exact direct-source baselines:** `stratbox@8459dc58922b7e8df853cf1d9e8131fa9e132580` and `stratbox-windows@959e9c4ce1441124af5111c1e025041714e04d3b`. The external managed platform is a separate contract owner and its potential future features are not evidence of present runtime behavior.

These modules have local static evidence, but no GUI, tests, filesystem mutation, fault injection or installed application was executed. They do not prove currentness of all other domains, complete coverage of the 553 registered file sources, or end-to-end reliability.

Uncovered mechanisms remain owned by their direct implementation and test source files. The scientific and target documents do not override their observed control flows.
