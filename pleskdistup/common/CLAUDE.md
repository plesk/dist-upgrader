# CLAUDE.md — `pleskdistup/common/`

This directory is the shared helper library for the pleskdistup framework — package managers, systemd, leapp configs, plesk, files, dns, logging, etc. It is where the bulk of the test coverage lives.

## Test coverage expectations

New utilities added under `src/` are expected to ship with tests in `tests/`. When adding or modifying a helper, add or extend the matching test module (`src/files.py` → `tests/filestests.py`, `src/rpm.py` → `tests/rpmtests.py`, ...). Mock external dependencies (filesystem, subprocess) rather than touching the real system.

**Test file naming**: test modules must end with `tests.py` (plural). This is what the unittest discovery pattern `*tests.py` picks up — a file named `footest.py`, `test_foo.py`, or `foo_tests.py` will be silently skipped and the coverage lost. Follow the `<subject>tests.py` convention (`filestests.py`, `rpmtests.py`, `leapp_configs_tests.py`, ...). The `test_main.py` Buck entrypoint is the one intentional exception — it is excluded by the pattern.

**Exception**: helpers that shell out to Plesk-provided utilities (`plesk`, `plesk db`, `plesk bin ...`, etc.) are not expected to have unit tests — those binaries are not available in the test environment. This applies to code in `src/plesk.py` and similar Plesk-facing wrappers.

Run the suite with the `pleskdistup-test` skill.
