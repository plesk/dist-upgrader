# Copyright 2023-2024. WebPros International GmbH. All rights reserved.
import os
import json
import shutil
import typing

from enum import IntEnum

from . import files, log, rpm


PATH_TO_CONFIGFILES = "/etc/leapp/files"
LEAPP_REPOS_FILE_PATH = os.path.join(PATH_TO_CONFIGFILES, "leapp_upgrade_repositories.repo")
LEAPP_MAP_FILE_PATH = os.path.join(PATH_TO_CONFIGFILES, "repomap.csv")
LEAPP_PKGS_CONF_PATH = os.path.join(PATH_TO_CONFIGFILES, "pes-events.json")

REPO_HEAD_WITH_URL = """
[{id}]
name={name}
baseurl={url}
"""

REPO_HEAD_WITH_METALINK = """
[{id}]
name={name}
metalink={url}
"""

REPO_HEAD_WITH_MIRRORLIST = """
[{id}]
name={name}
mirrorlist={url}
"""


def _do_replacement(
    to_change: typing.Optional[str],
    replacement_list: typing.List[
        typing.Callable[[str], str]]
) -> typing.Optional[str]:
    if to_change is None:
        return None

    for replace in replacement_list:
        to_change = replace(to_change)
    return to_change


def _do_id_replacement(id: typing.Optional[str]) -> typing.Optional[str]:
    return _do_replacement(id, [
        lambda to_change: "alma-" + to_change,
    ])


def _do_name_replacement(name: typing.Optional[str]) -> typing.Optional[str]:
    return _do_replacement(name, [
        lambda to_change: "Alma " + to_change,
        lambda to_change: to_change.replace("Enterprise Linux 7",  "Enterprise Linux 8"),
        lambda to_change: to_change.replace("EPEL-7", "EPEL-8"),
        lambda to_change: to_change.replace("$releasever", "8"),
    ])


def _fixup_old_php_urls(to_change: str) -> str:
    supported_old_versions = ["7.1", "7.2", "7.3"]
    for version in supported_old_versions:
        if "PHP_" + version in to_change:
            return to_change.replace("rpm-CentOS-7", "rpm-CentOS-8")

    return to_change


def _fix_rackspace_repository(to_change: str) -> str:
    if "mirror.rackspace.com" in to_change:
        return to_change.replace("centos7-amd64", "rhel8-amd64")

    return to_change


def _fix_mariadb_repository(to_change: str) -> str:
    # Mariadb official repository doesn't support short url for centos 8 since 10.11
    # Since there are short URL for rhel8 short for all versions, we could use it instead
    if "yum.mariadb.org" in to_change:
        return to_change.replace("centos7", "rhel8")

    return to_change


def _fix_postgresql_official_repository(to_change: str) -> str:
    # The default PostgreSQL official repository list includes a testing repository
    # intended for CentOS 7, which does not have an equivalent for RHEL-based 8.
    # This behavior is specific exactly for testing repository, srpms, common and debug
    # repositories are fine.
    # This issue is applicable to all PostgreSQL versions before 16.
    # Therefore, we need to create a mapping to the non-testing repository
    # to prevent errors during the conversion process.
    if "download.postgresql.org" in to_change:
        splited = to_change.split("/")
        for index, item in enumerate(splited):
            if item == "testing":
                # An exclusion for srpms repository. No rhel 8 repository when version is 14. Looks strange, maybe some kind of a mess
                if splited[index - 1] == "srpms" and splited[index + 1].isdigit() and int(splited[index + 1]) != 14:
                    return to_change
                if splited[index + 1] == "common" or splited[index + 1] == "debug":
                    return to_change
                if splited[index + 1].isdigit() and int(splited[index + 1]) >= 16:
                    return to_change

        return to_change.replace("/testing/", "/")

    return to_change


def _do_url_replacement(url: typing.Optional[str]) -> typing.Optional[str]:
    return _do_replacement(url, [
        _fixup_old_php_urls,
        _fix_rackspace_repository,
        _fix_mariadb_repository,
        _fix_postgresql_official_repository,
        lambda to_change: to_change.replace("rpm-CentOS-7", "rpm-RedHat-el8"),
        lambda to_change: to_change.replace("CloudLinux-7", "CloudLinux-8"),
        lambda to_change: to_change.replace("epel-7", "epel-8"),
        lambda to_change: to_change.replace("epel-debug-7", "epel-debug-8"),
        lambda to_change: to_change.replace("epel-source-7", "epel-source-8"),
        lambda to_change: to_change.replace("centos7", "centos8"),
        lambda to_change: to_change.replace("centos/7", "centos/8"),
        lambda to_change: to_change.replace("rhel/7", "rhel/8"),
        lambda to_change: to_change.replace("CentOS_7", "CentOS_8"),
        lambda to_change: to_change.replace("rhel-$releasever", "rhel-8"),
        lambda to_change: to_change.replace("$releasever", "8"),
        lambda to_change: to_change.replace("autoinstall.plesk.com/PMM_0.1.10", "autoinstall.plesk.com/PMM_0.1.11"),
        lambda to_change: to_change.replace("autoinstall.plesk.com/PMM0", "autoinstall.plesk.com/PMM_0.1.11"),
    ])


def _do_common_replacement(line: typing.Optional[str]) -> typing.Optional[str]:
    return _do_replacement(line, [
        lambda to_change: to_change.replace("EPEL-7", "EPEL-8"),
        # We can't check repository gpg because the key is not stored in the temporary file system
        # ToDo: Maybe we could find a way to put the key into the file system
        lambda to_change: to_change.replace("repo_gpgcheck = 1", "repo_gpgcheck = 0"),
    ])


def is_repo_ok(
    id: typing.Optional[str],
    name: typing.Optional[str],
    url: typing.Optional[str],
    metalink: typing.Optional[str],
    mirrorlist: typing.Optional[str]
) -> bool:
    if name is None:
        log.warn("Repository info for '[{id}]' has no a name".format(id=id))
        return False

    if url is None and metalink is None and mirrorlist is None:
        log.warn("Repository info for '{id}' has no baseurl and metalink".format(id=id))
        return False

    return True


def adopt_repositories(repofile: str, ignore: typing.Optional[typing.List[str]] = None) -> None:
    if ignore is None:
        ignore = []

    log.debug("Adopt repofile '{filename}' for AlmaLinux 8".format(filename=repofile))

    if not os.path.exists(repofile):
        log.warn("The repository adapter has tried to open an unexistent file: {filename}".format(filename=repofile))
        return

    with open(repofile + ".next", "a") as dst:
        for id, name, url, metalink, mirrorlist, additional_lines in rpm.extract_repodata(repofile):
            if not is_repo_ok(id, name, url, metalink, mirrorlist):
                continue

            if id in ignore:
                log.debug("Skip repository '{id}' adaptation since it is in ignore list.".format(id=id))
                continue

            log.debug("Adopt repository with id '{id}' is extracted.".format(id=id))

            id = _do_id_replacement(id)
            name = _do_name_replacement(name)
            if url is not None:
                url = _do_url_replacement(url)
                repo_format = REPO_HEAD_WITH_URL
            elif metalink is not None:
                url = _do_url_replacement(metalink)
                repo_format = REPO_HEAD_WITH_METALINK
            else:
                url = _do_url_replacement(mirrorlist)
                repo_format = REPO_HEAD_WITH_MIRRORLIST

            dst.write(repo_format.format(id=id, name=name, url=url))

            for line in (_do_common_replacement(add_line) for add_line in additional_lines):
                if line is not None:
                    dst.write(line)

    shutil.move(repofile + ".next", repofile)


def add_repositories_mapping(repofiles: typing.List[str], ignore: typing.Optional[typing.List[str]] = None,
                             leapp_repos_file_path: str = LEAPP_REPOS_FILE_PATH,
                             mapfile_path: str = LEAPP_MAP_FILE_PATH) -> None:
    if ignore is None:
        ignore = []

    with open(leapp_repos_file_path, "a") as leapp_repos_file, open(mapfile_path, "a") as map_file:
        for file in repofiles:
            log.debug("Processing repofile '{filename}' into leapp configuration".format(filename=file))

            if not os.path.exists(file):
                log.warn("The repository mapper has tried to open an unexistent file: {filename}".format(filename=file))
                continue

            for id, name, url, metalink, mirrorlist, additional_lines in rpm.extract_repodata(file):
                if not is_repo_ok(id, name, url, metalink, mirrorlist):
                    continue

                if id is None:
                    log.warn(f"Skip repository entry without id from {file}")
                    continue

                if id in ignore:
                    log.debug("Skip repository '{id}' since it is in ignore list.".format(id=id))
                    continue

                log.debug("Repository entry with id '{id}' is extracted.".format(id=id))

                new_id = _do_id_replacement(id)
                name = _do_name_replacement(name)
                if new_id is None or name is None:
                    log.warn(f"Skip repository '{id}' since it has no next id or name")
                    continue

                if url is not None:
                    url = _do_url_replacement(url)
                    repo_format = REPO_HEAD_WITH_URL
                elif metalink is not None:
                    url = _do_url_replacement(metalink)
                    repo_format = REPO_HEAD_WITH_METALINK
                else:
                    url = _do_url_replacement(mirrorlist)
                    repo_format = REPO_HEAD_WITH_MIRRORLIST
                if url is None:
                    log.warn(f"Skip repository '{id}' since it has no baseurl, metalink and mirrorlist")
                    continue

                leapp_repos_file.write(repo_format.format(id=new_id, name=name, url=url))

                for line in (_do_common_replacement(add_line) for add_line in additional_lines):
                    if line is not None:
                        leapp_repos_file.write(line)

                # Special case for plesk repository. We need to add dist repository to install some of plesk packages
                # We support metalink for plesk repository, regardless of the fact we don't use them now
                if id.startswith("PLESK_18_0") and "extras" in id and url is not None:
                    leapp_repos_file.write(repo_format.format(id=new_id.replace("-extras", ""),
                                                              name=name.replace("extras", ""),
                                                              url=url.replace("extras", "dist")))
                    leapp_repos_file.write("enabled=1\ngpgcheck=1\n")

                    map_file.write("{oldrepo},{newrepo},{newrepo},all,all,x86_64,rpm,ga,ga\n".format(oldrepo=id, newrepo=new_id.replace("-extras", "")))

                leapp_repos_file.write("\n")

                map_file.write("{oldrepo},{newrepo},{newrepo},all,all,x86_64,rpm,ga,ga\n".format(oldrepo=id, newrepo=new_id))

        map_file.write("\n")


def set_package_repository(package: str, repository: str, leapp_pkgs_conf_path: str = LEAPP_PKGS_CONF_PATH) -> None:
    pkg_mapping = None
    log.debug(f"Reconfigure mapping for package '{package}' to repository '{repository}'")
    with open(leapp_pkgs_conf_path, "r") as pkg_mapping_file:
        pkg_mapping = json.load(pkg_mapping_file)
        for info in pkg_mapping["packageinfo"]:
            if not info["out_packageset"] or not info["out_packageset"]["package"]:
                continue

            for outpkg in info["out_packageset"]["package"]:
                if outpkg["name"] == package:
                    log.debug(f"Change '{package}' package repository in info '{info['id']}' -> out packageset '{info['out_packageset']['set_id']}'")
                    outpkg["repository"] = repository

    log.debug(f"Write json into '{leapp_pkgs_conf_path}'")
    files.rewrite_json_file(leapp_pkgs_conf_path, pkg_mapping)


# The following types are defined in the leapp-repository repository and can be used
# to define the action type of the package in the pes-events.json file.
class LeappActionType(IntEnum):
    PRESENT = 0
    REMOVED = 1
    DEPRECATED = 2
    REPLACED = 3
    SPLIT = 4
    MERGED = 5
    MOVED = 6
    RENAMED = 7


def set_package_action(package: str, actionType: LeappActionType, leapp_pkgs_conf_path: str = LEAPP_PKGS_CONF_PATH):
    pkg_mapping = None
    log.debug(f"Reconfigure action for package '{package}' to type '{actionType}'")
    with open(leapp_pkgs_conf_path, "r") as pkg_mapping_file:
        pkg_mapping = json.load(pkg_mapping_file)
        for info in pkg_mapping["packageinfo"]:
            if not info["in_packageset"] or not info["in_packageset"]["package"]:
                continue

            for inpackage in info["in_packageset"]["package"]:
                if inpackage["name"] == package:
                    log.debug(f"Change '{package}' package action in info '{info['id']}' -> out packageset '{info['in_packageset']['set_id']}'")
                    info["action"] = actionType

    log.debug(f"Write json into '{leapp_pkgs_conf_path}'")
    files.rewrite_json_file(leapp_pkgs_conf_path, pkg_mapping)
