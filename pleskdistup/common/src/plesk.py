# Copyright 1999-2023. Plesk International GmbH. All rights reserved.

import enum
import os
import re
import subprocess
import typing

from . import log


def send_error_report(error_message: str) -> None:
    log.debug(f"Error report: {error_message}")
    # Todo. For now we works only on RHEL-based distros, so the path
    # to the send-error-report utility will be the same.
    # But if we will support Debian-based we should choose path carefully
    send_error_path = "/usr/local/psa/admin/bin/send-error-report"
    try:
        if os.path.exists(send_error_path):
            subprocess.run([send_error_path, "backend"], input=error_message.encode(),
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            log.debug("Sent error report")
    except Exception as ex:
        log.debug(f"Sending error report failed: {ex}")


def get_plesk_version() -> typing.List[str]:
    version_info = subprocess.check_output(["/usr/sbin/plesk", "version"], universal_newlines=True).splitlines()
    for line in version_info:
        if line.startswith("Product version"):
            version = line.split()[-1]
            return version.split(".")

    raise Exception("Unable to parse plesk version output.")


def get_plesk_full_version() -> typing.List[str]:
    return subprocess.check_output(["/usr/sbin/plesk", "version"], universal_newlines=True).splitlines()


def prepare_conversion_flag(status_flag_path: str) -> None:
    with open(status_flag_path, "w"):
        pass


def send_conversion_status(succeed: bool, status_flag_path: str) -> None:
    results_sender_path = None
    for path in ["/var/cache/parallels_installer/report-update", "/root/parallels/report-update"]:
        if os.path.exists(path):
            results_sender_path = path
            break

    # For now we are not going to install sender in scope of conversion.
    # So if we have one, use it. If not, just skip send the results
    if results_sender_path is None:
        log.warn("Unable to find report-update utility. Skip sending conversion status")
        return

    if not os.path.exists(status_flag_path):
        log.warn("Conversion status flag file does not exist. Skip sending conversion status")
        return

    plesk_version = ".".join(get_plesk_version())

    try:
        log.debug(f"Trying to send status of conversion by report-update utility {results_sender_path!r}")
        subprocess.run(
            ["/usr/bin/python3", results_sender_path, "--op", "dist-upgrade", "--rc", "0" if succeed else "1",
             "--start-flag", status_flag_path, "--from", plesk_version, "--to", plesk_version],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except Exception as ex:
        log.warn("Unable to send conversion status: {}".format(ex))

    # usually the file should be removed by report-update utility
    # but if it will be failed, we should remove it manually
    remove_conversion_flag(status_flag_path)


def remove_conversion_flag(status_flag_path: str) -> None:
    if os.path.exists(status_flag_path):
        os.unlink(status_flag_path)


def list_installed_extensions() -> typing.List[typing.Tuple[str, str]]:
    ext_info = subprocess.check_output(["/usr/sbin/plesk", "bin", "extension", "--list"], universal_newlines=True).splitlines()
    res: typing.List[typing.Tuple[str, str]] = []
    for line in ext_info:
        if " - " in line:
            name, display_name = line.split(" - ", maxsplit=1)
            res.append((name, display_name))
    return res


class PleskComponentState(enum.Enum):
    INSTALL = "install"
    UPGRADE = "upgrade"
    UP2DATE = "up2date"
    ERROR = "ERROR"


class PleskComponent:
    name: str
    state: PleskComponentState
    description: str

    def __init__(
        self,
        name: str,
        state: PleskComponentState,
        description: str,
    ):
        self.name = name
        self.state = state
        self.description = description

    def __str__(self) -> str:
        return f"{self.name} [{self.state}] - {self.description}"

    def __repr__(self) -> str:
        attrs = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{self.__class__.__name__}({attrs})"

    @property
    def is_installed(self) -> bool:
        return self.state in (PleskComponentState.UPGRADE, PleskComponentState.UP2DATE)


def list_installed_components() -> typing.Dict[str, PleskComponent]:
    comp_info = subprocess.check_output(
        ["/usr/sbin/plesk", "installer", "--select-release-current", "--show-components"],
        universal_newlines=True,
    ).splitlines()
    res: typing.Dict[str, PleskComponent] = {}
    comp_re = re.compile(r"\s*(?P<name>\S+)\s*\[(?P<state>[^]]+)\]\s*-\s*(?P<desc>.*)")
    for line in comp_info:
        m = comp_re.match(line)
        if m:
            c = PleskComponent(
                name=m["name"],
                state=PleskComponentState(m["state"]),
                description=m["desc"],
            )
            res[c.name] = c
    return res
