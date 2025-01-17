# Copyright 2023-2025. WebPros International GmbH. All rights reserved.
import re
import typing


def create_replace_string_function(old: str, new: str) -> typing.Callable[[str], str]:
    """
    Create a function that replaces occurrences of old with new in a string.

    :param old: The value to be replaced.
    :param new: The value to replace with.
    :return: A function that takes a string and returns it with replacements made.
    """
    def inner(line: str) -> str:
        return line.replace(old, new)
    return inner


def create_replace_regexp_function(pattern: str, repl: str) -> typing.Callable[[str], str]:
    def inner(line: str) -> str:
        return re.sub(pattern, repl, line)
    return inner
