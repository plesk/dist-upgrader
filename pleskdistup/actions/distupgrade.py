# Copyright 2023-2024. WebPros International GmbH. All rights reserved.
import os
import re
import subprocess
import typing
import urllib.request
import xml.etree.ElementTree as ElementTree

from pleskdistup.common import action, dist, dpkg, files, log, packages, plesk, util


class InstallUbuntuUpdateManager(action.ActiveAction):
    def __init__(self):
        self.name = "install Ubuntu update manager"

    def _prepare_action(self) -> action.ActionResult:
        packages.install_packages(["update-manager-core"])
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 10


class SetupUbuntu20Repositories(action.ActiveAction):
    def __init__(self):
        self.name = "set up Ubuntu 20 repositories"
        self.plesk_sourcelist_path = "/etc/apt/sources.list.d/plesk.list"

    def _prepare_action(self) -> action.ActionResult:
        files.replace_string("/etc/apt/sources.list", "bionic", "focal")

        for root, _, file in os.walk("/etc/apt/sources.list.d/"):
            for f in file:
                if f.endswith(".list"):
                    files.replace_string(os.path.join(root, f), "bionic", "focal")

        files.backup_file(self.plesk_sourcelist_path)
        files.replace_string(self.plesk_sourcelist_path, "extras", "all")

        packages.update_package_list()
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        files.restore_file_from_backup(self.plesk_sourcelist_path)
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        files.restore_file_from_backup(self.plesk_sourcelist_path)
        files.replace_string("/etc/apt/sources.list", "focal", "bionic")

        for root, _, file in os.walk("/etc/apt/sources.list.d/"):
            for f in file:
                if f.endswith(".list"):
                    files.replace_string(os.path.join(root, f), "focal", "bionic")

        packages.update_package_list()
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 20

    def estimate_revert_time(self) -> int:
        return 0


class UpdateLegacyPhpRepositories(action.ActiveAction):
    legacy_php_versions_inf3_urls: typing.List[str]
    from_os: dist.Distro
    to_os: dist.Distro
    sources_list_d_path: str

    def __init__(
        self,
        from_os: dist.Distro,
        to_os: dist.Distro,
        sources_list_d_path: str = "/etc/apt/sources.list.d/",
    ):
        self.name = "update legacy PHP repositories"
        self.legacy_php_versions_inf3_urls = [
            "https://autoinstall.plesk.com/php{}.inf3".format(version) for version in [71, 72, 73]
        ]
        self.from_os = from_os
        self.to_os = to_os
        self.sources_list_d_path = sources_list_d_path

    def _retrieve_php_version_repositories_mapping(self, url: str, from_os: dist.Distro, to_os: dist.Distro) -> typing.Dict[str, str]:
        try:
            response = urllib.request.urlopen(url)
            xml_content = response.read().decode('utf-8')
            log.debug(f"Retrieved PHP version repositories mapping from {url!r}. Content: {xml_content}")
            root = ElementTree.fromstring(xml_content)

            to_repo = plesk.get_repository_by_os_from_inf3(root, to_os)
            from_repo = plesk.get_repository_by_os_from_inf3(root, from_os)
            if to_repo and from_repo:
                return {from_repo: to_repo}
        except urllib.error.URLError as ex:
            log.warn(f"Unable to download {url!r}: {ex}")
        except ElementTree.ParseError as ex:
            log.warn(f"Unable to parse inf3 file from {url!r}: {ex}")
        except Exception as ex:
            log.warn(f"Unable to retrieve PHP version repositories mapping from {url!r}: {ex}")

        return {}

    def _prepare_action(self) -> action.ActionResult:
        mappings = {}
        for url in self.legacy_php_versions_inf3_urls:
            mappings.update(self._retrieve_php_version_repositories_mapping(url, self.from_os, self.to_os))

        for list_file in files.find_files_case_insensitive(self.sources_list_d_path, "*.list", True):
            if not files.backup_exists(list_file):
                files.backup_file(list_file)

            for from_repo, target_repo in mappings.items():
                log.debug(f"Replacing {from_repo!r} with {target_repo!r} in {list_file!r}")
                files.replace_string(list_file, from_repo, target_repo)

        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        # Source lists backups are not relevant after the upgrade, so we can remove them from any
        # action that uses them.
        for list_file in files.find_files_case_insensitive(self.sources_list_d_path, "*.list", True):
            files.remove_backup(list_file)

        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        for list_file in files.find_files_case_insensitive(self.sources_list_d_path, "*.list", True):
            files.restore_file_from_backup(list_file)

        packages.update_package_list()
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 20

    def estimate_revert_time(self) -> int:
        return 20


class CheckAptReposBackups(action.CheckAction):
    description: str
    _name: str
    sources_list_path: str
    sources_list_d_path: str

    @staticmethod
    def get_all_repo_list_files(sources_list_path: str, sources_list_d_path: str) -> typing.List[str]:
        ret = [sources_list_path]
        for root, _, filenames in os.walk(sources_list_d_path):
            for f in filenames:
                if f.endswith(".list"):
                    ret.append(os.path.join(root, f))
        return ret

    def __init__(self,
        sources_list_path: str = "/etc/apt/sources.list",
        sources_list_d_path: str = "/etc/apt/sources.list.d/",
    ) -> None:
        self._name = "Check repo.list leftovers from previous conversion"
        self.description = "These repo.list files are found with backups, please check/restore them, and delete the backups: {}"
        self.sources_list_path = sources_list_path
        self.sources_list_d_path = sources_list_d_path

    @property
    def name(self) -> str:
        return self._name.format(self)

    @name.setter
    def name(self, val: str) -> None:
        self._name = val

    def _do_check(self) -> bool:
        log.debug(f"Checking leftover repo.list files")
        archived_files = [f for f in
            CheckAptReposBackups.get_all_repo_list_files(self.sources_list_path, self.sources_list_d_path)
                if files.backup_exists(f)]
        if archived_files:
            self.description = self.description.format(",".join(archived_files))
            return False
        return True


class ReplaceAptReposRegexp(action.ActiveAction):
    from_regexp: str
    to_regexp: str
    sources_list_path: str
    sources_list_d_path: str
    _name: str

    def __init__(
        self,
        from_regexp: str,
        to_regexp: str,
        sources_list_path: str = "/etc/apt/sources.list",
        sources_list_d_path: str = "/etc/apt/sources.list.d/",
        name: str = "set up APT repositories to change from {self.from_regexp!r} to {self.to_regexp!r}",
    ) -> None:
        self.from_regexp = from_regexp
        self.to_regexp = to_regexp
        self.sources_list_path = sources_list_path
        self.sources_list_d_path = sources_list_d_path

        self._name = name

    @property
    def name(self) -> str:
        return self._name.format(self=self)

    @name.setter
    def name(self, val: str) -> None:
        self._name = val

    def _apply_replace_to_file(self, fpath: str, ptrn: re.Pattern, to_regexp: str) -> None:
        changed = False
        new_lines = []
        with open(fpath) as f:
            for line in f:
                new_lines.append(ptrn.sub(to_regexp, line))
                if new_lines[-1] != line:
                    changed = True
        if not changed:
            return
        files.backup_file(fpath)
        with open(fpath, 'w') as f:
            f.writelines(new_lines)

    def _get_all_repo_list_files(self) -> typing.List[str]:
        return CheckAptReposBackups.get_all_repo_list_files(self.sources_list_path,
                    self.sources_list_d_path)

    def _rm_backups(self) -> None:
        for f in self._get_all_repo_list_files():
            files.remove_backup(f, False, log.debug)

    def _change_by_regexp(self, from_regexp: str, to_regexp: str) -> None:
        p = re.compile(from_regexp)
        for f in self._get_all_repo_list_files():
            self._apply_replace_to_file(f, p, to_regexp)

    def _revert_all(self) -> None:
        for f in self._get_all_repo_list_files():
            files.restore_file_from_backup(f)

    def _prepare_action(self) -> action.ActionResult:
        self._change_by_regexp(self.from_regexp, self.to_regexp)
        packages.update_package_list()
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        self._rm_backups()
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        self._revert_all()
        packages.update_package_list()
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 22

    def estimate_revert_time(self) -> int:
        return 22


ReplaceAptReposRegexpDebian = ReplaceAptReposRegexp
ReplaceAptReposRegexpUbuntu = ReplaceAptReposRegexp


class SetupAptRepositories(action.ActiveAction):
    from_codename: str
    to_codename: str
    sources_list_path: str
    sources_list_d_path: str
    _name: str

    def __init__(
        self,
        from_codename: str,
        to_codename: str,
        sources_list_path: str = "/etc/apt/sources.list",
        sources_list_d_path: str = "/etc/apt/sources.list.d/",
        name: str = "set up APT repositories to upgrade from {self.from_codename!r} to {self.to_codename!r}",
    ):
        self.from_codename = from_codename
        self.to_codename = to_codename
        self.sources_list_path = sources_list_path
        self.sources_list_d_path = sources_list_d_path

        self._name = name

    @property
    def name(self):
        return self._name.format(self=self)

    def _change_sources_codename(self, from_codename: str, to_codename: str) -> None:
        files.replace_string(self.sources_list_path, from_codename, to_codename)

        for root, _, filenames in os.walk(self.sources_list_d_path):
            for f in filenames:
                if f.endswith(".list"):
                    files.replace_string(os.path.join(root, f), from_codename, to_codename)

    def _prepare_action(self) -> action.ActionResult:
        self._change_sources_codename(self.from_codename, self.to_codename)
        packages.update_package_list()
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        self._change_sources_codename(self.to_codename, self.from_codename)
        packages.update_package_list()
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 20

    def estimate_revert_time(self) -> int:
        return 20


SetupDebianRepositories = SetupAptRepositories
SetupUbuntuRepositories = SetupAptRepositories


class InstallNextKernelVersion(action.ActiveAction):
    def __init__(self):
        self.name = "install kernel from next OS version"

    def _prepare_action(self) -> action.ActionResult:
        packages.install_packages(["linux-generic"])
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 2 * 60 + 30


class InstallUdev(action.ActiveAction):
    def __init__(self):
        self.name = "install udev"

    def _prepare_action(self) -> action.ActionResult:
        try:
            packages.install_packages(["udev"])
        except Exception:
            udevd_service_path = "/lib/systemd/system/systemd-udevd.service"
            if os.path.exists(udevd_service_path):
                files.replace_string(udevd_service_path,
                                     "ExecReload=udevadm control --reload --timeout 0",
                                     "ExecReload=/bin/udevadm control --reload --timeout 0")

            dpkg.restore_installation()
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 2 * 60 + 30


class RemoveLXD(action.ActiveAction):
    def __init__(self):
        self.name = "remove lxd"

    def _is_required(self) -> bool:
        return packages.is_package_installed("lxd")

    def _prepare_action(self) -> action.ActionResult:
        packages.remove_packages(["lxd", "lxd-client"])
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        packages.install_packages(["lxd", "lxd-client"])
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        packages.install_packages(["lxd", "lxd-client"])
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 30

    def estimate_post_time(self) -> int:
        return 30

    def estimate_revert_time(self) -> int:
        return 30


class UpgradeGrub(action.ActiveAction):
    def __init__(self):
        self.name = "upgrade GRUB from new repositories"

    def _prepare_action(self) -> action.ActionResult:
        try:
            packages.upgrade_packages(["grub-pc"])
        except Exception:
            log.warn("grub-pc require configuration, trying to do it automatically")
            reconfigure_process = subprocess.Popen("/usr/bin/dpkg --configure grub-pc",
                                                   stdin=subprocess.PIPE,
                                                   stdout=subprocess.PIPE,
                                                   stderr=subprocess.PIPE,
                                                   shell=True, universal_newlines=True,
                                                   env={"PATH": os.environ["PATH"], "DEBIAN_FRONTEND": "readline"})
            exmsg = """Unable to reconfigure grub-pc package, plesk perform reconfiguration manually by calling:
1. dpkg --configure grub-pc
2. apt-get install -f"""
            if reconfigure_process is None or reconfigure_process.stdin is None:
                raise RuntimeError(exmsg)
            reconfigure_process.stdin.write("1\n")
            stdout, stderr = reconfigure_process.communicate()

            if reconfigure_process.returncode != 0:
                log.err("Unable to reconfigure grub-pc package automatically.\nstdout: {}\nstderr: {}".format(stdout, stderr))
                raise Exception(exmsg)

            dpkg.restore_installation()
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 5 * 60


class UpgradePackages(action.ActiveAction):
    name: str
    autoremove: bool

    def __init__(
        self,
        name: str = "upgrade packages",
        autoremove: bool = True
    ):
        self.name = name
        self.autoremove = autoremove

    def _prepare_action(self) -> action.ActionResult:
        packages.upgrade_packages()
        if self.autoremove:
            packages.autoremove_outdated_packages()
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 3 * 60


class UpgradePackagesFromNewRepositories(UpgradePackages):
    def __init__(
        self,
        name: str = "upgrade packages from new repositories",
        autoremove: bool = True,
    ):
        super().__init__(name=name, autoremove=autoremove)


class DoDistupgrade(action.ActiveAction):
    def __init__(self):
        self.name = "do dist-upgrade"

    def _prepare_action(self) -> action.ActionResult:
        dpkg.do_distupgrade()
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        packages.autoremove_outdated_packages()
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        # I believe there is no way to revert dist-upgrade
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 10 * 60

    def estimate_post_time(self) -> int:
        return 30

    def estimate_revert_time(self) -> int:
        return 0


class RepairPleskInstallation(action.ActiveAction):
    def __init__(self):
        self.name = "repair Plesk installation"

    def _prepare_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        util.logged_check_call(["/usr/sbin/plesk", "repair", "installation", "-y"])
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()

    def estimate_post_time(self) -> int:
        return 3 * 60
