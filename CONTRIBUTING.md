# Contributing to Cognarc Core

Thank you for taking the time to contribute. This document explains how the project is developed, how changes flow into a release, and the rules every change must respect.

## How changes land

Cognarc Core is maintained in a single internal source repository and **exported** into the public
`cognarc-core` repository at every release. The public repository therefore has one commit per
release and does not accept direct pushes. Pull requests are still welcome here:

1. Open an issue first for anything larger than a typo or a one-line fix, so we can agree on the
   approach before you invest time.
2. Fork the repository and open a pull request against `main`.
3. A maintainer reviews the pull request. Once accepted, the change is ported into the source
   repository, released in the next version, and credited to you in `CHANGELOG.md`.
4. The pull request is closed with a reference to the release that contains your change.

Translations of the Traditional Chinese documents under `docs/` into English are a particularly
welcome contribution.

## Development setup

Requirements: Python 3.12 or 3.13, [uv](https://docs.astral.sh/uv/), and for the integration
tests either local PostgreSQL 16 binaries (`initdb`, `pg_ctl`) or Docker.

```bash
git clone https://github.com/Cognarc-Inc/cognarc-core.git
cd cognarc-core
uv sync
uv run pre-commit install      # ruff check + format run on every commit
make lint                      # ruff check, ruff format --check, pyright (strict)
make test                      # unit tests, no database needed
make pg-up && make test-db     # integration tests against a throwaway PostgreSQL on 127.0.0.1:55434
make pg-down
```

`make pg-up` prints the `CORE_TEST_ADMIN_URL` it uses. Point that variable at any PostgreSQL 16+
instance where you can create roles and databases to run the integration tests elsewhere.

## Rules every change must respect

Read [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) before changing code: it explains where each
guarantee is enforced, which is what these rules protect. They are enforced by tests where possible. A change that breaks one of them will not be merged.

- **The schema has exactly one source: `src/cognarc_core/schema/sql/*.sql`.** Python reflects
  tables at runtime and never redefines them.
- **Released SQL files are never rewritten.** To change the schema, add a new file with the next
  number in the series (`0xx` for the open-source layer). `schema.apply()` records applied files
  by name and skips them on the next run. Comment-only edits (no DDL, no `{{...}}` placeholder,
  no `-- tier:` header change) do not count as a rewrite.
- **All timestamps are UTC and timezone-aware.** The four time columns stay separate:
  `event_time`, `published_at`, `available_at`, `ingested_at`.
- **Audit tables are append-only.** Corrections are new rows, never updates or deletes.
- **People are referenced by principal id, never by name.**
- **Tenant isolation is enforced in the database.** Every tenant table keeps
  `FORCE ROW LEVEL SECURITY`; do not add code paths that bypass `SET ROLE`.
- **No recommendation, scoring or auto-approval features.** Cognarc Core records decisions made
  by accountable actors; it does not make them.
- **No product-specific code.** The package must not import or encode any downstream product.
- **Document the design.** A new module or SQL file is described in `docs/ARCHITECTURE.md`;
  `tests/unit/test_architecture_doc.py` fails otherwise.

## Code style

- `ruff` for linting and formatting (configuration in `pyproject.toml`, line length 110).
- `pyright` in strict mode; new public functions need complete type annotations.
- Tests live in `tests/unit` (no database) and `tests/integration` (marked `db`). Add a test for
  every behaviour change; integration tests create their own keys with `uuid4()` and never truncate
  tables.
- Commit messages: one line summarising the change, in the imperative mood, followed by a blank
  line and the reasoning when it is not obvious.

## Reporting bugs and proposing features

Use the issue templates. For security problems, do **not** open a public issue; follow
[SECURITY.md](SECURITY.md).

## License

By contributing you agree that your contributions are licensed under the
[Apache License 2.0](LICENSE), the same license that covers the project.
