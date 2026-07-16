#!/usr/bin/env bash
# PostToolUse hook: run pleskdistup/common unittest discover when a file
# under dist-upgrader/pleskdistup/common/ has just been edited.
# Stdin: Claude Code PostToolUse JSON envelope.
# Exit 2 with stderr → surfaces test failures back to Claude.

set -uo pipefail

input="$(cat)"

command -v jq >/dev/null 2>&1 || exit 0
command -v python3 >/dev/null 2>&1 || exit 0

file_path="$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')"

[[ -n "$file_path" ]] || exit 0

# Only react to Python files inside pleskdistup/common/ — other files
# (Markdown, BUCK definitions, test fixtures, etc.) cannot affect test outcomes.
[[ "$file_path" == *.py ]] || exit 0
case "$file_path" in
    */dist-upgrader/pleskdistup/common/*) ;;
    *) exit 0 ;;
esac

common_dir="${file_path%%/dist-upgrader/pleskdistup/common/*}/dist-upgrader/pleskdistup/common"

[[ -d "$common_dir/tests" ]] || exit 0

if ! out=$(cd "$common_dir" && python3 -m unittest discover -s tests -p '*tests.py' 2>&1); then
    printf 'pleskdistup/common tests failed after editing %s:\n%s\n' "$file_path" "$out" >&2
    exit 2
fi
