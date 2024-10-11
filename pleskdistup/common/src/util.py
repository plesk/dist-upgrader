# Copyright 2023-2024. WebPros International GmbH. All rights reserved.

import subprocess
from select import select
import typing

from . import log


def log_outputs_check_call(
    cmd: typing.Union[typing.Sequence[str], str],
    collect_return_stdout: bool = False,
    **kwargs,
) -> str:
    '''
    Runs cmd and raises on nonzero exit code. Returns stdout when collect_return_stdout
    '''
    log.info(f"Running: {cmd!r}. Output:")
    stdout = []

    def proc_stdout(line: str) -> None:
        log.info("stdout: {}".format(line.rstrip('\n')), to_stream=False)
        if collect_return_stdout:
            stdout.append(line)

    def proc_stderr(line: str) -> None:
        log.info("stderr: {}".format(line.rstrip('\n')))

    exit_code = exec_get_output_streamed(cmd, proc_stdout, proc_stderr, **kwargs)
    if exit_code != 0:
        log.err(f"Command {cmd!r} failed with return code {exit_code}")
        raise subprocess.CalledProcessError(returncode=exit_code, cmd=cmd)

    log.info(f"Command {cmd!r} finished successfully")
    return "".join(stdout)


# Returns standard output
def logged_check_call(cmd: typing.Union[typing.Sequence[str], str], **kwargs) -> str:
    return log_outputs_check_call(cmd, collect_return_stdout=True, **kwargs)


def exec_get_output_streamed(
    cmd: typing.Union[typing.Sequence[str], str],
    process_stdout_line: typing.Optional[typing.Callable[[str], None]],
    process_stderr_line: typing.Optional[typing.Callable[[str], None]],
    **kwargs,
) -> int:
    '''
    Allows to get stdout/stderr by streaming line by line, by calling callbacks
    and returns process exit code
    '''
    kwargs["stdout"] = (subprocess.DEVNULL if process_stdout_line is None
                        else subprocess.PIPE)
    kwargs["stderr"] = (subprocess.DEVNULL if process_stderr_line is None
                        else subprocess.PIPE)
    kwargs["universal_newlines"] = True

    process = subprocess.Popen(cmd, **kwargs)
    if process_stdout_line is None and process_stderr_line is None:
        process.communicate()
        return process.returncode

    while process.poll() is None:
        if process_stdout_line is not None:
            if not process.stdout:
                raise RuntimeError(f"Cannot get process stdout of command {cmd!r}")
            if select([process.stdout], [], [], 0.0)[0]:
                line = process.stdout.readline()
                if line:
                    process_stdout_line(line)
        if process_stderr_line is not None:
            if not process.stderr:
                raise RuntimeError(f"Cannot get process stderr of command {cmd!r}")
            if select([process.stderr], [], [], 0.0)[0]:
                line = process.stderr.readline()
                if line:
                    process_stderr_line(line)
    return process.returncode


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
