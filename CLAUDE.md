# CLAUDE.md

## What this repository is

This is the **`pleskdistup` framework** — the shared engine behind Plesk's tools for upgrading a distribution to a newer version (Ubuntu 20 -> 22) or converting between distributions (e.g. CentOS → AlmaLinux).

**It is framework code only and cannot run on its own.** A usable tool requires an *upgrader module* (a concrete `DistUpgrader`/`DistUpgraderFactory` implementation) that registers itself and supplies the actual list of actions for a specific OS upgrade. Those modules live in the per-OS repositories, which vendor this framework in. When working here, you are changing behavior shared across all of them.

## Stack

Python 3 (3.6+ compat) · Buck2 → PEX · stdlib `unittest` · `flake8` + `mypy` · drives [leapp](https://leapp.readthedocs.io/) for RHEL-family and native `apt` for Debian-family · shared helpers in `pleskdistup/common/` (submodule of `plesk/distro-conversion-base`).
**No third-party runtime deps** — stdlib only; do not add PyPI packages or external libs.

## Architecture

The framework executes an OS conversion as a sequence of **phases → stages → actions**, with persistent
state so the process survives the multiple reboots a dist-upgrade requires.
Every conversion run begins by executing all registered `CheckAction`s — if any fails, the tool aborts before touching the system. `--precheck` is just the same phase run standalone. This is the way to prevent conversion for not ready host.

### Phases of a conversion
- **CONVERT** — preparation + the actual package dist-upgrade.
- **FINISH** — finalizing actions, run after reboot, fixing temporary changes required for the conversion.
- **REVERT** — undo CONVERT-phase changes (`--revert`). Available only before the first reboot.

FINISH and REVERT run actions in **reverse** stage/action order (`ReverseActionFlow`).

### Key places in the repository

- `pleskdistup/common/src/action.py` — the core abstraction: `ActiveAction` to perform actions, `CheckAction` to pre-check if conversion should be aborted, and **Flows** (`PrepareActionsFlow`, `FinishActionsFlow`, `RevertActionsFlow`, `CheckFlow`) that run the right actions in the right order for a phase and persist state so the process is resumable across reboots.
- `pleskdistup/main.py`, `pleskdistup/convert.py` — entry point. Parses args, detects the OS (`dist.get_distro()`), starts the flow. `ResumeTracker` is the class used to pick the flow back up after a reboot or a `--resume`.
- `pleskdistup/upgrader.py`, `pleskdistup/registry.py` — `DistUpgrader`/`DistUpgraderFactory`: what an external module subclasses to declare an upgrader for a specific conversion / dist-upgrade case (e.g. CentOS 7 → AlmaLinux 8).
- `pleskdistup/common/` — grab-bag of OS-interaction helpers for building actions (package managers, systemd, leapp configs, plesk, mariadb/postgres/php, files, dns, logging, etc.).
- `pleskdistup/common/tests/` — most test coverage targets the common helpers.
- `pleskdistup/actions/` — reusable action/check implementations built on top of the common library that upgrader modules compose into their plans.

## Conventions

- **Python 3.6 compatibility is required** (target systems include Ubuntu 18).
- Star imports (`from .x import *`) are used intentionally in `__init__.py` files to flatten the public API;
  flake8 F401/F403 are ignored there only.
- If you need something to survive a reboot, put it in the state dir (`--state-dir`) — not in `/tmp` or any other volatile location.

## Build gotchas

- `.buckconfig` invokes the Buck *parser* with `python2`, but runtime code targets Python 3 and must stay compatible back to **Python 3.6**. `*.defs.py` files are Buck build-definition helpers, not runtime code, and are excluded from linting.