# Copyright 2023-2025. WebPros International GmbH. All rights reserved.

from pleskdistup.common import action, log, rpm

import os
import urllib.request
import typing


class FetchGPGKeyForLeapp(action.ActiveAction):
    """This action fetches the GPG key from a specific repositories for leapp.
    Usually leapp brings all required GPG keys with it inside specific configuration directory.
    But since Plesk bring its own repositories which are not supported by AlmaLinux,
    we need to fetch the GPG key manually to make
    sure leapp will be able to proceed with the conversion when packages from repository installed.
    """
    target_repository_files_regex: typing.List[str] = []

    leapp_gpg_keys_store: str = "/etc/leapp/files/vendors.d/rpm-gpg"

    def __init__(self):
        if not hasattr(self, 'name') or self.name is None:
            self.name = "fetching GPG key for leapp"

        try:
            self.target_gpg_keys = rpm.collect_all_gpgkeys_from_repofiles("/etc/yum.repos.d", self.target_repository_files_regex)
        except Exception as e:
            raise RuntimeError(f"Unable to collect GPG keys from repository files: {e}") from e

    def _get_leapp_gpg_key_store(self, key_url: str) -> str:
        return os.path.join(self.leapp_gpg_keys_store, key_url.split('/')[-1])

    def _is_gpg_key_missing_in_leapp_configuration(self) -> bool:
        return any(
            not os.path.exists(self._get_leapp_gpg_key_store(key_url))
            for key_url in self.target_gpg_keys
        )

    def _is_required(self) -> bool:
        return len(self.target_gpg_keys) != 0 and self._is_gpg_key_missing_in_leapp_configuration()

    def _prepare_action(self) -> action.ActionResult:
        for key_url in self.target_gpg_keys:
            gpg_key_target_path = self._get_leapp_gpg_key_store(key_url)
            log.debug(f"Going to save GPG key from {key_url!r} to {gpg_key_target_path!r}")
            if os.path.exists(gpg_key_target_path):
                continue

            try:
                with urllib.request.urlopen(key_url, timeout=10) as response:
                    with open(gpg_key_target_path, 'wb') as out_file:
                        out_file.write(response.read())
            except Exception as e:
                log.err(f"Error occurred while fetching GPG key from '{key_url}': {e}")
                raise RuntimeError(
                    f"Unable to fetch GPG key from '{key_url}': {e}. To continue with the conversion,"
                    f"please manually install the key into {self.leapp_gpg_keys_store!r}."
                ) from e

        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        # Since it's part of leapp configuration, it is fine to keep the key in the store.
        # Because it will be removed anyway during other steps of the revert process.
        return action.ActionResult()
