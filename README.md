# The tool to dist-upgrade servers with Plesk

## Introduction
This utility is the official tool to dist-upgrade servers with Plesk on Debian and Ubuntu.

> [!NOTE]
> This repository only contains framework code which can't be used by itself without an upgrader module suitable for your system.
> Check the following repositories for versions of this tool endowed with upgrader modules for particular systems:
> - [Dist-upgrade Ubuntu 18 to 20](https://github.com/plesk/ubuntu18to20)
> - [Dist-upgrade Ubuntu 20 to 22](https://github.com/plesk/ubuntu20to22)
> - [Dist-upgrade Debian 11 to 12](https://github.com/plesk/debian11to12)

General information about Plesk dist-upgrade tool and its default behavior follows. Please see the documentation of specific tools like ubuntu18to20 for details pertaining to particular systems.

### Upgrader modules
This utility supports multiple upgrader modules performing particular variants of dist-upgrade (e.g. a module for Ubuntu 18 to 20 upgrade, a module for Debian 11 to 12, etc.). The module suitable for your system is selected automatically from available modules.

### Conversion phases
The conversion process consists of two phases:
1. The "convert" phase contains preparation and upgrading actions.
2. The "finish" phase is the last phase containing all finishing actions.

During each phase a conversion plan consisting of stages, which in turn consist of actions, is executed. You can see the general stages in the `--help` output and the detailed plan in the `--show-plan` output.

## Using the utility
To monitor the conversion process, we recommend using the ['screen' utility](https://www.gnu.org/software/screen/) to run the utility in the background. To do so, run the following command:
```shell
> screen -S dist-upgrader
> ./dist-upgrader
```
If you lose your SSH connection to the server, you can reconnect to the screen session by running the following command:
```shell
> screen -r dist-upgrader
```

You can also call dist-upgrader in the background:
```shell
> ./dist-upgrader &
```

And monitor its status with the '--status' or '--monitor' flags:
```shell
> ./dist-upgrader --status
> ./dist-upgrader --monitor
... live monitor session ...
```

Depending on the OS, the conversion process requires 2-3 reboots. It will be resumed automatically after reboot by the `plesk-dist-upgrader` systemd service. In addition to `--status` and `--monitor`, you can check the status of the conversion process by running the following command:
```shell
> systemctl status plesk-dist-upgrader
... live monitor session ...
```

Running dist-upgrader without any arguments initiates the conversion process. The utility performs preliminary checks, and if any issues are detected, it provides descriptions of the problems along with guidance on how to resolve them.
Following the preliminary checks, the tool proceeds with the dist-upgrade process, which is divided into multiple stages. Some stages end with a reboot. You can check the list of stages and steps by `./dist-upgrader --show-plan`.
When dist-upgrade is finished, you will see the following login message:
```
===============================================================================
Message from the Plesk dist-upgrader tool:
The server has been upgraded to <new OS>.
You can remove this message from the /etc/motd file.
===============================================================================
```

### Logs
If something goes wrong, read the logs to identify the problem.
The dist-upgrader writes its log to the `/var/log/plesk/dist-upgrader.log` file, as well as to stdout.
After the first reboot, the process is resumed by the `plesk-dist-upgrader` service, so its output is available in system logs (see `systemctl status plesk-dist-upgrader` and `journalctl -u plesk-dist-upgrader`).

### Revert
If the utility fails during the the "convert" stage before actual dist-upgrade of packages, you can use the dist-upgrader utility with the `-r` or `--revert` options to restore Plesk to normal operation. The dist-upgrader will undo some of the changes it made and restart Plesk services. Once you have resolved the root cause of the failure, you can attempt the conversion again.
Note:
- You cannot use revert to undo the changes after the dist-upgrade of packages, because packages provided by the new OS version are already installed.
- `--revert` mode is not perfect, it can fail or be unable to restore the initial state of the system. So, the importance of creating full server backup or snapshot before starting dist-upgrade can't be stressed enough.

### Checking the status of the conversion process and monitoring its progress
To check the status of the conversion process, use the `--status` option. You can see the current stage of the conversion process, the elapsed time, and the estimated time until finish.
```shell
> ./dist-upgrader --status
```

To monitor the progress of the conversion process in real time, use the `--monitor` option.
```shell
> ./dist-upgrader --monitor
( stage 3 / action re-installing plesk components  ) 02:26 / 06:18
```

## Issue handling
If for some reason the process has failed, inspect the log. By default, it's put to `/var/log/plesk/dist-upgrader.log`. If the process was interrupted before the first reboot, you can restart it with the `--resume` option. If the problem has happened after the first reboot, you can restart the process by running `systemctl restart plesk-dist-upgrader`.

If something goes wrong, you will be informed on the next login with this message:
```
===============================================================================
Message from Plesk dist-upgrader tool:
Something went wrong during dist-upgrade by dist-upgrader.
See the /var/log/plesk/dist-upgrader.log file for more information.
You can remove this message from the /etc/motd file.
===============================================================================
```

### Send feedback
If you got any error, please contact developers of the particular dist-upgrade tool you used (the link for issues should be in --help). Describe your problem and attach the feedback archive or at least the log to the issue. The feedback archive can be created by calling the tool with the `--prepare-feedback` option:
```shell
> ./dist-upgrader --prepare-feedback
```

If you are sure that it's some dist-upgrader framework problem, not an upgrader module problem, please create an issue in this repository and provide the same information.
