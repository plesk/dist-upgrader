# Copyright 2023-2024. WebPros International GmbH. All rights reserved.

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
