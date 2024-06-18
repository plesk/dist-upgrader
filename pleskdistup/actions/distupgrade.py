# Copyright 2023-2024. WebPros International GmbH. All rights reserved.

import os
import re
import shutil
import subprocess

from pleskdistup.common import action, dpkg, files, log, packages, util


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


class SetupAptRepositories(action.ActiveAction):
    system_type: str
    from_codename: str
    from_version: str
    to_codename: str
    to_version: str
    sources_list_path: str
    sources_list_d_path: str
    _name: str
    _sources_backup_suffix: str = ".pleskdistup-old"

    def __init__(
        self,
        system_type: str,
        from_codename: str,
        from_version: str,
        to_codename: str,
        to_version: str,
        sources_list_path: str = "/etc/apt/sources.list",
        sources_list_d_path: str = "/etc/apt/sources.list.d/",
        name: str = "set up APT repositories to upgrade from {self.from_system!r} to {self.to_system!r}",
    ):
        self.system_type = system_type
        self.from_codename = from_codename
        self.from_version = from_version
        self.to_codename = to_codename
        self.to_version = to_version
        self.sources_list_path = sources_list_path
        self.sources_list_d_path = sources_list_d_path

        self._name = name

    @property
    def name(self) -> str:
        return self._name.format(self=self)

    @name.setter
    def name(self, value) -> None:
        self._name = value

    @property
    def from_system(self) -> str:
        res = f"{self.system_type}"
        if self.from_version:
            res += f" {self.from_version}"
        if self.from_codename:
            res += f" ({self.from_codename})"
        return res

    @property
    def to_system(self) -> str:
        res = f"{self.system_type}"
        if self.to_version:
            res += f" {self.to_version}"
        if self.from_codename:
            res += f" ({self.to_codename})"
        return res

    def _change_sources_in_file(
        self,
        path: str,
        system_type: str,
        from_codename: str,
        from_version: str,
        to_codename: str,
        to_version: str,
    ):
        def escape_backslash(s):
            return s.replace("\\", "\\\\")

        log.debug(f"Replacing APT sources in {path!r}")
        subs_src = [
            (f"(https://packages.microsoft.com/{re.escape(system_type.lower())}/){re.escape(from_version)}/", f"\\g<1>{escape_backslash(to_version)}/"),
            (f"\\b{re.escape(from_codename)}\\b", escape_backslash(to_codename))
        ]
        subs = [(re.compile(item[0]), item[1]) for item in subs_src]
        with open(path, "r") as origf, open(path + ".next", "w") as nextf:
            for line in origf:
                sline = line.strip()
                if not sline or sline[0] == "#":
                    log.debug(f"Skipped comment {line}")
                    continue
                log.debug(f"Processing line: {line!r}")
                for sub_patt, sub_repl in subs:
                    line, subnum = sub_patt.subn(sub_repl, line)
                    if subnum > 0:
                        log.debug(f"Pattern {sub_patt} matched, new line: {line!r}")
                log.debug(f"Writing line: {line!r}")
                nextf.write(line)

        shutil.move(path, path + self._sources_backup_suffix)
        shutil.move(path + ".next", path)

    def _get_source_list_paths(self, suffix: str = ""):
        if os.path.exists(self.sources_list_path + suffix):
            yield self.sources_list_path + suffix
        for root, _, filenames in os.walk(self.sources_list_d_path):
            for f in filenames:
                if f.endswith(".list" + suffix):
                    yield os.path.join(root, f)

    def _change_sources(
        self,
        system_type: str,
        from_codename: str,
        from_version: str,
        to_codename: str,
        to_version: str,
    ) -> None:
        for f in self._get_source_list_paths():
            self._change_sources_in_file(
                f,
                self.system_type,
                self.from_codename,
                self.from_version,
                self.to_codename,
                self.to_version,
            )

    def _prepare_action(self) -> action.ActionResult:
        self._change_sources(
            self.system_type,
            self.from_codename,
            self.from_version,
            self.to_codename,
            self.to_version,
        )
        packages.update_package_list()
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        for path in self._get_source_list_paths(self._sources_backup_suffix):
            if path[-len(self._sources_backup_suffix):] == self._sources_backup_suffix:
                newpath = path[:-len(self._sources_backup_suffix)]
                if newpath:
                    shutil.move(path, newpath)
        packages.update_package_list()
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 20

    def estimate_revert_time(self) -> int:
        return 20


class SetupDebianRepositories(SetupAptRepositories):
    def __init__(self, *args, **kwargs):
        super().__init__("Debian", *args, **kwargs)


class SetupUbuntuRepositories(SetupAptRepositories):
    def __init__(self, *args, **kwargs):
        super().__init__("Ubuntu", *args, **kwargs)


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
