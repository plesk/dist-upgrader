# Copyright 2023-2024. WebPros International GmbH. All rights reserved.

import os
import json
import math
import time
import typing
import shutil
from abc import ABC, abstractmethod
from enum import Enum

from . import files, log, writers


class ActionState(str, Enum):
    SUCCESS = "success"
    SKIPPED = "skip"
    FAILED = "failed"


class RebootType(Enum):
    AFTER_CURRENT_STAGE = "after the current stage"
    AFTER_LAST_STAGE = "after the last stage"


# Unfortunately, dataclasses available since Python 3.7 aren't supported
# on Ubuntu 18 (Python 3.6)
class ActionResult:
    state: ActionState
    info: typing.Optional[str]
    reboot_requested: typing.Optional[RebootType]
    next_phase: typing.Any

    def __init__(
        self,
        state: ActionState = ActionState.SUCCESS,
        info: typing.Optional[str] = None,
        reboot_requested: typing.Optional[RebootType] = None,
        next_phase: typing.Any = None,
    ):
        self.state = state
        self.info = info
        self.reboot_requested = reboot_requested
        self.next_phase = next_phase

    def __repr__(self) -> str:
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{self.__class__.__name__}({attrs})"


class Action(ABC):
    """Base class for actions."""
    name: str
    description: str

    def __init__(self):
        self.name = ""
        self.description = ""

    def __repr__(self) -> str:
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{self.__class__.__name__}({attrs})"

    def __str__(self) -> str:
        return f"{self.name}"

    # For all estimates we assume all actions takes no more
    # than 1 second by default.
    # We trying to avoid estimate for small actions like
    # "change one line in string" or "remove one file"... etc
    def estimate_prepare_time(self) -> int:
        return 1

    def estimate_post_time(self) -> int:
        return 1

    def estimate_revert_time(self) -> int:
        return 1


class ActiveAction(Action):
    def invoke_prepare(self) -> ActionResult:
        return self._prepare_action()

    def invoke_post(self) -> ActionResult:
        return self._post_action()

    def invoke_revert(self) -> ActionResult:
        return self._revert_action()

    def is_required(self) -> bool:
        return self._is_required()

    def _is_required(self) -> bool:
        # All actions are required by default - just to simplify things
        return True

    @abstractmethod
    def _prepare_action(self) -> ActionResult:
        pass

    @abstractmethod
    def _post_action(self) -> ActionResult:
        pass

    @abstractmethod
    def _revert_action(self) -> ActionResult:
        pass


class ActionsFlow(ABC):
    def __enter__(self):
        return self

    def __exit__(self, *kwargs):
        pass


class FlowTracker(ABC):
    @abstractmethod
    def __call__(
        self,
        # We don't care about the type of phase here, as we don't
        # interpret it, just pass around
        phase: typing.Any = None,
        stage: typing.Optional[str] = None,
    ) -> None:
        pass


class ActiveFlow(ActionsFlow):
    state_dir: str
    _finished: bool
    stages: typing.Dict[str, typing.List[ActiveAction]]
    flow_tracker: typing.Optional[FlowTracker]
    resume_stage: typing.Optional[str]
    current_stage: str
    current_action: str
    total_time: int
    error: typing.Optional[typing.Union[Exception, str]]
    reboot_requested: typing.Optional[RebootType]

    # flow_tracker allows to track phase and stage switches to resume the process later.
    # resume_stage is the last successfully completed stage. The
    # process will be resumed from the stage following it
    def __init__(
        self,
        stages: typing.Dict[str, typing.List[ActiveAction]],
        state_dir: str,
        flow_tracker: typing.Optional[FlowTracker],
        resume_stage: typing.Optional[str] = None,
    ):
        super().__init__()
        self.state_dir = state_dir
        self._finished = False
        self.stages = stages
        self.flow_tracker = flow_tracker
        self.resume_stage = resume_stage
        self.current_stage = "initiliazing"
        self.current_action = "initiliazing"
        self.total_time = 0
        self.error = None
        self.reboot_requested = None

    @staticmethod
    def get_path_to_actions_data(state_dir: str) -> str:
        return os.path.join(state_dir, "actions.json")

    @property
    def path_to_actions_data(self) -> str:
        return self.get_path_to_actions_data(self.state_dir)

    def _track_flow(
        self,
        phase: typing.Any = None,
        stage: typing.Optional[str] = None,
    ) -> None:
        log.debug(f"_track_flow(phase={phase!r}, stage={stage!r})")
        if self.flow_tracker is not None:
            log.debug(f"flow_tracker(phase={phase!r}, stage={stage!r})")
            self.flow_tracker(phase=phase, stage=stage)

    def validate_actions(self):
        # Note. This one is for development purposes only
        for _, actions in self.stages.items():
            for action in actions:
                if not isinstance(action, ActiveAction):
                    raise TypeError(
                        "Not an ActiveAction passed into action flow. "
                        f"Name of the action is {action.name!r}"
                    )

    def pass_actions(self) -> bool:
        stages = self._get_flow()
        self._finished = False

        if self.resume_stage is not None:
            if self.resume_stage not in stages:
                raise ValueError(f"Resume stage {self.resume_stage!r} not in stages. Existing stages: {list(stages)}")
            else:
                log.debug(f"Resuming from the stage {self.resume_stage!r}")

        resume_stage = self.resume_stage
        for stage_id, actions in stages.items():
            if resume_stage is not None:
                if stage_id == resume_stage:
                    resume_stage = None
                log.debug(f"Skipping the stage {stage_id!r} due to resume mode")
                continue
            log.debug(f"Starting the stage {stage_id!r}")
            next_phase = None
            self._pre_stage(stage_id, actions)
            for action in actions:
                try:
                    if not self._is_action_required(stage_id, action):
                        log.info(f"Skipped: {action}")
                        self._save_action_state(stage_id, action.name, ActionState.SKIPPED)
                        continue

                    log.debug(f"Invoking action '{action}'")
                    action_start_time = int(time.time())
                    res = self._invoke_action(action)
                    action_duration = int(time.time()) - action_start_time
                    log.debug(f"Action '{action}' completed in {action_duration} s with result: {res}")
                    self._save_action_state(stage_id, action.name, res.state)

                    if res.state is ActionState.SUCCESS:
                        log.info(f"Success: {action}")
                    elif res.state is ActionState.SKIPPED:
                        msg = f"Skipped: {action}"
                        if res.info:
                            msg += f". Additional information: {res.info}"
                        log.info(msg)
                    elif res.state is ActionState.FAILED:
                        msg = f"Failed: {action}"
                        if res.info:
                            msg += f". Additional information: {res.info}"
                        self.error = msg
                        log.err(msg)
                        return False
                    if res.next_phase:
                        log.info(f"Action '{action}' requested process phase switch to {res.next_phase}")
                        next_phase = res.next_phase
                    if res.reboot_requested:
                        log.info(f"Action '{action}' requested reboot {res.reboot_requested}")
                        if (
                            self.reboot_requested is RebootType.AFTER_CURRENT_STAGE
                            and res.reboot_requested is RebootType.AFTER_LAST_STAGE
                        ):
                            log.info(f"Already have pending {self.reboot_requested} request, which can't be overridden by {res.reboot_requested}")
                        else:
                            self.reboot_requested = res.reboot_requested
                except UnicodeDecodeError as ex:
                    self._save_action_state(stage_id, action.name, ActionState.FAILED)
                    self.error = ex
                    log.err(f"Failed: {action}. The reason is encoding problem. Exception: {ex}")
                    raise ex
                except Exception as ex:
                    self._save_action_state(stage_id, action.name, ActionState.FAILED)
                    self.error = Exception(f"Failed: {action}. The reason: {ex}")
                    log.err(f"Failed: {action}. The reason: {ex}")
                    return False
            self._post_stage(stage_id, actions)
            self._track_flow(phase=next_phase, stage=stage_id)
            if self.reboot_requested is RebootType.AFTER_CURRENT_STAGE:
                log.debug("Not starting the next stage due to pending reboot request")
                break

        self._finished = True
        return True

    def _get_flow(self) -> typing.Dict[str, typing.List[ActiveAction]]:
        return {}

    def _pre_stage(self, stage: str, actions: typing.List[ActiveAction]):
        log.info(f"Start stage {stage!r}.")
        self.current_stage = stage
        pass

    def _post_stage(self, stage: str, actions: typing.List[ActiveAction]):
        pass

    def _is_action_required(self, stage: str, action: ActiveAction) -> bool:
        return action.is_required()

    def _invoke_action(self, action: ActiveAction) -> ActionResult:
        log.info(f"Do: {action}")
        self.current_action = action.name
        return self._do_invoke_action(action)

    @abstractmethod
    def _do_invoke_action(self, action: ActiveAction) -> ActionResult:
        pass

    def _save_action_state(self, stage: str, name: str, state: ActionState, override: bool = False) -> None:
        pass

    def _load_actions_state(self):
        if os.path.exists(self.path_to_actions_data):
            with open(self.path_to_actions_data, "r") as actions_data_file:
                return json.load(actions_data_file)

        return {"actions": []}

    def is_finished(self) -> bool:
        return self._finished or self.error is not None

    def is_failed(self) -> bool:
        return self.error is not None

    def get_error(self) -> typing.Optional[typing.Union[Exception, str]]:
        return self.error

    def get_current_stage(self) -> str:
        return self.current_stage

    def get_current_action(self) -> str:
        return self.current_action

    def _get_action_estimate(self, stage: str, action: ActiveAction) -> int:
        return action.estimate_prepare_time()

    def get_total_time(self) -> int:
        if self.total_time != 0:
            return self.total_time

        for stage_id, actions in self.stages.items():
            for action in actions:
                self.total_time += self._get_action_estimate(stage_id, action)

        return self.total_time


class PrepareActionsFlow(ActiveFlow):
    actions_data: dict

    def __init__(
        self,
        stages: typing.Dict[str, typing.List[ActiveAction]],
        state_dir: str,
        flow_tracker: typing.Optional[FlowTracker],
        resume_stage: typing.Optional[str] = None,
    ):
        super().__init__(stages, state_dir, flow_tracker, resume_stage=resume_stage)
        self.actions_data = {}

    def __enter__(self):
        self.actions_data = self._load_actions_state()
        return self

    def __exit__(self, *kwargs):
        files.rewrite_json_file(self.path_to_actions_data, self.actions_data)

    def _save_action_state(self, stage: str, name: str, state: ActionState, override: bool = False) -> None:
        for action in self.actions_data["actions"]:
            if action["stage"] == stage and action["name"] == name:
                if override or action.get("state") is None:
                    action["state"] = state
                return

        self.actions_data["actions"].append({"stage": stage, "name": name, "state": state})

    def _get_flow(self) -> typing.Dict[str, typing.List[ActiveAction]]:
        return self.stages

    def _is_action_required(self, stage: str, action: ActiveAction) -> bool:
        # Don't repeat already performed and succeeded actions (in case of process restart)
        # If an action has skipped, we should recheck if it could be skipped again
        # If an action has failed, we should perform it again to make sure conversion/distupgrade
        # will be performed correctly
        for stored_action in self.actions_data["actions"]:
            if (
                stored_action["stage"] == stage
                and stored_action["name"] == action.name
            ):
                if stored_action["state"] == ActionState.SUCCESS:
                    return False

        return action.is_required()

    def _do_invoke_action(self, action: ActiveAction) -> ActionResult:
        return action.invoke_prepare()

    def _get_action_estimate(self, stage: str, action: ActiveAction) -> int:
        if not self._is_action_required(stage, action):
            return 0
        return action.estimate_prepare_time()


class ReverseActionFlow(ActiveFlow):
    def __enter__(self):
        self.actions_data = self._load_actions_state()
        return self

    def __exit__(self, *kwargs):
        # Do not remove the actions data if an error occurs because
        # customer will likely want to retry after correcting the error on their end
        if self.error is not None and os.path.exists(self.path_to_actions_data):
            os.remove(self.path_to_actions_data)

    def _get_flow(self) -> typing.Dict[str, typing.List[ActiveAction]]:
        res = {}
        for stage_id, actions in reversed(list(self.stages.items())):
            res[stage_id] = list(reversed(list(actions)))
        return res

    def _is_action_required(self, stage: str, action: ActiveAction) -> bool:
        # I believe the finish stage could have an action that was not performed on conversion stage
        # So we ignore the case when there is no actions in persistence store
        for stored_action in self.actions_data["actions"]:
            if (
                stored_action["stage"] == stage
                and stored_action["name"] == action.name
            ):
                if stored_action["state"] == ActionState.FAILED or stored_action["state"] == ActionState.SKIPPED:
                    return False
                elif stored_action["state"] == ActionState.SUCCESS:
                    return True

        return action.is_required()


class FinishActionsFlow(ReverseActionFlow):
    def _do_invoke_action(self, action: ActiveAction) -> ActionResult:
        return action.invoke_post()

    def _get_action_estimate(self, stage: str, action: ActiveAction) -> int:
        if not self._is_action_required(stage, action):
            return 0
        return action.estimate_post_time()


class RevertActionsFlow(ReverseActionFlow):
    def _do_invoke_action(self, action: ActiveAction) -> ActionResult:
        return action.invoke_revert()

    def _get_action_estimate(self, stage: str, action: ActiveAction) -> int:
        if not self._is_action_required(stage, action):
            return 0
        return action.estimate_revert_time()


class CheckAction(Action):
    def do_check(self) -> bool:
        return self._do_check()

    def _do_check(self) -> bool:
        raise NotImplementedError("Not implemented check call")


class CheckFlow(ActionsFlow):
    stages: typing.List[CheckAction]

    def __init__(self, stages: typing.List[CheckAction]):
        super().__init__()
        self.stages = stages

    def validate_actions(self):
        # Note. This one is for development purposes only
        for check in self.stages:
            if not isinstance(check, CheckAction):
                raise TypeError(
                    "Not a CheckAction passed into check flow. "
                    f"Name of the action is {check.name!r}"
                )

    def make_checks(self) -> typing.List[CheckAction]:
        failed_checks = []
        log.debug("Start checks")
        for check in self.stages:
            log.debug("Performing check: {name}".format(name=check.name))
            try:
                if not check.do_check():
                    failed_checks.append(check)
            except Exception as e:
                raise RuntimeError(f"Exception during checking of required pre-conversion condition {check.name!r}") from e

        return failed_checks


_DEFAULT_TIME_EXCEEDED_MESSAGE = """
\033[91m**************************************************************************************
The conversion process is taking too long. It may be stuck. Please verify if the process is
still running by checking the logfile continues to update.
It is safe to interrupt the process with Ctrl+C and restart it from the same stage.
**************************************************************************************\033[0m
"""


class FlowProgressbar():
    def __init__(self, flow: ActiveFlow, writers_: typing.Optional[typing.List[writers.Writer]] = None, time_exceeded_message: str = _DEFAULT_TIME_EXCEEDED_MESSAGE):
        self.flow = flow
        self.total_time = flow.get_total_time()
        self.time_exceeded_message = time_exceeded_message

        if writers_ is None:
            writers_ = [writers.StdoutWriter()]
        self.writers = writers_

    def _seconds_to_minutes(self, seconds: int) -> str:
        minutes = int(seconds / 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"

    def get_action_description(self) -> str:
        description = f" stage {self.flow.get_current_stage()} / action {self.flow.get_current_action()} "
        description_length = len(description)
        return "(" + " " * math.floor((50 - description_length) / 2) + description + " " * math.ceil((50 - description_length) / 2) + ")"

    def write(self, msg: str) -> None:
        for writer in self.writers:
            writer.write(msg)

    def display(self) -> None:
        start_time = int(time.time())
        passed_time = 0

        while passed_time < self.total_time and not self.flow.is_finished():
            percent = int((passed_time) / self.total_time * 100)

            description = self.get_action_description()

            progress = "=" * int(percent / 2) + ">" + " " * (50 - int(percent / 2))
            progress = "[" + progress[:25] + description + progress[25:] + "]"

            terminal_size, _ = shutil.get_terminal_size()
            output = ""
            if terminal_size > 118:
                output = progress + " " + self._seconds_to_minutes(passed_time) + " / " + self._seconds_to_minutes(self.total_time)
            elif terminal_size > 65 and terminal_size < 118:
                output = description + " " + self._seconds_to_minutes(passed_time) + " / " + self._seconds_to_minutes(self.total_time)
            else:
                output = self._seconds_to_minutes(passed_time) + " / " + self._seconds_to_minutes(self.total_time)

            clean = " " * (terminal_size - len(output))

            if percent < 80:
                color = "\033[92m"  # green
            else:
                color = "\033[93m"  # yellow
            drop_color = "\033[0m"

            self.write(f"\r{color}{output}{clean}{drop_color}")
            time.sleep(1)
            passed_time = int(time.time()) - start_time

        if passed_time > self.total_time:
            self.write("\r\033[91m[" + "X" * 25 + self.get_action_description() + "X" * 25 + "] exceed\033[0m")
            self.write(self.time_exceeded_message)
