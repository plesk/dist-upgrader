---
name: pleskdistup-checkaction
description: Idioms for writing `CheckAction` subclasses in the pleskdistup framework. Use whenever a new `CheckAction` / `Assert*` is being added or an existing one edited, and whenever the user asks to "pre-check" or "check" something before the upgrade / dist-upgrade / conversion / precheck — those requests are always implemented as a `CheckAction`. Examples - "add a check that X is installed before conversion", "make sure the server has at least N GB free before we run", "block the upgrade when config Y is missing", "add a precheck for Z", "why is this AssertFoo description empty on failure".
---

# CheckAction idioms

A `CheckAction` is a single pre-conversion gate. Every registered check runs in `CheckFlow` before any real work starts (and standalone under `--precheck`). Any failing check aborts the run before the system is touched. The base class lives with the rest of the flow abstractions in `pleskdistup/common/src/action.py` — grep for `class CheckAction`.

## Contract

In `__init__`:
- `self.name` — short lowercase label shown while the check runs (e.g. `"checking if there are duplicate repositories"`).
- `self.description` — user-facing message printed **only on failure**. Explain what is wrong AND how to fix it.

Implement `_do_check(self) -> bool`:
- return `True` if the condition holds (pass), `False` if not (fail).
- exceptions propagate; `CheckFlow.make_checks` wraps them in `RuntimeError` with the check name and aborts.

Naming convention: **`Assert*`**, not `Check*` (`AssertMinPhpVersion`, `AssertNoRepositoryDuplicates`, ...). The framework does not enforce it, but every existing subclass follows it.

## The four idioms

### 1. Template + late fill (by far the most common)

`__init__` sets `self.description` to a template with `{}` placeholders; `_do_check` fills it with the actual offending items right before returning `False`. Filling **only on failure** keeps the message empty for passing runs and specific for failing ones.

Sketch:

```python
def __init__(self):
    self.name = "checking if there are duplicate repositories"
    self.description = """There are duplicate repositories present:
\t- {}

\tPlease remove duplicates to proceed the conversion.
"""

def _do_check(self) -> bool:
    duplicates = _find_duplicates()
    if not duplicates:
        return True
    self.description = self.description.format("\n\t- ".join(duplicates))
    return False
```

**Render several values as a bullet list, not an inline comma-join.** Whenever the description
enumerates more than one item (offending repos, files, domains, packages, …), format them one per
line as a `\t- ` bullet list — `"\n\t- ".join(items)` filling a template that starts the list with
`\t- {}`. It reads far better in the terminal than `", ".join(...)`, and it applies both to the
late-fill case above and to values known at construction time (e.g. a list of repo-file paths
passed into `__init__`). Reserve inline comma-joins for a single short value.

Existing examples to grep for: `AssertNoRepositoryDuplicates`, `AssertIPRepositoryNotPresent`, `AssertNoAbsoluteLinksInRoot`, `AssertMinFreeDiskSpace`.

### 2. Multi-section description assembled conditionally

For failures with several independent remediation steps, keep each fragment as its own template attribute and stitch them together in `_do_check` depending on what actually broke. Numbering (`1.` / `2.`) is added inline only when more than one step applies.

Existing example: `AssertMinPhpVersion` — three templates (`self.description`, `self.fix_domains_step`, `self.remove_php_step`) combined at the end of `_do_check`.

### 3. Parametrized helper base class

When several checks differ only in a predicate or formatting function, make an abstract base that accepts callables in its constructor and let thin subclasses supply them.

Sketch:

```python
def __init__(self, name, description, formatter, condition):
    self.name, self.description = name, description
    self.formatter, self.condition = formatter, condition
```

Existing examples: `AssertInstalledPhpVersionsByCondition` and its concrete subclasses `AssertMinPhpVersionInstalled` / `AssertInstalledPhpVersionsInList`; the analogous `...ByWebsitesByCondition` / `...ByCronByCondition` bases. The minimal parametrized case is `AssertPackageIsNotInstalled` — takes a `package_name` and optionally overrides the default description.

### 4. Dynamic `name` via `@property`

If the label depends on constructor args, expose `name` as a `@property`.

Existing example: `AssertPleskExtensions` yields names like `"check Plesk extensions state: +plesk-core, -watchdog"`.

## What checks typically do

- **Repository / package state** — `rpm`, `dnf list installed`, repo-file inspection.
- **Plesk state** — `plesk.get_from_plesk_database(...)`, `plesk.list_installed_extensions(...)`. Always guard with `plesk.is_plesk_database_ready()` — the DB can be down.
- **Filesystem** — `os.walk`, disk-space, symlink audits.
- **System state** — running kernel, NIC names, RAM.
- **Subprocess** — `yum check-update`, `curl` for repo probing, `fuser` for lock detection.
- **Distro / version** — the concrete converter (e.g. centos2alma) checks its expected source distro before doing anything.

Log with `log.debug(...)` liberally in `_do_check` — what you inspected and what you found. `log.warn` / `log.info` only for exceptional non-blocking situations (Plesk DB unavailable, optional check skipped).

## Gotchas

- **Empty description on failure.** If `_do_check` returns `False` but you forgot to `.format(...)` the placeholders, the UI prints an unfilled template (`{}`) or nothing useful. Every `return False` path must leave `self.description` populated with the concrete offenders. This is the single most common bug in new checks.
- **Do not do work in `__init__`.** Constructors run at registration time for every check, even ones that end up skipped. Filesystem walks, RPM queries, subprocess calls, Plesk DB calls belong in `_do_check`. `__init__` should only stash arguments and prepare templates.
- **f-string for `self.description` in `__init__`.** Locks the value at construction time. Use `.format()` templates so `_do_check` can fill them lazily with real state.
- **Bare `except Exception`.** Prefer letting `_do_check` raise on genuinely unexpected failures — `CheckFlow` wraps them with the check name for context. Only swallow errors when the check is legitimately optional, and then log why.
- **Python 3.6 compat.** Framework must run on Ubuntu 18. No walrus, no `match`, no `dict | dict` merge. Use `typing.List` / `typing.Dict`, not `list[...]` / `dict[...]`.

## Where new checks live

- **Framework-shared** (applies to more than one converter, e.g. any Plesk host): the reusable check modules under `pleskdistup/actions/` in the framework. Extend the closest existing module (`common_checks.py`, `packages.py`, `extensions.py`).
- **Converter-specific** (distro/kernel/leapp-only preconditions for a single upgrader): the converter repo's own `actions/common_checks.py` (e.g. `centos2almaconverter/actions/common_checks.py` for centos2alma).

Register the new check by adding it to the check list produced by the relevant `DistUpgrader` (framework side) or the concrete converter (e.g. `Centos2AlmaConverter`). If the check calls into a new common helper, ship tests for that helper alongside — the common library expects `<subject>tests.py`; see the common-library CLAUDE.md for the naming rule.
