# Copyright 2023-2024. WebPros International GmbH. All rights reserved.

import os
import typing

from pleskdistup.common import action, systemd


class AddUpgradeSystemdService(action.ActiveAction):
    util_path: str
    options: typing.Any
    service_name: str
    _state_dir: str
    _name: str
    _service_file_path: str
    _service_content: str

    def __init__(
        self,
        util_path: str,
        options: typing.Any,
        name: str = "add the service {self.service_name!r} to resume Plesk dist-upgrade after reboot",
        service_name: str = "plesk-dist-upgrade-resume.service",
    ):
        self.util_path = util_path
        self.options = options
        self.service_name = service_name

        self._state_dir = options.state_dir
        self._name = name
        self._service_file_path = os.path.join("/etc/systemd/system", self.service_name)
        self._service_content = """
[Unit]
Description=Resume Plesk dist-upgrade after reboot
After=network.target network-online.target

[Service]
Type=simple
# want to run it once per boot time
RemainAfterExit=yes
ExecStart={util_path} --state-dir "{state_dir}" --resume {arguments}

[Install]
WantedBy=multi-user.target
"""

    @property
    def name(self):
        return self._name.format(self=self)

    @property
    def _service_arguments(self) -> typing.List[str]:
        args = []
        if self.options.verbose:
            args.append("--verbose")
        if self.options.log_file:
            args.append(f'--log-file "{self.options.log_file}"')
        return args

    def _prepare_action(self) -> action.ActionResult:
        systemd.add_systemd_service(
            self.service_name,
            self._service_content.format(
                util_path=self.util_path,
                state_dir=self._state_dir,
                arguments=" ".join(self._service_arguments)
            ),
        )
        return action.ActionResult()

    def _post_action(self) -> action.ActionResult:
        systemd.remove_systemd_service(self.service_name)
        return action.ActionResult()

    def _revert_action(self) -> action.ActionResult:
        systemd.remove_systemd_service(self.service_name)
        return action.ActionResult()
