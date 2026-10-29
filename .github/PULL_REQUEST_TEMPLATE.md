## Summary

<!-- What changes and why. Link the issue this closes. -->

Closes #

## Checklist

- [ ] `make lint` and `make test` pass locally
- [ ] `make test-db` passes, or the change does not touch SQL or database code
- [ ] New or changed behaviour has a test
- [ ] Schema changes are in a **new** SQL file; no released file was edited
- [ ] All timestamps are UTC and the four time columns stay separate
- [ ] No update or delete path was added to an append-only table
- [ ] People are referenced by principal id, never by name
- [ ] `CHANGELOG.md` has an entry under *Unreleased*
- [ ] Documentation updated where behaviour changed
