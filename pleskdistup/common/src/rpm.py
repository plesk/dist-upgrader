# Copyright 2023-2024. WebPros International GmbH. All rights reserved.
import ipaddress
import itertools
import os
import shutil
import subprocess
import typing

from urllib.parse import urlparse

from . import files, util, log

REPO_HEAD_WITH_URL = """[{id}]
name={name}
baseurl={url}
"""

REPO_HEAD_WITH_METALINK = """[{id}]
name={name}
metalink={url}
"""

REPO_HEAD_WITH_MIRRORLIST = """[{id}]
name={name}
mirrorlist={url}
"""


def extract_repodata(
    repofile: str
) -> typing.Iterable[
    typing.Tuple[
        typing.Optional[str],
        typing.Optional[str],
        typing.Optional[str],
        typing.Optional[str],
        typing.Optional[str],
        typing.List[str]
    ]
]:
    id: typing.Optional[str] = None
    name: typing.Optional[str] = None
    url: typing.Optional[str] = None
    metalink: typing.Optional[str] = None
    mirrorlist: typing.Optional[str] = None
    additional: typing.List[str] = []

    with open(repofile, "r") as repo:
        for line in repo.readlines():
            if line.startswith("["):
                if id is not None:
                    yield (id, name, url, metalink, mirrorlist, additional)

                id = None
                name = None
                url = None
                metalink = None
                mirrorlist = None
                additional = []

            log.debug("Repository file line: {line}".format(line=line.rstrip()))
            if line.startswith("["):
                id = line[1:-2]
                continue

            if "=" not in line:
                additional.append(line)
                continue

            field, val = line.split("=", 1)
            field = field.strip().rstrip()
            val = val.strip().rstrip()
            if field == "name":
                name = val
            elif field == "baseurl":
                url = val
            elif field == "metalink":
                metalink = val
            elif field == "mirrorlist":
                mirrorlist = val
            else:
                additional.append(line)

    yield (id, name, url, metalink, mirrorlist, additional)


def write_repodata(
    repofile: str,
    id: typing.Optional[str],
    name: typing.Optional[str],
    url: typing.Optional[str],
    metalink: typing.Optional[str],
    mirrorlist: typing.Optional[str],
    additional: typing.List[str]
) -> None:
    repo_format = REPO_HEAD_WITH_URL
    if url is None and metalink is not None:
        url = metalink
        repo_format = REPO_HEAD_WITH_METALINK
    if url is None and mirrorlist is not None:
        url = mirrorlist
        repo_format = REPO_HEAD_WITH_MIRRORLIST

    with open(repofile, "a") as dst:
        dst.write(repo_format.format(id=id, name=name, url=url))
        for line in additional:
            dst.write(line)


def remove_repositories(
    repofile: str,
    conditions: typing.Iterable[
        typing.Callable[
            [
                typing.Optional[str],
                typing.Optional[str],
                typing.Optional[str],
                typing.Optional[str],
                typing.Optional[str]
            ],
            bool
        ]
    ]
) -> None:
    for id, name, url, metalink, mirrorlist, additional_lines in extract_repodata(repofile):
        remove = False
        for condition in conditions:
            if condition(id, name, url, metalink, mirrorlist):
                remove = True
                break

        if not remove:
            write_repodata(repofile + ".next", id, name, url, metalink, mirrorlist, additional_lines)

    if os.path.exists(repofile + ".next"):
        shutil.move(repofile + ".next", repofile)
    else:
        os.remove(repofile)


def filter_installed_packages(lookup_pkgs: typing.List[str]) -> typing.List[str]:
    return [pkg for pkg in lookup_pkgs if is_package_installed(pkg)]


def is_package_installed(pkg: str) -> bool:
    res = subprocess.run(["/usr/bin/rpm", "--quiet", "--query", pkg])
    return res.returncode == 0


def install_packages(pkgs: typing.List[str], repository: typing.Optional[str] = None, force_package_config: bool = False) -> None:
    # force_package_config is not supported yet
    if len(pkgs) == 0:
        return

    command = ["/usr/bin/yum", "install"]
    if repository is not None:
        command += ["--repo", repository]
    command += ["-y"] + pkgs

    util.logged_check_call(command)


def get_installed_packages_list(regex: str) -> typing.List[str]:
    res = subprocess.check_output(["/usr/bin/rpm", "-qa", "--queryformat", "%{NAME} %{VERSION}-%{RELEASE}\n", regex], universal_newlines=True)
    return res.splitlines()


def remove_packages(pkgs: typing.List[str]) -> None:
    if len(pkgs) == 0:
        return

    if os.path.exists("/usr/bin/package-cleanup"):
        duplicates = subprocess.check_output(["/usr/bin/package-cleanup", "--dupes"], universal_newlines=True).splitlines()
        for duplicate, pkg in itertools.product(duplicates, pkgs):
            if pkg in duplicate:
                util.logged_check_call(["/usr/bin/rpm", "-e", "--nodeps", duplicate])
                # Since we removed each duplicate, we don't need to remove the package in the end.
                if pkg in pkgs:
                    pkgs.remove(pkg)

    util.logged_check_call(["/usr/bin/rpm", "-e", "--nodeps"] + pkgs)


def handle_rpmnew(original_path: str) -> bool:
    if not os.path.exists(original_path + ".rpmnew"):
        return False

    if os.path.exists(original_path):
        log.debug("The '{path}' file has a '.rpmnew' analogue file. Going to replace the file with this rpmnew file. "
                  "The file itself will be saved as .rpmsave".format(path=original_path))
        shutil.move(original_path, original_path + ".rpmsave")
    else:
        log.debug("The '{path}' file is missing, but has '.rpmnew' analogue file. Going to use it".format(path=original_path))

    shutil.move(original_path + ".rpmnew", original_path)

    return True


def handle_all_rpmnew_files(directory: str) -> typing.List[str]:
    fixed_list = []
    for file in files.find_files_case_insensitive(directory, ["*.rpmnew"]):
        original_file = file[:-len(".rpmnew")]
        if handle_rpmnew(original_file):
            fixed_list.append(original_file)

    return fixed_list


def find_related_repofiles(repository_file: str) -> typing.List[str]:
    return files.find_files_case_insensitive("/etc/yum.repos.d", repository_file)


def update_package_list() -> None:
    util.logged_check_call(["/usr/bin/yum", "update", "-y"])


def upgrade_packages(pkgs: typing.Optional[typing.List[str]] = None) -> None:
    if pkgs is None:
        pkgs = []

    util.logged_check_call(["/usr/bin/yum", "upgrade", "-y"] + pkgs)


def autoremove_outdated_packages() -> None:
    util.logged_check_call(["/usr/bin/yum", "autoremove", "-y"])


def repository_has_none_link(
    id: typing.Optional[str],
    name: typing.Optional[str],
    url: typing.Optional[str],
    metalink: typing.Optional[str],
    mirrorlist: typing.Optional[str]
) -> bool:
    for link in (url, metalink, mirrorlist):
        if link is not None and link.lower() == "none":
            return True

    return False


def repository_source_is_ip(
    baseurl: typing.Optional[str],
    metalink: typing.Optional[str],
    mirrorlist: typing.Optional[str]
) -> bool:
    """
    Checks if any of the provided repository source URLs (baseurl, metalink, mirrorlist) is an IP address.

    Parameters:
    - baseurl (typing.Optional[str]): The base URL of the repository. Could be None.
    - metalink (typing.Optional[str]): The metalink URL of the repository. Could be None.
    - mirrorlist (typing.Optional[str]): The mirrorlist URL of the repository. Could be None.

    Returns:
    - bool: True if any of the URLs is an IP address, False otherwise.
    """
    for link in (baseurl, metalink, mirrorlist):
        if link is None:
            continue

        hostname = urlparse(link).hostname
        if not hostname:
            continue
        try:
            ipaddress.ip_address(hostname)
            return True
        except ValueError:
            continue
    return False
