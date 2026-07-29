# Copyright 2023-2026. WebPros International GmbH. All rights reserved.

from pleskdistup.common import action, files, rpm, util

import glob
import os
import shutil
import subprocess
import typing


class LeappInstallation(action.ActiveAction):
    """Install a fixed set of leapp packages from the ELevate repository.

    Every RHEL-family conversion needs the same thing: add the elevate-release
    repository, install a pinned set of leapp packages from it, and remove all of
    it again once the conversion is over (or reverted). Only the elevate-release
    RPM URL, the repository id and the list of pinned packages differ between
    conversions, so they are constructor arguments.

    The packages installed are pinned on purpose, and the repository is disabled
    right after the installation, so nothing can silently upgrade leapp to a
    version we did not test the conversion with.

    Cleanup relies on the 'leapp_packages_glob' pattern rather than on
    'pkgs_to_install', so leftovers from a previous conversion are removed as
    well. A conversion that pins a package not matching the pattern should
    override 'leapp_packages_glob'.
    """

    pkgs_to_install: typing.List[str]
    elevate_release_rpm_url: str
    elevate_repo_id: str
    remove_logs_on_finish: bool

    leapp_packages_glob: str = "*leapp*"
    leapp_related_files: typing.List[str] = [
        "/root/tmp_leapp_py3/leapp",
    ]
    leapp_related_directories: typing.List[str] = [
        "/etc/leapp",
        "/var/lib/leapp",
    ]
    # Depending on the conversion leapp is installed for python 2 or python 3,
    # so we can't rely on a fixed site-packages location here.
    leapp_python_site_packages_glob: str = "/usr/lib/python*/site-packages/leapp"
    leapp_logs_directory: str = "/var/log/leapp"

    def __init__(
        self,
        elevate_release_rpm_url: str,
        pkgs_to_install: typing.List[str],
        elevate_repo_id: str = "elevate",
        remove_logs_on_finish: bool = False,
        name: str = "installing leapp",
    ):
        self.name = name
        self.elevate_release_rpm_url = elevate_release_rpm_url
        self.pkgs_to_install = pkgs_to_install
        self.elevate_repo_id = elevate_repo_id
        self.remove_logs_on_finish = remove_logs_on_finish

    def _get_installed_leapp_packages(self) -> typing.List[str]:
        try:
            return [name for name, _ in rpm.get_installed_packages_list(self.leapp_packages_glob)]
        except subprocess.CalledProcessError:
            # 'rpm -qa <glob>' behaviour on a glob matching nothing is not consistent
            # between rpm versions, so treat a query failure as 'nothing is installed'.
            return []

    def _remove_leapp_packages(self, also_remove: typing.Optional[typing.List[str]] = None) -> None:
        pkgs_to_remove = set(self._get_installed_leapp_packages())
        pkgs_to_remove |= set(rpm.filter_installed_packages(also_remove if also_remove else []))
        rpm.remove_packages(sorted(pkgs_to_remove))

    def _remove_previous_installation(self) -> None:
        # Remove leapp packages installed before, either by a previous run of the
        # converter or by a previous conversion, to make sure we will install the
        # versions we expect.
        # In previous version of converters we do not remove some leapp packages
        # after conversion finished, so we have to make sure everything cleaned here.
        self._remove_leapp_packages()

        # The directory contains leapp-data package configurations, which causes problems with
        # the package installation. So we have to remove it, to reinstall package from scratch.
        for system_upgrade_link in files.find_files_case_insensitive("/etc/leapp/repos.d", "system_upgrade*"):
            os.unlink(system_upgrade_link)

    def _remove_installation(self, include_logs: bool) -> None:
        self._remove_leapp_packages(also_remove=["elevate-release"])

        for file in self.leapp_related_files:
            if os.path.exists(file):
                os.unlink(file)

        leapp_related_directories = list(self.leapp_related_directories)
        leapp_related_directories += glob.glob(self.leapp_python_site_packages_glob)
        if include_logs:
            leapp_related_directories.append(self.leapp_logs_directory)

        for directory in leapp_related_directories:
            if os.path.exists(directory):
                shutil.rmtree(directory)

    def _prepare_action(self) -> action.ActionResult:
        self._remove_previous_installation()

        if not rpm.is_package_installed("elevate-release"):
            util.logged_check_call(["/usr/bin/yum", "install", "-y", self.elevate_release_rpm_url])

        util.logged_check_call(["/usr/bin/yum-config-manager", "--enable", self.elevate_repo_id])

        rpm.install_packages(self.pkgs_to_install)
        # We want to prevent the leapp packages from being updated accidentally to
        # the latest version (for example by using 'yum update -y'). Therefore, we
        # should disable the elevate repository. Additionally, this will prevent
        # the pre-checker from detecting leapp as outdated and prevent re-evaluation
        # on the next restart.
        util.logged_check_call(["/usr/bin/yum-config-manager", "--disable", self.elevate_repo_id])
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        self._remove_installation(include_logs=self.remove_logs_on_finish)
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        # Logs of a conversion we've reverted could be useful to understand why
        # it was reverted, so keep them in place.
        self._remove_installation(include_logs=False)
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 40


class RemoveLeappReposDisablement(action.ActiveAction):
    def __init__(self):
        self.name = "remove leapp installation yum.conf inhibitors"

    def _is_required(self) -> bool:
        return bool(rpm.yum_conf_get_exclude_list())

    def _prepare_action(self) -> action.ActionResult:
        files.backup_file(rpm.YUM_CONF_PATH)
        rpm.yum_conf_rm_leapp_disablement()
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        # We need to get rid of leapp repo entries in 'exclude=' in order
        # to enable leapp packages installations in the next OS conversion.
        # These are possibly added during leapp upgrade step to prevent
        # unnecessary leapp upgrades
        rpm.yum_conf_rm_leapp_disablement()
        files.remove_backup(rpm.YUM_CONF_PATH, raise_exception=False)
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        files.restore_file_from_backup(rpm.YUM_CONF_PATH)
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 1
