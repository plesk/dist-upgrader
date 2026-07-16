#!/usr/bin/env bash
# PostToolUse hook: run flake8 on the Python file just edited.
# Stdin: Claude Code PostToolUse JSON envelope.
# Exit 2 with stderr → surfaces lint errors back to Claude.
#
# mypy is intentionally NOT in the hook — single-file mypy produces spurious
# "import-not-found" errors because cross-package imports aren't resolvable
# without the right MYPYPATH / --package context. Run full mypy via the
# pleskdistup-lint skill instead.

set -uo pipefail

input="$(cat)"

command -v jq >/dev/null 2>&1 || exit 0
command -v flake8 >/dev/null 2>&1 || exit 0

file_path="$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')"

[[ -n "$file_path" && "$file_path" == *.py && -f "$file_path" ]] || exit 0

# Buck build-definition files are parsed by Buck (python2), not real runtime code.
case "$(basename "$file_path")" in
    *.defs.py) exit 0 ;;
esac

if ! out=$(flake8 --extend-ignore=E501 \
    --per-file-ignores='pleskdistup/__init__.py:F401,F403 pleskdistup/*/__init__.py:F401,F403' \
    "$file_path" 2>&1); then
    printf 'flake8 found issues in %s:\n%s\n' "$file_path" "$out" >&2
    exit 2
fi
