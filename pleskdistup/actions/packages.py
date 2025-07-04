# Copyright 2023-2025. WebPros International GmbH. All rights reserved.

import os
import subprocess
import typing

from pleskdistup.common import action, dpkg, packages


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
        if not packages.is_package_available(self.package_name):
            return False
        return True
