# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Until 1.0.0, minor versions
may contain breaking changes; they are called out explicitly below.

## [Unreleased]

### Added

- English README with quick start, guarantees, upgrade and removal paths.
- `examples/quickstart.py`: the README's four steps as a runnable script whose output is shown in
  the README.
- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md` and this changelog.
- GitHub Actions CI (lint, type check, unit tests on Python 3.12 and 3.13, integration tests
  against PostgreSQL 16), Dependabot configuration, issue and pull request templates.
- Project URLs, keywords and classifiers in `pyproject.toml`.
- Brand artwork under `docs/assets/` (trademarks of Cognarc Inc., not covered by the license),
  architecture diagrams in the README, a `pre-commit` configuration and a package build check in CI.
- README header with badges and navigation, a News section, a prompt for setting the project up
  with a coding agent, a Traditional Chinese translation (`README.zh-TW.md`) and `CITATION.cff`.
- `tests/unit/test_release_metadata.py`: the package version, `pyproject.toml`, `CITATION.cff` and
  this changelog must agree.
- `docs/ARCHITECTURE.md`: design principles, code map, data model, role model, write path,
  idempotency, schema lifecycle, trust boundaries, failure behaviour, a verified pattern for adding
  your own tables, and non-goals. `tests/unit/test_architecture_doc.py` fails if a module or SQL
  file is not described.

### Changed

- The contract, schema documentation, JSON Schema and docstrings no longer refer to Cognarc's own
  product lines; domain examples are labelled as examples. The package-boundary test now enforces
  a neutral rule (standard library plus declared dependencies only) instead of a list of product
  package names.
- The README's quick-start output now labels the admin connection correctly: it is a superuser that
  bypasses row-level security, not the owner role. The append-only guarantee now states that the
  owner role or a superuser can disable triggers first.

## [0.1.0] - 2026-10-29

Initial public release, extracted from Cognarc's internal codebase.

### Added

- Decision-record contract: `docs/CONTRACT.md` and the machine-readable
  `contracts/decision_record.schema.json`.
- `cognarc_core.clock`: timezone-aware UTC clock with an injectable `ManualClock` for tests.
- `cognarc_core.db.engine.make_engine`: SQLAlchemy engine that issues `SET ROLE` on every new
  connection, with role-name validation.
- `cognarc_core.db.idempotent.insert_idempotent`: unique-key idempotent inserts that return the
  existing row instead of creating a duplicate.
- `cognarc_core.db.reflect.reflect_table`: table reflection so the schema is defined once, in SQL.
- `cognarc_core.decisions.record_decision`: writes a `DecisionRecord`.
- `cognarc_core.schema.apply`: applies the versioned SQL files in order and records them in
  `core.schema_applied`.
- SQL schema `000`–`030`: bootstrap roles, tenants and tenant roles with
  `core.current_tenant_id()`, the ledger tables `core.policy`, `core.decision_record` and
  `core.outcome_observation` with forced row-level security, and the append-only `core.audit_log`
  whose triggers reject `UPDATE`, `DELETE` and `TRUNCATE` for every role.

[Unreleased]: https://github.com/Cognarc-Inc/cognarc-core/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Cognarc-Inc/cognarc-core/releases/tag/v0.1.0
