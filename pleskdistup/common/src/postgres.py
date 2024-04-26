# Copyright 1999 - 2024. Plesk International GmbH. All rights reserved.
import os
import subprocess

_PATH_TO_PSQL_UTIL = '/usr/bin/psql'


def is_postgres_installed() -> bool:
    return os.path.exists(get_phsql_root_path()) and os.path.exists(_PATH_TO_PSQL_UTIL)


def get_postgres_major_version() -> int:
    version_out = subprocess.check_output([_PATH_TO_PSQL_UTIL, '--version'], universal_newlines=True)
    return int(version_out.split(' ')[2].split('.')[0])


def get_phsql_root_path() -> str:
    return '/var/lib/pgsql'


def get_data_path() -> str:
    return os.path.join(get_phsql_root_path(), 'data')


def get_saved_data_path() -> str:
    return os.path.join(get_phsql_root_path(), 'data-old')


def is_database_initialized() -> bool:
    return os.path.exists(os.path.join(get_data_path(), "PG_VERSION"))


def is_database_major_version_lower(version: int) -> bool:
    version_file_path = os.path.join(get_data_path(), "PG_VERSION")

    if not os.path.exists(version_file_path):
        raise Exception('There is no "' + version_file_path + '" file')

    with open(version_file_path, 'r') as version_file:
        pg_version = int(version_file.readline().split('.')[0])
        if pg_version < version:
            return True
    return False
