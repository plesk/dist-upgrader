# Copyright 2023-2024. WebPros International GmbH. All rights reserved.
# vim:ft=python:

with allow_unsafe_import():
    import subprocess

def get_git_revision():
    return subprocess.check_call(['git', 'rev-parse', 'HEAD'])
