# Copyright 2023-2025. WebPros International GmbH. All rights reserved.
import ipaddress
import itertools
import os
import shutil
import subprocess
import typing

from urllib.parse import urlparse

from . import files, util, log

REPO_HEAD = """[{id}]
name={name}
"""


class Repository:
    def __init__(
            self,
            id: str,
            name: typing.Optional[str] = None,
            url: typing.Optional[str] = None,
            metalink: typing.Optional[str] = None,
            mirrorlist: typing.Optional[str] = None,
            additional: typing.Optional[typing.List[str]] = None
    ):
        self.id = id
        self.name = name
        self.url = url
        self.metalink = metalink
        self.mirrorlist = mirrorlist
        self.additional = [] if additional is None else additional

    def __str__(self) -> str:
        return f"Repository(id={self.id}, name={self.name}, url={self.url}, metalink={self.metalink}, mirrorlist={self.mirrorlist}, additional={self.additional})"

    def __repr__(self) -> str:
        content = REPO_HEAD.format(id=self.id, name=self.name)

        if self.url is not None:
            content += f"baseurl={self.url}\n"
        if self.metalink is not None:
            content += f"metalink={self.metalink}\n"
        if self.mirrorlist is not None:
            content += f"mirrorlist={self.mirrorlist}\n"

        for add_line in self.additional:
            content += add_line

        return content


def extract_repodata(
    repofile: str
) -> typing.Iterable[Repository]:
    id: typing.Optional[str] = None
    name: typing.Optional[str] = None
    url: typing.Optional[str] = None
    metalink: typing.Optional[str] = None
    mirrorlist: typing.Optional[str] = None
    additional: typing.List[str] = []

    if not os.path.exists(repofile):
        raise FileNotFoundError(f"The repository file {repofile!r} does not exist")

    with open(repofile, "r") as repo:
        for line in repo.readlines():
            if line.startswith("["):
                if id is not None:
                    yield Repository(id, name, url, metalink, mirrorlist, additional)

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

    yield Repository(id, name, url, metalink, mirrorlist, additional)


def write_repodata(
    repofile: str,
    repodata: Repository
) -> None:
    with open(repofile, "a") as dst:
        dst.write(repr(repodata))


def remove_repositories(
    repofile: str,
    conditions: typing.Iterable[
        typing.Callable[
            [
                Repository
            ],
            bool
        ]
    ]
) -> None:
    for repodata in extract_repodata(repofile):
        remove = False
        for condition in conditions:
            if condition(repodata):
                remove = True
                break

        if not remove:
            write_repodata(repofile + ".next", repodata)

    if os.path.exists(repofile + ".next"):
        shutil.move(repofile + ".next", repofile)
    else:
        os.remove(repofile)


def filter_installed_packages(lookup_pkgs: typing.List[str]) -> typing.List[str]:
    return [pkg for pkg in lookup_pkgs if is_package_installed(pkg)]


def is_package_installed(pkg: str) -> bool:
    res = subprocess.run(["/usr/bin/rpm", "--quiet", "--query", pkg])
    return res.returncode == 0


def install_packages(
    pkgs: typing.List[str],
    repository: typing.Optional[str] = None,
    force_package_config: bool = False,
    simulate: bool = False,
) -> None:
    # force_package_config is not supported yet
    if len(pkgs) == 0:
        return

    command = ["/usr/bin/yum", "install"]
    if repository is not None:
        command += ["--repo", repository]
    if simulate:
        command += ["--setopt", "tsflags=test"]
    command += ["-y"] + pkgs

    util.logged_check_call(command)


def get_installed_packages_list(regex: str) -> typing.List[typing.Tuple[str, str]]:
    pkgs_info = subprocess.check_output(["/usr/bin/rpm", "-qa", "--queryformat", "%{NAME} %{VERSION}-%{RELEASE}\n", regex], universal_newlines=True)
    result = []
    for line in pkgs_info.splitlines():
        name, version = line.split(" ", 1)
        result.append((name, version))
    return result


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
    repository: Repository
) -> bool:
    for link in (repository.url, repository.metalink, repository.mirrorlist):
        if link is not None and link.lower() == "none":
            return True

    return False


def repository_source_is_ip(
    repository: Repository
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
    for link in (repository.url, repository.metalink, repository.mirrorlist):
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
