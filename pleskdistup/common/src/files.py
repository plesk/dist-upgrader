# Copyright 2023-2024. WebPros International GmbH. All rights reserved.
import fnmatch
import json
import os
import re
import shutil
import typing

from . import log


PathType = typing.Union[os.PathLike, str]

DEFAULT_BACKUP_EXTENSION = ".conversion.bak"

def replace_string(filename: str, original_substring: str, new_substring: str) -> None:
    with open(filename, "r") as original, open(filename + ".next", "w") as dst:
        for line in original.readlines():
            line = line.replace(original_substring, new_substring)
            dst.write(line)

    shutil.move(filename + ".next", filename)


def append_strings(filename: str, strings: typing.List[str]) -> None:
    next_file = filename + ".next"
    shutil.copy(filename, next_file)

    with open(next_file, "a") as dst:
        for string in strings:
            dst.write(string)

    shutil.move(next_file, filename)


def push_front_strings(filename: str, strings: typing.List[str]) -> None:
    next_file = filename + ".next"

    with open(filename, "r") as original, open(next_file, "w") as dst:
        for string in strings:
            dst.write(string)

        for line in original.readlines():
            dst.write(line)

    shutil.move(next_file, filename)


def rewrite_json_file(filename: str, jobj: typing.Union[dict, typing.List]) -> None:
    log.debug("Going to write json '{file}' with new data".format(file=filename))

    with open(filename + ".next", "w") as dst:
        dst.write(json.dumps(jobj, indent=4))

    shutil.move(filename + ".next", filename)


def get_last_lines(filename: PathType, n: int) -> typing.List[str]:
    with open(filename) as f:
        return f.readlines()[-n:]


def backup_file(filename: str, ext: str = DEFAULT_BACKUP_EXTENSION) -> None:
    if os.path.exists(filename):
        shutil.copy(filename, filename + ext)


def backup_exists(filename: str, ext: str = DEFAULT_BACKUP_EXTENSION) -> bool:
    return os.path.exists(filename + ext)


def restore_file_from_backup(
    filename: str,
    remove_if_no_backup: bool = False,
    ext: str = DEFAULT_BACKUP_EXTENSION,
) -> None:
    if os.path.exists(filename + ext):
        shutil.move(filename + ext, filename)
    elif remove_if_no_backup and os.path.exists(filename):
        os.remove(filename)


def remove_backup(
    filename: str,
    raise_exception: bool = True,
    logf: typing.Optional[typing.Callable[[str], typing.Any]] = None,
    ext: str = DEFAULT_BACKUP_EXTENSION,
) -> None:
    backup_name = filename + ext
    try:
        if os.path.exists(backup_name):
            os.remove(backup_name)
    except Exception as ex:
        if logf is not None:
            logf(f"failed to remove backup ({backup_name}): {ex}")
        if raise_exception:
            raise


def __get_files_recursive(path: str) -> typing.Iterator[str]:
    for root, _, files in os.walk(path):
        for file in files:
            yield os.path.relpath(os.path.join(root, file), path)


def find_files_case_insensitive(path: str, regexps_strings: typing.Union[typing.List, str], recursive: bool = False) -> typing.List[str]:
    # Todo. We should add typing for our functions
    if not isinstance(regexps_strings, list) and not isinstance(regexps_strings, str):
        raise TypeError("find_files_case_insensitive argument regexps_strings must be a list")
    # But string is a common mistake and we can handle it simply
    if isinstance(regexps_strings, str):
        regexps_strings = [regexps_strings]

    if not os.path.exists(path) or not os.path.isdir(path):
        return []

    result = []
    regexps = [re.compile(fnmatch.translate(r), re.IGNORECASE) for r in regexps_strings]
    files_list = __get_files_recursive(path) if recursive else os.listdir(path)

    for file in files_list:
        for regexp in regexps:
            if regexp.match(os.path.basename(file)):
                result.append(os.path.join(path, file))

    return result


def is_directory_empty(path: str) -> bool:
    return not os.path.exists(path) or len(os.listdir(path)) == 0


def find_subdirectory_by(directory: str, functor: typing.Callable[[str], bool]) -> typing.Optional[str]:
    for root, directories, _ in os.walk(directory):
        for subdir in directories:
            fullpath = os.path.join(root, subdir)
            if functor(fullpath):
                return fullpath
    return None


def find_file_substrings(filename: str, substring: str) -> typing.List[str]:
    if not os.path.exists(filename):
        return []

    res = []
    with open(filename, "r") as f:
        for line in f.readlines():
            if substring in line:
                res.append(line)
    return res


def cnf_get_section_variable(filename: str, section: str, variable: str) -> typing.Optional[str]:
    with open(filename, "r") as original:
        in_section = False
        for line in original.readlines():
            sec_match = re.match(r"\s*\[\s*(?P<sec_name>\S+)\s*\]", line)
            if sec_match:
                in_section = sec_match["sec_name"] == section
                continue
            if in_section:
                var_match = re.match(f"\\s*{variable}\\s*=\\s*(?P<value>.*)", line)
                if var_match:
                    return var_match["value"]
    return None


def cnf_set_section_variable(filename: str, section: str, variable: str, value: str) -> None:
    if not os.path.exists(filename):
        return

    with open(filename, "r") as original, open(filename + ".next", "w") as dst:
        section_found = in_section = False
        variable_found = False
        for line in original.readlines():
            sec_match = re.match(r"\s*\[\s*(?P<sec_name>\S+)\s*\]", line)
            if sec_match:
                if in_section:
                    in_section = False
                    if not variable_found:
                        dst.write(f"{variable}={value}\n")
                else:
                    in_section = sec_match["sec_name"] == section
                    section_found = in_section is True

            if in_section and re.match(f"\\s*{variable}\\s*=", line):
                line = f"{variable}={value}\n"
                variable_found = True

            dst.write(line)

        if not section_found:
            dst.write(f"\n[{section}]\n{variable}={value}\n")
        elif in_section and not variable_found:
            dst.write(f"{variable}={value}\n")

    shutil.move(filename + ".next", filename)


def cnf_unset_section_variable(filename: str, section: str, variable: str) -> None:
    if not os.path.exists(filename):
        return

    with open(filename, "r") as original, open(filename + ".next", "w") as dst:
        section_found = False
        for line in original.readlines():
            sec_match = re.match(r"\s*\[\s*(?P<sec_name>\S+)\s*\]", line)
            if sec_match:
                if section_found:
                    section_found = False
                else:
                    section_found = sec_match["sec_name"] == section

            if section_found and re.match(f"\\s*{variable}\\s*=", line):
                continue

            dst.write(line)

    shutil.move(filename + ".next", filename)
