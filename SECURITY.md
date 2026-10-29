# Security Policy

Cognarc Core exists to make decision records trustworthy. A vulnerability in it is a vulnerability
in every system that relies on those records, so we treat reports seriously and respond quickly.

## Supported versions

| Version | Supported |
| ------- | --------- |
| 0.1.x   | Yes       |

Security fixes ship as the next patch release of the latest minor version.

## Reporting a vulnerability

Please **do not** open a public issue for security problems.

Report privately through GitHub's private vulnerability reporting:
<https://github.com/Cognarc-Inc/cognarc-core/security/advisories/new>

Include what you can of the following:

- a description of the issue and the component affected (SQL file, module, function);
- a minimal reproduction, ideally as a failing test;
- the impact you believe it has (for example, cross-tenant read, audit row modification);
- the version or commit you tested against.

We aim to acknowledge reports within five business days, to keep you informed while we work on a
fix, and to credit you in the release notes unless you prefer otherwise.

## What counts as a security issue

Any way to break one of the guarantees the project documents, including:

- reading or writing another tenant's rows despite row-level security;
- updating, deleting or truncating rows in an append-only table (`core.audit_log`,
  `core.decision_record`, and in the enterprise distribution the audit chain and seals);
- bypassing the `SET ROLE` requirement or injecting into role names;
- creating duplicate records through `insert_idempotent` for the same unique key;
- producing a timestamp that is not UTC or that collapses the four separate time columns;
- any issue in the packaging or build pipeline that could ship altered code.

## Scope

This policy covers the code in this repository. Issues in PostgreSQL, SQLAlchemy or psycopg should
be reported to those projects; we are happy to coordinate when a fix on our side is needed.
