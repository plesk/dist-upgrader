#!/usr/bin/python3
# Copyright 2023-2024. WebPros International GmbH. All rights reserved.

import argparse
import json
import logging
import os
import sys
import time
import traceback
import typing
from collections import Counter
from datetime import datetime

import pleskdistup
import pleskdistup.config
import pleskdistup.convert
import pleskdistup.registry
from pleskdistup import messages
from pleskdistup.common import action, dist, feedback, files, log, motd, plesk, systemd, writers
from pleskdistup.phase import Phase
from pleskdistup.resume import ResumeData
from pleskdistup.sysdesc import BasicSystemDescription
from pleskdistup.upgrader import DistUpgrader


PathType = typing.Union[os.PathLike, str]


def printerr(msg, logit: bool = True) -> None:
    print(msg, file=sys.stderr)
    if logit:
        log.err(msg)


def prepare_feedback(
    upgrader: DistUpgrader,
    options: typing.Any,
    logfile_path: str,
    util_name: str,
    issues_url: str
) -> None:
    feedback_archive: str = f"{util_name}_feedback.zip"

    feed = feedback.Feedback(
        util_name,
        pleskdistup.config.revision,
        upgrader.upgrader_name,
        upgrader.upgrader_version,
        attached_files=[
            logfile_path,
            action.ActiveFlow.get_path_to_actions_data(options.state_dir),
            options.resume_path,
        ],
    )
    feed = upgrader.prepare_feedback(feed)
    feed.prepare()
    feed.save_archive(feedback_archive)

    print(
        messages.FEEDBACK_IS_READY_MESSAGE.format(
            feedback_archive_path=feedback_archive, issues_url=issues_url
        ),
        end='',
    )


def show_status(status_file_path: PathType) -> None:
    if not os.path.exists(status_file_path):
        print("Conversion process is not running.")
        return

    print("Conversion process in progress:")
    status = files.get_last_lines(status_file_path, 1)
    print(status[0])


def monitor_status(status_file_path: PathType) -> None:
    if not os.path.exists(status_file_path):
        print("Conversion process is not running.")
        return

    with open(status_file_path, "r") as status:
        status.readlines()
        while os.path.exists(status_file_path):
            line = status.readline().rstrip()
            sys.stdout.write("\r" + line)
            sys.stdout.flush()
            time.sleep(1)


def show_fail_motd(logfile_path: PathType, util_name: str) -> None:
    motd.add_finish_ssh_login_message(f"""
Something went wrong during dist-upgrade by {util_name}.
See the {logfile_path} file for more information.
""")
    motd.publish_finish_ssh_login_message()


def required_conditions_satisfied(upgrader: DistUpgrader, options: typing.Any, phase: Phase) -> bool:
    checks = upgrader.get_check_actions(options, phase)

    try:
        with action.CheckFlow(checks) as check_flow, writers.StdoutWriter() as writer:
            writer.write("Doing preparation checks...\n")
            check_flow.validate_actions()
            failed_checks = check_flow.make_checks()
            writer.write("\r")
            for check in failed_checks:
                writer.write(check)
                log.err(check)

            if failed_checks:
                return False
            return True
    except Exception as ex:
        ex_info = traceback.format_exc()
        printerr(f"Preparation checks failed: {ex}\n{ex_info}")
        return False


def handle_error(
    error: str,
    logfile_path: PathType,
    util_name: str,
    status_flag_path: PathType,
    upgrader: DistUpgrader,
) -> None:
    print()
    print(error)
    print(messages.FAIL_MESSAGE_HEAD.format(logfile_path=logfile_path), end='')

    error_message = f"[{util_name}] (dist-upgrader {pleskdistup.config.revision}, upgrader module {upgrader.upgrader_name} {upgrader.upgrader_version}) process has failed. Error: {error}\n\n"
    for line in files.get_last_lines(logfile_path, 100):
        print(line, end='')
        error_message += line

    print(messages.FAIL_MESSAGE_TAIL.format(util_name=util_name, logfile_path=logfile_path), end='')

    plesk.send_error_report(error_message)
    plesk.send_conversion_status(False, str(status_flag_path))

    log.err(f"{util_name} process has failed. Error: {error}")
    show_fail_motd(logfile_path, util_name)


class ResumeTracker(action.FlowTracker):
    resume_data: ResumeData
    resume_path: str

    def __init__(
        self,
        resume_data: ResumeData,
        resume_path: str,
    ):
        self.resume_data = resume_data
        self.resume_path = resume_path

    def __call__(
        self,
        phase: typing.Any = None,
        stage: typing.Optional[str] = None,
    ) -> None:
        log.debug(f"ResumeTracker: phase={phase!r}, stage={stage!r}")
        if phase is not None:
            assert isinstance(phase, Phase), "phase is not an instance of Phase"
            self.resume_data.phase = phase
            # Changing phase resets stage
            self.resume_data.stage = None
        elif stage is not None:
            self.resume_data.stage = stage
        with open(self.resume_path, "w") as f:
            log.debug(f"Writing {self.resume_data!r} to {self.resume_path!r}")
            json.dump(self.resume_data.to_dict(), f)


def find_duplicate_actions(
    actions_map: typing.Dict[str, typing.List[action.ActiveAction]]
) -> typing.Optional[typing.Tuple[str, typing.List[str]]]:
    for stage_id, actions in actions_map.items():
        cnt = Counter(act.name for act in actions)
        dup = [k for k, v in cnt.items() if v > 1]
        if dup:
            return stage_id, dup
    return None


def do_convert(
    upgrader: DistUpgrader,
    options: typing.Any,
    status_file_path: PathType,
    logfile_path: PathType,
    util_name: str,
    show_plan: bool,
) -> int:
    if not options.resume and not required_conditions_satisfied(upgrader, options, options.phase):
        printerr("Please fix noted problems before continuing the conversion")
        return 1

    actions_map = upgrader.construct_actions(sys.argv[0], options, options.phase)
    dup = find_duplicate_actions(actions_map)
    if dup:
        printerr(f"Stage {dup[0]!r} contains duplicate actions: {dup[1]}")
        return 1

    if not show_plan:
        resume_tracker = ResumeTracker(options.resume_data, options.resume_path)
        if options.resume:
            # Restore status flag in resume mode (it could be removed by
            # plesk.send_conversion_status() called by handle_error() in
            # case of error)
            if not os.path.exists(options.status_flag_path):
                log.debug(f"Restoring lost status flag at {options.status_flag_path!r} due to resume mode")
                plesk.prepare_conversion_flag(options.status_flag_path)
        else:
            # Write initial resume file
            resume_tracker()

        try:
            convert_result = pleskdistup.convert.convert(
                options.phase,
                options.resume_stage,
                actions_map,
                options.state_dir,
                status_file_path,
                messages.TIME_EXCEEDED_MESSAGE.format(logfile_path=logfile_path),
                resume_tracker,
            )
            if not options.no_reboot and convert_result.reboot_requested:
                log.info("Going to reboot the system")
                if options.phase is Phase.CONVERT:
                    print(
                        messages.CONVERT_RESTART_MESSAGE.format(
                            time=datetime.now().strftime("%H:%M:%S"),
                            util_path=os.path.abspath(sys.argv[0])
                        ),
                        end='',
                    )
                elif options.phase is Phase.FINISH:
                    print(messages.FINISH_RESTART_MESSAGE, end='')
                systemd.do_reboot()
        except Exception as e:
            handle_error(str(e), logfile_path, util_name, options.status_flag_path, upgrader)
            return 1
    else:
        for stage_id, actions in actions_map.items():
            if not options.show_hidden_stages and stage_id.startswith("_"):
                continue
            print(f"Stage {stage_id!r}:")
            for act in actions:
                if not options.show_hidden_stages and act.name.startswith("_"):
                    continue
                print(f"- {act.name}")

    if options.phase == Phase.REVERT:
        print(messages.REVERT_FINISHED_MESSAGE, end='')

    return 0


def read_resume_data(resume_path: PathType) -> ResumeData:
    with open(resume_path, "r") as f:
        resume_dict = json.load(f)
    try:
        return ResumeData.from_dict(resume_dict)
    except Exception:
        printerr(f"Corrupted resume file {resume_path!r}.")
        raise


DESC_MESSAGE = """Use this utility to dist-upgrade your server with Plesk.

The utility writes a log to the file specified by --logfile. If there are any issues, you can find more information in the log file.

Utility version is {util_revision}.
"""


class ArgumentDefaultsRawDescriptionHelpFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawTextHelpFormatter):
    pass


def main():
    util_name = os.path.basename(sys.argv[0])

    parser = argparse.ArgumentParser(
        description=DESC_MESSAGE.format(
            util_revision=pleskdistup.config.revision,
        ),
        formatter_class=ArgumentDefaultsRawDescriptionHelpFormatter,
        add_help=False,
    )
    operation_group = parser.add_mutually_exclusive_group()
    parser.add_argument(
        "-h", "--help", action="store_true", default=argparse.SUPPRESS,
        help="show this help message and exit"
    )
    # Overrides safety checks, dangerous
    parser.add_argument("--I-know-what-I-am-doing", action="store_true", dest="unsafe_mode", help=argparse.SUPPRESS)
    parser.add_argument("--log-file", default=f"/var/log/plesk/{util_name}.log", help="path to the log file.")
    operation_group.add_argument(
        "--monitor", action="store_true",
        help="monitor the status of the conversion process in real time."
    )
    parser.add_argument("--no-reboot", action="store_true", help=argparse.SUPPRESS)
    operation_group.add_argument(
        "-p", "--phase", choices=("convert", "revert", "finish"),
        # help="start one of the conversion process' phases."
        help=argparse.SUPPRESS
    )
    operation_group.add_argument(
        "-f", "--prepare-feedback", action="store_true",
        help="prepare feedback archive that should be sent to the developers for further failure investigation."
    )
    operation_group.add_argument(
        "--resume", action="store_true",
        help="resume the process after reboot or interruption."
    )
    parser.add_argument("--resume-stage", help=argparse.SUPPRESS)
    operation_group.add_argument(
        "--revert", action="store_const", dest="phase", const="revert",
        help="revert all changes made by this tool. This option can only take effect "
             "if packages from the new OS version haven't been installed."
    )
    parser.add_argument("--show-hidden-stages", action="store_true", help=argparse.SUPPRESS)
    operation_group.add_argument(
        "--show-plan", action="store_true",
        help="don't convert the system, just show what has to be done."
    )
    parser.add_argument(
        "--state-dir", default=f"/usr/local/psa/var/{util_name}",
        help="directory to keep dist-upgrade state files. Please note that the directory "
             "must not be cleaned on reboot, so /tmp or /usr/local/psa/tmp usually won't do."
    )
    operation_group.add_argument(
        "--status", action="store_true",
        help="show the current status of the conversion process."
    )
    parser.add_argument(
        "--status-file", default=f"/tmp/{util_name}.status",
        help="path to the status file (used by --status and --monitor to get status)."
    )
    parser.add_argument("--upgrader-name", help=argparse.SUPPRESS)
    parser.add_argument(
        "--verbose", nargs="?", choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
        const="DEBUG", default="DEBUG", help="select verbosity level."
    )
    parser.add_argument(
        "-v", "--version", action="store_true",
        help="show the version of this utility."
    )

    options, extra_args = parser.parse_known_args()
    if getattr(options, "help", False):
        parser.print_help()
    else:
        options.help = False

    logfile_path = options.log_file
    log.init_logger(
        [logfile_path],
        [],
        loglevel=getattr(logging, options.verbose, logging.DEBUG),
    )

    if not options.status and not options.monitor:
        log.info(f"Started with arguments {sys.argv}")

    if options.unsafe_mode:
        log.warn("Operating in unsafe mode!")

    status_file_path = options.status_file
    if options.status:
        show_status(status_file_path)
        return 0

    if options.monitor:
        monitor_status(status_file_path)
        return 0

    if options.phase:
        if options.resume:
            printerr("--resume can't be used together with --phase")
            return 1
    else:
        options.phase = "convert"

    options.phase = Phase.from_str(options.phase)
    options.resume_path = os.path.join(options.state_dir, "resume.json")

    if options.resume:
        try:
            resume_data = read_resume_data(options.resume_path)
            log.debug(f"Resuming with command-line arguments {resume_data.argv}")
            resume_options, extra_args = parser.parse_known_args(resume_data.argv[1:])
            resume_options.resume = True
            resume_options.help = False
            resume_options.phase = resume_data.phase
            resume_options.resume_stage = resume_data.stage if not options.resume_stage else options.resume_stage
            resume_options.upgrader_name = resume_data.upgrader_name if not options.upgrader_name else options.upgrader_name
            resume_options.resume_path = options.resume_path
            resume_options.resume_data = resume_data
            options = resume_options
        except Exception as ex:
            ex_info = traceback.format_exc()
            printerr(f"Couldn't resume from {options.resume_path!r}: {ex}\n{ex_info}")
            return 1
    else:
        options.resume_stage = None

    if options.prepare_feedback and not options.upgrader_name:
        try:
            resume_data = read_resume_data(options.resume_path)
            options.upgrader_name = resume_data.upgrader_name
            log.debug(f"Got upgrader name {options.upgrader_name!r} for feedback preparation from {options.resume_path!r}")
        except Exception as ex:
            ex_info = traceback.format_exc()
            log.warn(f"Couldn't get upgrader name from {options.resume_path!r}: {ex}\n{ex_info}")

    distro = dist.get_distro()
    log.debug(f"Detected current OS distribution as {distro}")
    if isinstance(distro, dist.UnknownDistro):
        printerr(messages.NOT_SUPPORTED_ERROR)
        return 1
    sys_desc = BasicSystemDescription(distro.name, distro.version)
    log.debug(f"Current system description: {sys_desc}")

    log.debug(f"Available upgraders: {list(pleskdistup.registry.iter_upgraders())}")
    if not options.upgrader_name:
        log.debug(f"Looking for upgrader from {distro}")
        upgraders = list(pleskdistup.registry.iter_upgraders(sys_desc))
    else:
        log.debug(f"Looking for upgrader by the name '{options.upgrader_name}'")
        upgraders = list(pleskdistup.registry.iter_upgraders(upgrader_name=options.upgrader_name))
    log.debug(f"Found upgraders: {upgraders}")
    if not upgraders:
        printerr(f"No upgraders found for your system ({distro})")
        return 1
    if len(upgraders) > 1:
        log.info(f"Multiple upgraders found ({len(upgraders)}), using the first one")
    upgrader = upgraders[0].create_upgrader()
    log.debug(f"Selected upgrader: {upgrader}")
    if not options.resume:
        options.resume_data = ResumeData(
            phase=options.phase,
            argv=sys.argv,
            upgrader_name=upgraders[0].upgrader_name,
            stage=None
        )
    log.debug(
        f"Upgrader {upgrader} support of your system: "
        f"as source = {upgrader.supports(from_system=sys_desc)}, "
        f"as target = {upgrader.supports(to_system=sys_desc)}"
    )
    if (
        not upgrader.supports(from_system=sys_desc)
        and ((not options.resume and not options.prepare_feedback) or not upgrader.supports(to_system=sys_desc))
    ):
        printerr(f"Selected upgrader {upgrader} doesn't support your system ({distro})")
        if not options.unsafe_mode:
            return 1
        else:
            log.warn("Failed check ignored due to unsafe mode")

    if options.help:
        print(
            f"\nThe currently selected upgrader is {upgrader.upgrader_name!r} of version {upgrader.upgrader_version}.\n"
            "Its help message follows.\n"
        )
        upgrader.parse_args(["--help"])
        parser.exit()
    if options.version:
        print(
            f"Plesk dist-upgrader {pleskdistup.config.revision}.\n"
            f"{upgrader.upgrader_name} {upgrader.upgrader_version}."
        )
        return 0
    upgrader.parse_args(extra_args)

    if options.prepare_feedback:
        prepare_feedback(upgrader, options, logfile_path, util_name, upgrader.issues_url)
        return 0

    if not os.path.exists(options.state_dir):
        os.mkdir(options.state_dir, 0o750)
    elif not os.path.isdir(options.state_dir):
        printerr(
            f"The state directory path exists at {options.state_dir!r}, but it's not a directory. "
            "You can change the directory using --state-dir."
        )
        return 1
    options.status_flag_path = os.path.join(options.state_dir, "dist-upgrade-conversion.flag")
    options.completion_flag_path = os.path.join(options.state_dir, "dist-upgrade-done.flag")

    convert_res = do_convert(upgrader, options, status_file_path, logfile_path, util_name, options.show_plan)
    if convert_res == 0 and os.path.exists(options.completion_flag_path):
        log.info("Dist-upgrade process completed, cleaning up...")
        if os.path.exists(options.resume_path):
            os.unlink(options.resume_path)
            log.debug(f"Removed the resume file {options.resume_path!r}")
        os.unlink(options.completion_flag_path)
    return convert_res


if __name__ == "__main__":
    sys.exit(main())
