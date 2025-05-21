# Copyright 2023-2025. WebPros International GmbH. All rights reserved.
import os
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


def upgrade_packages(
    pkgs: typing.Optional[typing.List[str]] = None,
    allow_downgrade: bool = False,
) -> None:
    started_on = dist.get_distro()
    if started_on.deb_based:
        return dpkg.upgrade_packages(pkgs, allow_downgrade=allow_downgrade)
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


def handle_configuration_files_conflict(configuration_file_path: str) -> typing.Optional[str]:
    """
    Make sure that configuration file from the new package will be used
    and the old one will be saved in distro specific backup format.
    :param configuration_file_path: path to the configuration file
    :return: path to the preserved configuration file
    """
    started_on = dist.get_distro()

    old_suffix: str = ""
    new_suffix: str = ""
    if started_on.rhel_based:
        old_suffix = ".rpmsave"
        new_suffix = ".rpmnew"
    elif started_on.deb_based:
        old_suffix = ".dpkg-old"
        new_suffix = ".dpkg-dist"
    else:
        raise NotImplementedError(f"Unsupported distro {started_on}")

    # If there are no configuration files we do not need to do anything
    if not os.path.exists(configuration_file_path + old_suffix) and not os.path.exists(configuration_file_path + new_suffix):
        return None

    # When there is old_suffix file we actually do not need to do anything
    # because package manager already did everything for us
    # But when there is new_suffix file we need to handle it
    if os.path.exists(configuration_file_path + new_suffix):
        if started_on.deb_based:
            dpkg.handle_dpkg_dist(configuration_file_path)
        elif started_on.rhel_based:
            rpm.handle_rpmnew(configuration_file_path)

    return configuration_file_path + old_suffix


def get_repositories_urls(repofile: str) -> typing.Set[str]:
    """
    Get the list of repository URLs
    :return: list of repository URLs
    """
    started_on = dist.get_distro()
    if started_on.deb_based:
        return dpkg.get_repositories_urls(repofile)
    elif started_on.rhel_based:
        return rpm.get_repositories_urls(repofile)
    else:
        raise NotImplementedError(f"Unsupported distro {started_on}")


def get_repository_metafile_url(repository_url: str) -> str:
    """
    Get the repository metafile URL from the given repository URL.
    """
    started_on = dist.get_distro()
    if started_on.deb_based:
        return dpkg.get_repository_metafile_url(repository_url)
    elif started_on.rhel_based:
        return rpm.get_repository_metafile_url(repository_url)
    else:
        raise NotImplementedError(f"Unsupported distro {started_on}")
