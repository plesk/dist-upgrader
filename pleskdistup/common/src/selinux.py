# Copyright 2023-2026. WebPros International GmbH. All rights reserved.
import enum
import os
import re
import subprocess
import typing

from . import log

SELINUX_CONFIG_PATH = "/etc/selinux/config"
SEMANAGE_BIN_PATH = "/usr/sbin/semanage"


class SelinuxMode(enum.Enum):
    ENFORCING = "enforcing"
    PERMISSIVE = "permissive"
    DISABLED = "disabled"
    UNKNOWN = "unknown"


def get_configured_mode(config_path: str = SELINUX_CONFIG_PATH) -> SelinuxMode:
    """
    Return the SELinux mode selected in the configuration file, or SelinuxMode.UNKNOWN when it
    cannot be determined: the file is absent or unreadable, holds no effective 'SELINUX='
    assignment, or the assigned value is not one of the recognized modes. Commented-out
    assignments are ignored and the first effective assignment wins, as in libselinux itself.
    """
    if not os.path.exists(config_path):
        return SelinuxMode.UNKNOWN

    with open(config_path, encoding="utf-8", errors="replace") as config:
        for line in config:
            line = line.strip()
            if line.startswith("SELINUX="):
                value = line.split("=", 1)[1].split("#", 1)[0].strip().strip("\"'").lower()
                try:
                    return SelinuxMode(value)
                except ValueError:
                    log.debug(f"Unexpected SELinux mode {value!r} is configured in {config_path!r}")
                    return SelinuxMode.UNKNOWN

    return SelinuxMode.UNKNOWN


def get_boolean_persisted_state(boolean_name: str) -> typing.Optional[bool]:
    """
    Return the persisted (policy store) value of an SELinux boolean, or None when it cannot be
    determined: the semanage utility is unavailable, it fails, or it does not list the boolean.
    'semanage boolean -l' prints '<name> (<runtime> , <persisted>) <description>', so the
    value we are after is the second one.
    """
    if not os.path.exists(SEMANAGE_BIN_PATH):
        log.debug(f"Unable to read the {boolean_name!r} SELinux boolean: {SEMANAGE_BIN_PATH!r} does not exist")
        return None

    try:
        output = subprocess.check_output(
            [SEMANAGE_BIN_PATH, "boolean", "-l"],
            universal_newlines=True, stderr=subprocess.DEVNULL,
            # semanage renders the state columns through gettext, so on a localized host they
            # would read '(выкл , выкл)' and never match. The locale is pinned to keep the
            # output parsable. The environment is inherited rather than replaced, since
            # semanage is a python script and may rely on the rest of it.
            env=dict(os.environ, LC_ALL="C", LANG="C"),
        )
    except subprocess.SubprocessError as ex:
        log.debug(f"Unable to read the {boolean_name!r} SELinux boolean: {ex}")
        return None

    # 'httpd_can_network_connect             (off  ,  off)  Allow httpd to ...'
    #                                          ^runtime ^persisted
    boolean_line_regex = re.compile(
        r"^{name}\s+\((?:on|off)\s*,\s*(?P<persisted>on|off)\s*\)".format(name=re.escape(boolean_name))
    )
    for line in output.splitlines():
        match = boolean_line_regex.match(line)
        if match is not None:
            return match.group("persisted") == "on"

    log.debug(f"The {boolean_name!r} SELinux boolean is not listed by {SEMANAGE_BIN_PATH!r}")
    return None
