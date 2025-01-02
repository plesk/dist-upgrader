# Copyright 2023-2025. WebPros International GmbH. All rights reserved.
import os
import typing


def get_fstab_configuration_misorderings(configpath: str) -> typing.List[typing.Tuple[str, str]]:
    """
    Analyzes the fstab configuration file to find misorderings in mount points.
    This function reads the fstab configuration file specified by `configpath` and checks for any misorderings
    in the mount points. A misordering is defined as a mount point that appears before its parent directory
    in the fstab file.
    Args:
        configpath (str): The path to the fstab configuration file.
    Returns:
        List[Tuple[str, str]]: A list of tuples where each tuple contains a misordered parent directory and
        its corresponding mount point.
    Example:
        >>> get_fstab_configuration_misorderings('/etc/fstab')
        [('/home', '/home/user'), ('/var', '/var/log')]
    """

    if not os.path.exists(configpath):
        return []

    mount_points_order: typing.Dict[str, int] = {}
    with open(configpath, "r") as f:
        for iter, line in enumerate(f.readlines()):
            if line.startswith("#") or line == "\n" or line == "":
                continue
            mount_point = line.split()[1]
            mount_points_order[mount_point] = iter

    misorderings: typing.List[typing.Tuple[str, str]] = []
    for mount_point in mount_points_order.keys():
        if mount_point == "/" or not mount_point.startswith("/"):
            continue

        parent_dir: str = mount_point
        root_found: bool = False

        while not root_found:
            parent_dir = os.path.dirname(parent_dir)
            if parent_dir in mount_points_order and mount_points_order[parent_dir] > mount_points_order[mount_point]:
                misorderings.append((parent_dir, mount_point))
            if parent_dir == "/":
                root_found = True

    return misorderings
