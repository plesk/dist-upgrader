# Copyright 2023-2025. WebPros International GmbH. All rights reserved.
import os
import json
import shutil
import typing

from enum import IntEnum
from datetime import datetime, timezone

from . import files, log, rpm


PATH_TO_CONFIGFILES = "/etc/leapp/files"
LEAPP_REPOS_FILE_PATH = os.path.join(PATH_TO_CONFIGFILES, "leapp_upgrade_repositories.repo")
LEAPP_MAP_FILE_PATH = os.path.join(PATH_TO_CONFIGFILES, "repomap.csv")
LEAPP_PKGS_CONF_PATH = os.path.join(PATH_TO_CONFIGFILES, "pes-events.json")
LEAPP_VENDORS_DIR_PATH = os.path.join(PATH_TO_CONFIGFILES, "vendors.d")

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


class RepositoryDescription(typing.NamedTuple):
    id: str
    name: str
    url: typing.Optional[str]
    metalink: typing.Optional[str]
    mirrorlist: typing.Optional[str]
    additional_lines: typing.List[str]


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
        lambda to_change: "alma-" + to_change if not to_change.startswith("alma-") else to_change,
    ])


def _do_name_replacement(name: typing.Optional[str]) -> typing.Optional[str]:
    return _do_replacement(name, [
        lambda to_change: "Alma " + to_change if not to_change.startswith("Alma ") else to_change,
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


def _fix_rackspace_epel_repository(to_change: str) -> str:
    # The Rackspace EPEL repository for version 8 has a slightly different path, including 'Everything' in it
    # Additionally, some repositories use '7Server' instead of 7.
    # Therefore, we need to handle these cases specifically.
    if "iad.mirror.rackspace.com/epel/7/" in to_change:
        return to_change.replace("7", "8/Everything")
    if "iad.mirror.rackspace.com/epel/7Server" in to_change:
        return to_change.replace("7Server", "8/Everything")
    return to_change


def _do_url_replacement(url: typing.Optional[str]) -> typing.Optional[str]:
    return _do_replacement(url, [
        _fixup_old_php_urls,
        _fix_rackspace_repository,
        _fix_mariadb_repository,
        _fix_postgresql_official_repository,
        _fix_rackspace_epel_repository,
        lambda to_change: to_change.replace("archives.fedoraproject.org/pub/archive/epel/7", "dl.fedoraproject.org/pub/epel/8/Everything"),
        lambda to_change: to_change.replace("rpm-CentOS-7", "rpm-RedHat-el8"),
        lambda to_change: to_change.replace("CloudLinux-7", "CloudLinux-8"),
        lambda to_change: to_change.replace("cloudlinux/7", "cloudlinux/8"),
        lambda to_change: to_change.replace("epel-7", "epel-8"),
        lambda to_change: to_change.replace("epel/7", "epel/8"),
        lambda to_change: to_change.replace("epel-debug-7", "epel-debug-8"),
        lambda to_change: to_change.replace("epel-source-7", "epel-source-8"),
        lambda to_change: to_change.replace("centos7", "centos8"),
        lambda to_change: to_change.replace("centos/7", "centos/8"),
        lambda to_change: to_change.replace("rhel/7", "rhel/8"),
        lambda to_change: to_change.replace("rhel7", "rhel8"),
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


def _write_repository_adoption(
        repository: RepositoryDescription,
        dst: typing.TextIO,
        keep_id: bool = False
) -> typing.Optional[RepositoryDescription]:
    id = _do_id_replacement(repository.id) if not keep_id else repository.id
    name = _do_name_replacement(repository.name)

    if id is None or name is None:
        log.warn(f"Skip repository '{repository.id}' since it has no next id or next name")
        return None

    if repository.url is not None:
        url = _do_url_replacement(repository.url)
        repo_format = REPO_HEAD_WITH_URL
    elif repository.metalink is not None:
        url = _do_url_replacement(repository.metalink)
        repo_format = REPO_HEAD_WITH_METALINK
    else:
        url = _do_url_replacement(repository.mirrorlist)
        repo_format = REPO_HEAD_WITH_MIRRORLIST
    if url is None:
        log.warn(f"Skip repository '{repository.id}' since it has no baseurl, metalink and mirrorlist")
        return None

    content = repo_format.format(id=id, name=name, url=url)
    for add_line in repository.additional_lines:
        content += _do_common_replacement(add_line)

    dst.write(content)

    if repository.url is not None:
        return RepositoryDescription(id, name, url, None, None, repository.additional_lines)
    elif repository.metalink is not None:
        return RepositoryDescription(id, name, None, url, None, repository.additional_lines)
    else:
        return RepositoryDescription(id, name, None, None, url, repository.additional_lines)


def adopt_repositories(repofile: str, ignore: typing.Optional[typing.List[str]] = None, keep_id: bool = False) -> None:
    if ignore is None:
        ignore = []

    log.debug(f"Adopt repofile '{repofile}'")

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

            _write_repository_adoption(
                RepositoryDescription(id, name, url, metalink, mirrorlist, additional_lines),
                dst, keep_id
            )

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

                after_repository = _write_repository_adoption(
                    RepositoryDescription(id, name, url, metalink, mirrorlist, additional_lines),
                    leapp_repos_file, False
                )
                if after_repository is None:
                    continue

                # Special case for plesk repository. We need to add dist repository to install some of plesk packages
                # We support metalink for plesk repository, regardless of the fact we don't use them now
                if id.startswith("PLESK_18_0") and "extras" in id and url is not None:
                    dist_repository_description = RepositoryDescription(
                        id.replace("-extras", ""),
                        name.replace("extras", ""),
                        url.replace("extras", "dist"),
                        None, None, ["enabled=1\n", "gpgcheck=1\n"]
                    )
                    after_dist_repository = _write_repository_adoption(dist_repository_description, leapp_repos_file, False)
                    if after_dist_repository is not None:
                        map_file.write("{oldrepo},{newrepo},{newrepo},all,all,x86_64,rpm,ga,ga\n".format(oldrepo=id, newrepo=after_dist_repository.id))

                leapp_repos_file.write("\n")

                map_file.write("{oldrepo},{newrepo},{newrepo},all,all,x86_64,rpm,ga,ga\n".format(oldrepo=id, newrepo=after_repository.id))

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


def take_free_packageset_id(pkg_mapping: dict) -> int:
    max_id: int = 0
    if "packageinfo" not in pkg_mapping:
        return 1

    for info in pkg_mapping["packageinfo"]:
        input_set_id = 0
        if "in_packageset" in info and info["in_packageset"] and info["in_packageset"]["set_id"]:
            input_set_id = int(info["in_packageset"]["set_id"])

        output_set_id = 0
        if "out_packageset" in info and info["out_packageset"] and info["out_packageset"]["set_id"]:
            output_set_id = int(info["out_packageset"]["set_id"])

        max_id = max(max_id, input_set_id, output_set_id)

    return max_id + 1


def set_package_mapping(
        in_package: str,
        source_repository: str,
        out_package: str,
        target_repository: str,
        leapp_pkgs_conf_path: str = LEAPP_PKGS_CONF_PATH
) -> None:
    pkg_mapping = None
    log.debug(f"Reconfigure mapping for package {in_package!r} from repository {source_repository!r} to package {out_package!r} from repository {target_repository!r}")
    with open(leapp_pkgs_conf_path, "r") as pkg_mapping_file:
        pkg_mapping = json.load(pkg_mapping_file)
        for info in pkg_mapping["packageinfo"]:
            if not info["in_packageset"] or not info["in_packageset"]["package"]:
                continue

            if all(inpkg["name"] != in_package or inpkg["repository"] != source_repository for inpkg in info["in_packageset"]["package"]):
                continue

            log.debug(f"Change '{in_package}' package repository in info '{info['id']}' -> in packageset '{info['in_packageset']['set_id']}'")
            if "out_packageset" not in info or not info["out_packageset"]:
                info["out_packageset"] = {"set_id": take_free_packageset_id(pkg_mapping), "package": []}
                info["out_packageset"]["package"].append({"name": out_package, "repository": target_repository})
            else:
                info["out_packageset"]["package"] = []
                info["out_packageset"]["package"].append({"name": out_package, "repository": target_repository})

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


def remove_package_action(package: str, repository: str, leapp_pkgs_conf_path: str = LEAPP_PKGS_CONF_PATH):
    log.debug(f"Remove action for package '{package}' from repository '{repository}'")

    def is_action_for_target_package(action: dict) -> bool:
        if "in_packageset" not in action or action["in_packageset"] is None or "package" not in action["in_packageset"]:
            return False
        return any(inpackage["name"] == package and inpackage["repository"] == repository for inpackage in action["in_packageset"]["package"])

    pkg_mapping = None
    with open(leapp_pkgs_conf_path, "r") as pkg_mapping_file:
        pkg_mapping = json.load(pkg_mapping_file)
        if "packageinfo" not in pkg_mapping:
            return

        pkg_mapping["packageinfo"] = [action for action in pkg_mapping["packageinfo"] if not is_action_for_target_package(action)]

    log.debug(f"Write json into '{leapp_pkgs_conf_path}'")
    files.rewrite_json_file(leapp_pkgs_conf_path, pkg_mapping)


def _add_repository_mapping_entry(dst: json, id: str, new_id: str) -> None:
    """
    Add a repository mapping entry to the given JSON object. The JSON object format specified by leapp.
    Format was originally taken from /etc/leapp/files/vendor.d/mariadb_map.json. Leapp version - 0.18.0-2
    On modern leapp versions format might be different.

    Args:
        dst (json): The JSON object to which the mapping entry will be added.
        id (str): The original repository ID.
        new_id (str): The new repository ID to map to.
    """
    dst["mapping"][0]["entries"].append({
        "source": id,
        "target": [new_id],
    })

    orig_repo_description = {
        "pesid": id,
        "entries": [
            {
                "major_version": "7",
                "repoid": id,
                "arch": "x86_64",
                "channel": "ga",
                "repo_type": "rpm"
            }
        ]
    }

    after_repo_description = {
        "pesid": new_id,
        "entries": [
            {
                "major_version": "8",
                "repoid": new_id,
                "arch": "x86_64",
                "channel": "ga",
                "repo_type": "rpm"
            }
        ]
    }

    dst["repositories"].append(orig_repo_description)
    dst["repositories"].append(after_repo_description)


def create_leapp_vendor_repository_adoption(
        repofile: str,
        leapp_vendors_dir: str = LEAPP_VENDORS_DIR_PATH,
        ignore: typing.Optional[typing.List[str]] = None,
        keep_id: bool = False
) -> None:
    """
    Create a repository mapping configuration for leapp in /etc/leapp/files/vendors.d directory.

    Args:
        repofile (str): The path to the repository file to adapt.
        leapp_vendors_dir (str): The path to the leapp vendors directory. Used mostly for testing purposes.
        ignore (typing.Optional[typing.List[str]]): A list of repository IDs to ignore.
        keep_id (bool): If True, the original repository ID will be preserved in the mapping.
    """
    # Since leapp 0.18.0, we can store repository adoptions separately
    # in the vendors.d sub-directory of /etc/leapp/files.
    # Additionally, some repositories are already preconfigured by almalinux developers.
    # Unfortunately, they might not meet our needs, so we need to rewrite them occasionally.
    # Storing repositories in separate configuration files also seems logical,
    # so it is preferable to use this method for modern leapp.
    if ignore is None:
        ignore = []

    if not os.path.exists(repofile):
        log.warn("The repository adapter has tried to open an unexistent file: {filename}".format(filename=repofile))
        return

    if not os.path.exists(leapp_vendors_dir):
        # The new version of leapp may eliminate the vendor directory as there is no stable version yet.
        # This behavior might change, so raising an exception will help identify changes during development.
        raise FileNotFoundError(f"Leapp vendors directory {leapp_vendors_dir!r} does not exist")

    mapping_json = {
        "datetime": datetime.now(timezone.utc).strftime("%Y%m%d%H%MZ"),
        "version_format": "1.2.1",
        "mapping": [
            {
                "source_major_version": "7",
                "target_major_version": "8",
                "entries": [],
            },
        ],
        "repositories": [],
        "provided_data_streams": [
            "1.1",
            "2.0",
            "3.0",
            "3.1"
        ]
    }

    repofile_name: str = os.path.basename(repofile)
    json_file_name: str = repofile_name.split(".")[0] + "_map.json"
    target_repo_file: str = os.path.join(leapp_vendors_dir, repofile_name)
    log.debug(f"Adopt repofile into vendor directory with dst: {repofile!r} and {json_file_name!r}")

    with open(target_repo_file + ".next", "w") as dst:
        for id, name, url, metalink, mirrorlist, additional_lines in rpm.extract_repodata(repofile):
            if id is None:
                log.warn(f"Skip repository from '{repofile}' since it has no id")
                continue

            if id in ignore:
                log.debug("Skip repository '{id}' adaptation since it is in ignore list.".format(id=id))
                continue

            if not is_repo_ok(id, name, url, metalink, mirrorlist):
                continue

            _write_repository_adoption(RepositoryDescription(id, name, url, metalink, mirrorlist, additional_lines), dst, keep_id)
            _add_repository_mapping_entry(mapping_json, id, _do_id_replacement(id) if not keep_id else id)

    if os.path.getsize(target_repo_file + ".next") == 0:
        os.remove(target_repo_file + ".next")
        return

    shutil.move(target_repo_file + ".next", target_repo_file)
    files.rewrite_json_file(os.path.join(leapp_vendors_dir, json_file_name), mapping_json)
