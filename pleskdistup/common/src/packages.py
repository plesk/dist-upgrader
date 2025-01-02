# Copyright 2023-2025. WebPros International GmbH. All rights reserved.
import typing

from . import dist, dpkg, rpm


def filter_installed_packages(lookup_pkgs: typing.Iterable[str]) -> typing.List[str]:
    return [pkg for pkg in lookup_pkgs if is_package_installed(pkg)]


def is_package_installed(pkg: str) -> bool:
    started_on = dist.get_distro()
    if started_on.deb_based:
        return dpkg.is_package_installed(pkg)
    elif started_on.rhel_based:
        return rpm.is_package_installed(pkg)
    else:
        raise NotImplementedError(f"Unsupported distro {started_on}")


def install_packages(pkgs: typing.List[str], repository: typing.Optional[str] = None, force_package_config: bool = False) -> None:
    started_on = dist.get_distro()
    if started_on.deb_based:
        dpkg.install_packages(pkgs, repository, force_package_config)
    elif started_on.rhel_based:
        rpm.install_packages(pkgs, repository, force_package_config)
    else:
        raise NotImplementedError(f"Unsupported distro {started_on}")


def remove_packages(pkgs: typing.List[str]) -> None:
    started_on = dist.get_distro()
    if started_on.deb_based:
        dpkg.remove_packages(pkgs)
    elif started_on.rhel_based:
        rpm.remove_packages(pkgs)
    else:
        raise NotImplementedError(f"Unsupported distro {started_on}")


def find_related_repofiles(repofiles_mask: str) -> typing.List[str]:
    started_on = dist.get_distro()
    if started_on.deb_based:
        return dpkg.find_related_repofiles(repofiles_mask)
    elif started_on.rhel_based:
        return rpm.find_related_repofiles(repofiles_mask)
    else:
        raise NotImplementedError(f"Unsupported distro {started_on}")


def update_package_list() -> None:
    started_on = dist.get_distro()
    if started_on.deb_based:
        return dpkg.update_package_list()
    elif started_on.rhel_based:
        return rpm.update_package_list()
    else:
        raise NotImplementedError(f"Unsupported distro {started_on}")


def upgrade_packages(pkgs: typing.Optional[typing.List[str]] = None) -> None:
    started_on = dist.get_distro()
    if started_on.deb_based:
        return dpkg.upgrade_packages(pkgs)
    elif started_on.rhel_based:
        return rpm.upgrade_packages(pkgs)
    else:
        raise NotImplementedError(f"Unsupported distro {started_on}")


def autoremove_outdated_packages() -> None:
    started_on = dist.get_distro()
    if started_on.deb_based:
        return dpkg.autoremove_outdated_packages()
    elif started_on.rhel_based:
        return rpm.autoremove_outdated_packages()
    else:
        raise NotImplementedError(f"Unsupported distro {started_on}")


def get_installed_packages_list(regex: str) -> typing.List[typing.Tuple[str, str]]:
    started_on = dist.get_distro()
    if started_on.deb_based:
        return dpkg.get_installed_packages_list(regex)
    elif started_on.rhel_based:
        return rpm.get_installed_packages_list(regex)
    else:
        raise NotImplementedError(f"Unsupported distro {started_on}")
