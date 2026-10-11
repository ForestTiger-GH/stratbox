# Low-Level Design — выборочные рисковые механизмы

**Status:** selected candidate LDD only. Дизайн не является действующим кодом и наследует `TW-SB-2026-10-09-CANDIDATE-1` / `TH-SB-2026-10-09-CANDIDATE-1` / `PA-SB-2026-10-09-CANDIDATE-1`.

- [Staged → Verified → Published artifact](artifacts/staged-publication.md) — локальная спецификация состояния и отказов файловой публикации.
- [Neutral provider conformance vectors](extensions/neutral-provider-conformance-vectors.md) — 98 original-source-preserved, environment-neutral negative and contract test intents; candidate-only, not an implemented suite or certified provider.

Эта спецификация достаточно конкретна для обсуждения тестов, но не замещает Product Decisions о хранении, подтверждении и пользователях. Остальные рисковые темы (durable Job, ACL, external health contract) пока не получили достаточного фиксированного предметного baseline для независимого LDD.
