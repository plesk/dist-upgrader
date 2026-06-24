# Copyright 2023-2025. WebPros International GmbH. All rights reserved.

import os
import subprocess
import typing

from pleskdistup.common import action, dpkg, packages, rpm


class AssertPackageIsNotInstalled(action.CheckAction):
    def __init__(self, package_name: str, description: typing.Optional[str] = None):
        self.package_name = package_name
        self.name = f"checking if the '{package_name}' package is installed"
        if description:
            self.description = description
        else:
            self.description = f"The '{package_name}' package is installed. Please remove it to proceed with the conversion."

    def _do_check(self) -> bool:
        return len(packages.get_installed_packages_list(self.package_name)) == 0


class ReinstallSystemd(action.ActiveAction):
    name: str

    def __init__(self, name: str = "reinstalling systemd"):
        self.name = name

    def _prepare_action(self) -> action.ActionResult:
        packages.install_packages(["systemd"])
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 30

    def estimate_post_time(self) -> int:
        return 0

    def estimate_revert_time(self) -> int:
        return 0


class InstallPackages(action.ActiveAction):
    packages_to_install: typing.List[str]
    _name: str
    post_remove: bool
    protected_packages: typing.List[str]

    # protected_packages = None means the default, pass [] to disable
    # protection against removal
    def __init__(
        self,
        packages_to_install: typing.Iterable[str],
        name: str = "installing packages",
        post_remove: bool = False,
        protected_packages: typing.Optional[typing.Iterable[str]] = None,
    ):
        self.packages_to_install = list(packages_to_install)
        self._name = name
        self.post_remove = post_remove
        self.protected_packages = list(protected_packages) if protected_packages is not None else ["plesk-core", "psa", "plesk-web-hosting"]

    @property
    def name(self) -> str:
        return f"{self._name}: {', '.join(self.packages_to_install)}"

    @name.setter
    def name(self, val: str) -> None:
        self._name = val

    def _prepare_action(self) -> action.ActionResult:
        dpkg.safely_install_packages(self.packages_to_install, protected_pkgs=self.protected_packages)
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        if self.post_remove:
            packages.remove_packages(self.packages_to_install)
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        packages.remove_packages(self.packages_to_install)
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 20 * len(self.packages_to_install)

    def estimate_post_time(self) -> int:
        if self.post_remove:
            return self.estimate_revert_time()
        return 0

    def estimate_revert_time(self) -> int:
        return self.estimate_prepare_time()


class RemoveReplacePackages(action.ActiveAction):
    """
    Removes or replaces packages by saving to rollback accordingly
    """
    packmap: typing.Dict[str, str]
    tmpsavepath: str

    def __init__(
        self,
        packmap: typing.Dict[str, str],
        tmpsavepath: str,
        display_name: typing.Optional[str] = None,
    ):
        self.packmap = packmap
        self.tmpsavepath = tmpsavepath
        os.makedirs(os.path.dirname(self.tmpsavepath),
                    exist_ok=True)
        self.name = display_name or f"remove/replace packages {packmap.keys()}"

    def is_required(self) -> bool:
        return bool(packages.filter_installed_packages(
            [k for k in self.packmap.keys()]))

    def _prepare_action(self) -> action.ActionResult:
        if os.path.isfile(self.tmpsavepath):
            return action.ActionResult()

        already_installed = packages.filter_installed_packages(self.packmap.keys())
        with open(self.tmpsavepath, "w") as f:
            f.write("\n".join(already_installed))
        packages.remove_packages(already_installed)
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        if os.path.isfile(self.tmpsavepath):
            with open(self.tmpsavepath) as f:
                rpm.install_packages(
                    [self.packmap[dep] for dep in f.read().splitlines() if self.packmap[dep]]
                )
        os.unlink(self.tmpsavepath)
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        if os.path.isfile(self.tmpsavepath):
            with open(self.tmpsavepath) as f:
                rpm.install_packages(f.read().splitlines())
            os.unlink(self.tmpsavepath)
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 10

    def estimate_post_time(self) -> int:
        return 1

    def estimate_revert_time(self) -> int:
        return 10


class TemporaryRemovePackage(action.ActiveAction):
    """
    Temporarily removes a package during the prepare phase and reinstalls it
    during the post phase (finish) and revert phase (rollback).
    """
    package_name: str

    def __init__(
        self,
        package_name: str,
        name: typing.Optional[str] = None,
    ):
        self.package_name = package_name
        self.name = name or f"temporarily removing {package_name}"

    def _is_required(self) -> bool:
        return packages.is_package_installed(self.package_name)

    def _prepare_action(self) -> action.ActionResult:
        packages.remove_packages([self.package_name])
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        packages.install_packages([self.package_name])
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        packages.install_packages([self.package_name])
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 10

    def estimate_post_time(self) -> int:
        return 20

    def estimate_revert_time(self) -> int:
        return 20


class AssertRepositorySubstitutionAvailable(action.CheckAction):
    """
    Check if the repository substitution is available.
    """

    def __init__(
        self,
        target_repository_file: str,
        substitution_rule: typing.Callable[[str], str],
        name: str = "asserting repository substitution available",
        description_addition: str = "",
    ):
        self.name = name
        self.description = "Target platform repository '{}' is not available."
        self.target_repository_file = target_repository_file
        self.substitution_rule = substitution_rule
        self.description_addition = description_addition

    def _do_check(self) -> bool:
        # We don't care if there is not such repository
        if not os.path.exists(self.target_repository_file):
            return True

        for url in packages.get_repositories_urls(self.target_repository_file):
            metafile_url = packages.get_repository_metafile_url(url)
            next_metafile_url = self.substitution_rule(metafile_url)
            result = subprocess.run(["curl", "-s", "-o", "/dev/null", "-f", next_metafile_url], check=False)
            if result.returncode != 0:
                self.description = self.description.format(url) + "\n" + self.description_addition
                return False

        return True


class AssertPackageAvailable(action.CheckAction):
    """
    Check if the package is available in the target repository.
    """

    def __init__(self, package_name: str, name: str = "asserting package available", recommendation: str = ""):
        self.name = name
        self.package_name = package_name
        self.description = f"Package '{package_name}' is not available."
        if recommendation:
            self.description += f" {recommendation}"

    def _do_check(self) -> bool:
        if not packages.is_package_available(self.package_name) and not packages.is_package_installed(self.package_name):
            return False
        return True


class AssertNoLibodbcFromMicrosoftRepository(action.CheckAction):
    name: str = "asserting no libodbc from microsoft repository"
    package_name: str = "libodbc1"
    microsoft_repo_url: str = "packages.microsoft.com"

    def __init__(self):
        self.description = f"""Package '{self.package_name}' from the Microsoft repository should be removed due
\tto a conflict with the Ubuntu 22 system package 'libodbc2'
\tTo proceed with distupgrade re-install {self.package_name} from the official Ubuntu repositories by calling:
\t- apt-get install libodbc1=2.3.6-0.1ubuntu0.1
"""

    def _do_check(self) -> bool:
        # The Microsoft package version 2.3.11-1 is the source of the conflict, as it includes the libodbc.so.2 file,
        # which clashes with the same file provided by the libodbc2 package on Ubuntu 22.
        # Interestingly, the libodbc1 package from the Ubuntu 22 Microsoft repository does not include libodbc.so.2,
        # making it compatible. However, its version is lower than 2.3.11-1, so it won't be selected during a dist-upgrade.
        return not (packages.is_package_installed(self.package_name) and
                    packages.is_repository_url_enabled(self.microsoft_repo_url) and
                    "2.3.11-1" == packages.get_package_installed_version(self.package_name))


class ProhibitLibodbcFromMicrosoftRepository(action.ActiveAction):
    name: str = "prohibiting libodbc from microsoft repository"
    suspicious_packages: typing.List[str] = ["libodbc1", "idbcinst", "odbcinst1debian2"]
    microsoft_repo_url: str = "packages.microsoft.com"

    def _is_required(self):
        return any(packages.is_package_installed(pkg) for pkg in self.suspicious_packages) and packages.is_repository_url_enabled(self.microsoft_repo_url)

    def _prepare_action(self) -> action.ActionResult:
        for pkg in self.suspicious_packages:
            packages.prohibit_package_from_repository(pkg, self.microsoft_repo_url)
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        for pkg in self.suspicious_packages:
            packages.allow_package_from_repository(pkg, self.microsoft_repo_url)
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        for pkg in self.suspicious_packages:
            packages.allow_package_from_repository(pkg, self.microsoft_repo_url)
        return action.ActionResult()

    def estimate_prepare_time(self) -> int:
        return 5

    def estimate_post_time(self) -> int:
        return 5

    def estimate_revert_time(self) -> int:
        return 5


class RemovePackagesOnFinish(action.ActiveAction):
    """
    Removes packages during the finishing stage of the conversion.
    This action does nothing during prepare phase and removes specified
    packages during the post phase (after OS upgrade and reboot).
    """
    packages_to_remove: typing.List[str]
    _name: str

    def __init__(
        self,
        packages_to_remove: typing.Iterable[str],
        name: str = "removing packages on finish",
    ):
        self.packages_to_remove = list(packages_to_remove)
        self._name = name

    @property
    def name(self) -> str:
        return self._name.format(self=self)

    @name.setter
    def name(self, val: str) -> None:
        self._name = val

    def _prepare_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        packages.remove_packages([package for package in self.packages_to_remove if packages.is_package_installed(package)])
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        return action.ActionResult()

    def estimate_post_time(self) -> int:
        return 5 * len(self.packages_to_remove)
