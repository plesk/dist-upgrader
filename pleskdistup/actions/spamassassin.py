# Copyright 2023-2024. WebPros International GmbH. All rights reserved.
import os
import shutil
import typing

from pleskdistup.common import action, dist, packages, motd, rpm, systemd, util

SPAMASSASIN_CONFIG_PATH = "/etc/mail/spamassassin/init.pre"


class RestoreCurrentSpamassasinConfiguration(action.ActiveAction):
    state_dir: str
    spamassasin_config_path: str
    spamassasin_backup_path: str

    def __init__(self, state_dir: str) -> None:
        self.state_dir = state_dir
        self.name = "restore current spamassassin configuration after conversion"
        self.spamassasin_config_path = "/etc/spamassassin/local.cf"
        self.spamassasin_backup_path = os.path.join(self.state_dir, "spamassasin_local.cf.backup")

    def _is_required(self) -> bool:
        return os.path.exists(self.spamassasin_config_path)

    def _prepare_action(self) -> action.ActionResult:
        shutil.copy(self.spamassasin_config_path, self.spamassasin_backup_path)
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        shutil.copy(self.spamassasin_backup_path, self.spamassasin_config_path)
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        os.unlink(self.spamassasin_backup_path)
        return action.ActionResult()


class HandleUpdatedSpamassassinConfig(action.ActiveAction):
    spamassasin_service_name: str

    # Make sure the trick is preformed before any call of 'systemctl daemon-reload'
    # because we change spamassassin.service configuration in scope of this action.
    def __init__(self) -> None:
        self.name = "handle spamassassin configuration update"
        self.spamassasin_service_name = "spamassassin.service"

    def _is_required(self) -> bool:
        return packages.is_package_installed("psa-spamassassin")

    def _prepare_action(self) -> action.ActionResult:
        util.logged_check_call(["/usr/bin/systemctl", "stop", self.spamassasin_service_name])
        util.logged_check_call(["/usr/bin/systemctl", "disable", self.spamassasin_service_name])
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        util.logged_check_call(["/usr/sbin/plesk", "sbin", "spammng", "--enable"])
        util.logged_check_call(["/usr/sbin/plesk", "sbin", "spammng", "--update", "--enable-server-configs", "--enable-user-configs"])

        util.logged_check_call(["/usr/bin/systemctl", "daemon-reload"])
        # There might be an issue if spamassassin.service is disabled. However, we still need to reconfigure
        # spamassassin, so we should not skip the action, but simply avoid enabling the service.
        if systemd.is_service_startable(self.spamassasin_service_name):
            util.logged_check_call(["/usr/bin/systemctl", "enable", self.spamassasin_service_name])

        # TODO. Following action is not supported on deb-based system. Actually it will be just skipped.
        # So if you are going to use the action on deb-based, you should be ready there will be no .rpmnew
        # things or even file here (obviously).
        if dist.get_distro().rhel_based:
            if rpm.handle_rpmnew(SPAMASSASIN_CONFIG_PATH):
                motd.add_finish_ssh_login_message(
                    f"Note that spamassasin configuration '{SPAMASSASIN_CONFIG_PATH}' was changed during conversion. "
                    f"Original configuration can be found in {SPAMASSASIN_CONFIG_PATH}.rpmsave."
                )

        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        util.logged_check_call(["/usr/bin/systemctl", "enable", self.spamassasin_service_name])
        util.logged_check_call(["/usr/bin/systemctl", "start", self.spamassasin_service_name])
        return action.ActionResult()


class AssertSpamassassinAdditionalPluginsDisabled(action.CheckAction):
    supported_plugins: typing.List[str]

    def __init__(self) -> None:
        self.name = "check spamassassin additional plugins are disabled"
        self.description = """There are additional plugins enabled in spamassassin configuration:
\t- {}

They will not be available after the conversion. Please disable them manually or use --disable-spamassasin-plugins option to force script to remove them automatically.
"""
        self.supported_plugins = [
            "Mail::SpamAssassin::Plugin::URIDNSBL",
            "Mail::SpamAssassin::Plugin::Hashcash",
            "Mail::SpamAssassin::Plugin::SPF",
        ]

    def _do_check(self) -> bool:
        if not os.path.exists(SPAMASSASIN_CONFIG_PATH):
            return True

        unsupported_plugins = []
        with open(SPAMASSASIN_CONFIG_PATH, "r") as fp:
            for loadline in [line for line in fp.readlines() if line.startswith("loadplugin")]:
                plugin = loadline.rstrip().split(' ')[1]
                if plugin not in self.supported_plugins:
                    unsupported_plugins.append(plugin)

        if not unsupported_plugins:
            return True

        self.description = self.description.format("\n\t- ".join(unsupported_plugins))
        return False
