---
name: pleskdistup-test
description: Run unit tests for the dist-upgrader framework. Use whenever the user asks to run, execute, or check tests, or wants to verify a single test case after a change. Examples - "run the tests", "run the unittest suite", "test this change", "rerun test_files", "do the tests still pass".
---

# pleskdistup-test

Test runners for the pleskdistup common library. Tests live in `dist-upgrader/pleskdistup/common/tests/` and use Python's `unittest` with mocked filesystem and command execution.

**All `unittest` invocations must be run from `dist-upgrader/pleskdistup/common/`** — tests do `from src import ...`, and `src` is only importable when that directory is on `sys.path`. Running from any other cwd fails with `ModuleNotFoundError: No module named 'src'`.

## Full suite via unittest

```sh
cd dist-upgrader/pleskdistup/common
python3 -m unittest discover -s tests -p '*test*.py'
```

The non-default pattern `*test*.py` is required — most test files use the suffix form (`filestests.py`, `rpmtests.py`, `logtests.py`, ...) which the default `test*.py` pattern misses. The pattern also skips `test_main.py`, which is a Buck-only entrypoint (imports `__test_main__` injected by `python_test`) and cannot run under plain `unittest`.

## Single test module

```sh
cd dist-upgrader/pleskdistup/common
python3 -m unittest tests.filestests
```

Module names match the on-disk filenames (`filestests`, `rpmtests`, etc.) — there is no `test_files` module.

## Single test case or method

```sh
cd dist-upgrader/pleskdistup/common
python3 -m unittest tests.filestests.AppendStringsTests.test_append_strings
```
