# Copyright 1999-2023. Plesk International GmbH. All rights reserved.

import subprocess
import typing

from . import log


# Returns standard output
def logged_check_call(cmd: typing.Union[typing.Sequence[str], str], **kwargs) -> str:
    log.info(f"Running: {cmd!r}. Output:")

    # I beleive we should be able pass argument to the subprocess function
    # from the caller. So we have to inject stdout/stderr/universal_newlines
    kwargs["stdout"] = subprocess.PIPE
    kwargs["stderr"] = subprocess.STDOUT
    kwargs["universal_newlines"] = True

    stdout = []
    process = subprocess.Popen(cmd, **kwargs)
    while None is process.poll():
        if not process.stdout:
            log.err(f"Can't get process output from {cmd!r}")
            raise RuntimeError(f"Can't get process output from {cmd!r}")
        line = process.stdout.readline()
        if line:
            stdout.append(line)
            if line.strip():
                log.info(line.strip(), to_stream=False)

    if process.returncode != 0:
        log.err(f"Command {cmd!r} failed with return code {process.returncode}")
        raise subprocess.CalledProcessError(returncode=process.returncode, cmd=cmd, output="\n".join(stdout))

    log.info(f"Command {cmd!r} finished successfully")
    return "\n".join(stdout)


def merge_dicts_of_lists(
    dict1: typing.Dict[typing.Any, typing.Any],
    dict2: typing.Dict[typing.Any, typing.Any],
) -> typing.Dict[typing.Any, typing.Any]:
    for key, value in dict2.items():
        if key in dict1:
            for item in value:
                dict1[key].append(item)
        else:
            dict1[key] = value
    return dict1
