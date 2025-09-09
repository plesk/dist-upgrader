# Copyright 2023-2025. WebPros International GmbH. All rights reserved.
from collections import defaultdict
import ipaddress
import itertools
import os
import re
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
            enabled: typing.Optional[str] = None,
            gpgcheck: typing.Optional[str] = None,
            gpgkeys: typing.Optional[typing.List[str]] = None,
            additional: typing.Optional[typing.List[str]] = None
    ):
        self.id = id
        self.name = name
        self.url = url
        self.metalink = metalink
        self.mirrorlist = mirrorlist
        self.enabled = enabled
        self.gpgcheck = gpgcheck
        self.gpgkeys = gpgkeys
        self.additional = [] if additional is None else additional

    def __str__(self) -> str:
        return f"Repository(id={self.id}, name={self.name}, url={self.url}, metalink={self.metalink}, mirrorlist={self.mirrorlist}, enabled={self.enabled}, gpgcheck={self.gpgcheck}, gpgkeys={self.gpgkeys} additional={self.additional})"

    def __repr__(self) -> str:
        content = REPO_HEAD.format(id=self.id, name=self.name)

        if self.url is not None:
            content += f"baseurl={self.url}\n"
        if self.metalink is not None:
            content += f"metalink={self.metalink}\n"
        if self.mirrorlist is not None:
            content += f"mirrorlist={self.mirrorlist}\n"

        if self.enabled is not None:
            content += f"enabled={self.enabled}\n"

        if self.gpgcheck is not None:
            content += f"gpgcheck={self.gpgcheck}\n"

        if self.gpgkeys is not None:
            content += "gpgkey=" + "\n       ".join(self.gpgkeys) + "\n"

        for add_line in self.additional:
            content += add_line

        return content

    @classmethod
    def from_lines(cls, lines: typing.List[str]) -> 'Repository':
        known_fields: typing.List[str] = ["name", "baseurl", "metalink", "mirrorlist", "enabled", "gpgcheck", "gpgkey"]
        additional: typing.List[str] = []

        if not lines[0].startswith("["):
            raise ValueError("Repository ID is missing in the provided lines")

        id: str = lines[0].rstrip()[1:-1]

        parsed_lines: typing.Dict[str, str] = defaultdict(None)
        current_key: typing.Optional[str] = None

        for line in lines[1:]:
            # just skip commentaries and add them somewhere at the end
            if line.strip().startswith("#"):
                additional.append(line)
                continue

            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip().rstrip()
                value = value.strip().rstrip()
                if key in known_fields:
                    parsed_lines[key] = value
                    current_key = key
                else:
                    # We do not intend to remove or add '\n' for additional lines
                    # and likely we prefer to simply copy them, not change.
                    # Hence, I am not using strip for this task.
                    additional.append(line)
                    current_key = None
            elif current_key is not None:
                parsed_lines[current_key] += "\n" + line.rstrip()
            else:
                additional.append(line)

        return cls(
            id,
            name=parsed_lines.get("name"),
            url=parsed_lines.get("baseurl"),
            metalink=parsed_lines.get("metalink"),
            mirrorlist=parsed_lines.get("mirrorlist"),
            enabled=parsed_lines.get("enabled"),
            gpgcheck=parsed_lines.get("gpgcheck"),
            # Configuration variable is "gpgkey", function parameter is "gpgkeys".
            # It's not a typo. We can have several GPG keys, so it's array.
            gpgkeys=util.multi_split(parsed_lines.get("gpgkey", ""), ["\n", " ", "\t"], remove_empty=True) if "gpgkey" in parsed_lines else None,
            additional=additional,
        )


def extract_repodata(
    repofile: str
) -> typing.Iterable[Repository]:

    if not os.path.exists(repofile):
        raise FileNotFoundError(f"The repository file {repofile!r} does not exist")

    repository_lines: typing.List[str] = []

    with open(repofile, "r") as repo:
        for line in repo.readlines():
            if line.startswith("["):
                if len(repository_lines):
                    log.debug("Previous repository ended. Create object from lines")
                    yield Repository.from_lines(repository_lines)

                log.debug("Start repository: {line}".format(line=line.rstrip()))
                repository_lines = [line]
                continue

            log.debug("Repository file line: {line}".format(line=line.rstrip()))
            if len(repository_lines) == 0:
                log.debug("Skip line outside of repository")
                continue

            repository_lines.append(line)

    if len(repository_lines) == 0:
        return

    yield Repository.from_lines(repository_lines)


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


def find_all_repofiles(sources_dir: str = "/etc/yum.repos.d/") -> typing.List[str]:
    return files.find_files_case_insensitive(sources_dir, "*.repo")


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


def collect_all_gpgkeys_from_repofiles(
        path: str,
        regexps_strings: typing.Union[typing.List, str],
) -> typing.List[str]:
    gpg_keys = []
    for repofile in files.find_files_case_insensitive(path, regexps_strings):
        for repo in extract_repodata(repofile):
            if repo.gpgkeys is not None:
                gpg_keys += [key.strip().rstrip() for key in repo.gpgkeys]

    return gpg_keys


def get_repositories_urls(repofile: str) -> typing.Set[str]:
    if not os.path.exists(repofile):
        return set()

    urls = set()
    for repo in extract_repodata(repofile):
        if repo.url is not None:
            urls.add(repo.url)
        if repo.metalink is not None:
            urls.add(repo.metalink)
        if repo.mirrorlist is not None:
            urls.add(repo.mirrorlist)
    return urls


def get_repository_metafile_url(repository_url: str) -> str:
    """
    Get the repository metafile URL from the given repository URL.
    """
    return repository_url.rstrip("/") + "/repodata/repomd.xml"


def extract_gpgkey_from_rpm_database(
        summary_regexp: str,
        destination: str,
        from_file: typing.Optional[str] = None
) -> bool:
    """
    Extracts first GPG key from the RPM database based on the summary regular expression and saves it to the destination file.

    :param summary_regexp: Regular expression to match the summary of the GPG key package.
    :param destination: Path to the file where the GPG key will be saved.
    """
    rpm_gpg_keys_info = []

    if from_file is not None:
        if os.path.exists(from_file):
            with open(from_file, "r") as src_file:
                rpm_gpg_keys_info = src_file.readlines()
    else:
        rpm_gpg_keys_info = subprocess.check_output(
            ["/usr/bin/rpm", "-qi", "gpg-pubkey"],
            universal_newlines=True
        ).splitlines()

    match_found = False
    in_key_block = False
    with open(destination, "w") as dst_file:
        for line in rpm_gpg_keys_info:
            try:
                if line.startswith("Summary") and re.search(summary_regexp, line):
                    match_found = True
                    continue
            except re.error as e:
                raise Exception(f"Invalid regular expression for GPG key extraction: {summary_regexp}") from e

            if match_found:
                if "-----BEGIN PGP PUBLIC KEY BLOCK-----" in line:
                    in_key_block = True

                if in_key_block:
                    dst_file.write(line + "\n")
                    if "-----END PGP PUBLIC KEY BLOCK-----" in line:
                        in_key_block = False
                        return True

                if line.startswith("Name"):
                    match_found = False

    os.remove(destination)
    return False


def is_package_available(package_name: str) -> bool:
    """
    Check if the package is available in enabled repositories.
    :param package_name: name of the package to check
    :return: True if the package is available, False otherwise
    """
    cmd = ["/usr/bin/yum", "list", "available", package_name]
    res = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )

    # If the command returns 0, the package is available.
    # If it returns 1, the package is not available.
    # If it returns any other code, it means there was an error in yum itself.
    if res.returncode != 0 and res.returncode != 1:
        log.debug(
            f"Command '{' '.join(cmd)}' failed with return code {res.returncode}. stdout: {res.stdout}, stderr: {res.stderr}"
        )

    return res.returncode == 0


def disable_repo_if(repofile: str, condition: typing.Callable[[Repository], bool]) -> typing.List[str]:
    """
    Disable repositories in a repo file if they match the given condition.
    :param repofile: path to the repository file
    :param condition: callable that takes a repository object and returns True if it should be disabled
    :return: list of repository IDs that were disabled
    """
    if not os.path.exists(repofile):
        return []

    disabled_repos = []
    with open(repofile + ".next", "w") as dst:
        for repo in extract_repodata(repofile):
            if condition(repo):
                repo.enabled = "0"
                disabled_repos.append(repo.id)

            dst.write(repr(repo))

    if os.path.exists(repofile + ".next"):
        shutil.move(repofile + ".next", repofile)

    return disabled_repos


def prohibit_package_from_repository(package: str, repository: str) -> None:
    # Was not required so far. Potentially could be implemented via exclude directive in repo file.
    raise NotImplementedError("Package lock is not supported for rpm-based distros yet")


def allow_package_from_repository(package: str, repository: str) -> None:
    raise NotImplementedError("Package lock is not supported for rpm-based distros yet")


def is_repository_url_enabled(repository_url: str, sources_dir: str = "/etc/yum.repos.d/") -> bool:
    """
    Check if the given repository URL is enabled in any of the repository files.
    :param repository_url: URL of the repository
    :return: True if the repository is enabled, False otherwise
    """
    for repofile in find_all_repofiles(sources_dir=sources_dir):
        for repo in extract_repodata(repofile):
            if any(repository_url in (link or "") for link in (repo.url, repo.metalink, repo.mirrorlist)) and repo.enabled == "1":
                return True

    return False
