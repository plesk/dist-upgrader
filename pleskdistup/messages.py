# Copyright 1999-2023. Plesk International GmbH. All rights reserved.

CONVERT_RESTART_MESSAGE = """
\033[92m**************************************************************************************
The dist-upgrade process needs to reboot the server. It will be rebooted in several seconds.
The process will resume automatically after the reboot.
Current server time: {time}.
To monitor the disupgrade status use one of the following commands:
    {util_path} --status
or
    {util_path} --monitor
**************************************************************************************\033[0m
"""

FINISH_RESTART_MESSAGE = """
\033[92m**************************************************************************************
The dist-upgrade process has finished. The server will now reboot.
**************************************************************************************\033[0m
"""

REVERT_FINISHED_MESSAGE = """
\033[92m**************************************************************************************
All changes have been reverted. Plesk should now return to normal operation.
**************************************************************************************\033[0m
"""

FAIL_MESSAGE_HEAD = """
\033[91m**************************************************************************************
The dist-upgrade process has failed. Here are the last 100 lines of the {logfile_path} file:
**************************************************************************************\033[0m
"""

FAIL_MESSAGE_TAIL = """
\033[91m**************************************************************************************
The dist-ugrade process has failed. See the {logfile_path} file for more information.
The last 100 lines of the file are shown above.
For assistance, call '{util_name} --prepare-feedback' and follow the instructions.
**************************************************************************************\033[0m
"""

TIME_EXCEEDED_MESSAGE = """
\033[91m**************************************************************************************
The dist-upgrade process is taking too long. It may be stuck. Please verify if the process is
still running by checking if logfile {logfile_path} continues to update.
It is safe to interrupt the process with Ctrl+C and restart it from the same stage.
**************************************************************************************\033[0m
"""

FEEDBACK_IS_READY_MESSAGE = """
\033[92m**************************************************************************************
The feedback archive is ready. You can find it here: {feedback_archive_path}
For further assistance, create an issue in our GitHub repository - {issues_url}.
Please attach the feedback archive to the created issue and provide as much information about the problem as you can.
**************************************************************************************\033[0m
"""

NOT_SUPPORTED_ERROR = "Your distribution is not supported yet, please contact Plesk support for further assistance."
