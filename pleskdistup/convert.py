# Copyright 2023-2024. WebPros International GmbH. All rights reserved.

import os
import threading
import typing

from pleskdistup.common import action, writers
from pleskdistup.phase import Phase


PathType = typing.Union[os.PathLike, str]


def get_flow(
    phase: Phase,
    resume_stage: str,
    actions_map: typing.Dict[str, typing.List[action.ActiveAction]],
    state_dir: PathType,
    flow_tracker: action.FlowTracker,
) -> action.ActiveFlow:
    state_dir = str(state_dir)
    if phase is Phase.FINISH:
        return action.FinishActionsFlow(actions_map, state_dir, flow_tracker, resume_stage)
    elif phase is Phase.REVERT:
        return action.RevertActionsFlow(actions_map, state_dir, flow_tracker, resume_stage)
    else:
        return action.PrepareActionsFlow(actions_map, state_dir, flow_tracker, resume_stage)


def start_flow(
    flow: action.ActiveFlow,
    status_file_path: PathType,
    time_exceeded_msg: str,
) -> None:
    with writers.FileWriter(status_file_path) as status_writer, writers.StdoutWriter() as stdout_writer:
        progressbar = action.FlowProgressbar(flow, [stdout_writer, status_writer], time_exceeded_msg)
        progress = threading.Thread(target=progressbar.display)
        executor = threading.Thread(target=flow.pass_actions)

        progress.start()
        executor.start()

        executor.join()
        progress.join()


# Unfortunately, dataclasses available since Python 3.7 aren't supported
# on Ubuntu 18 (Python 3.6)
class ConvertResult:
    success: bool
    reboot_requested: bool

    def __init__(
        self,
        success: bool = True,
        reboot_requested: bool = False,
    ):
        self.success = success
        self.reboot_requested = reboot_requested

    def __repr__(self) -> str:
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{self.__class__.__name__}({attrs})"


def convert(
    phase: Phase,
    resume_stage: str,
    actions_map: typing.Dict[str, typing.List[action.ActiveAction]],
    state_dir: PathType,
    status_file_path: PathType,
    time_exceeded_msg: str,
    flow_tracker: action.FlowTracker,
) -> ConvertResult:
    with get_flow(phase, resume_stage, actions_map, state_dir, flow_tracker) as flow:
        flow.validate_actions()
        start_flow(flow, status_file_path, time_exceeded_msg)
        if flow.is_failed():
            raise RuntimeError(flow.get_error())
        return ConvertResult(success=True, reboot_requested=(flow.reboot_requested is not None))
