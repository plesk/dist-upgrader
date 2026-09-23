# Copyright 2023-2025. WebPros International GmbH. All rights reserved.
import typing

from . import util

DEBCONF_SHOW_CMD = "/usr/bin/debconf-show"


def parse_show_output(output: str) -> typing.Dict[str, typing.List[str]]:
    """
    Parse the output of 'debconf-show <package>' into a question -> values map.
    Every value is a list: multiselect values hold one item per choice,
    other values hold a single item, empty values are empty lists.
    debconf-show does not print question types, so a free-text string value
    containing ", " is split into several items too.
    :param output: stdout of debconf-show
    :return: map of question name (e.g. "grub-pc/install_devices") to its values
    """
    result: typing.Dict[str, typing.List[str]] = {}
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("*"):
            line = line[1:].strip()

        name, sep, value = line.partition(":")
        if not sep or not name:
            continue

        value = value.strip()
        # Not just ',' because linux_cmdline could contain
        # the symbol inside a value
        result[name] = value.split(", ") if value else []
    return result


def get_package_values(package: str) -> typing.Dict[str, typing.List[str]]:
    """
    Get debconf values of all questions owned by the package.
    :param package: package name, e.g. "grub-pc"
    :return: map of question name to its values, see parse_show_output
    """
    return parse_show_output(util.logged_check_call([DEBCONF_SHOW_CMD, package]))
