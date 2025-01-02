# Copyright 2023-2025. WebPros International GmbH. All rights reserved.
import typing

from . import version


def get_known_php_versions() -> typing.List[version.PHPVersion]:
    # TODO: get rid of the explicit version list
    return [
        version.PHPVersion(ver) for ver in (
            "5.2", "5.3", "5.4", "5.5", "5.6",
            "7.0", "7.1", "7.2", "7.3", "7.4",
            "8.0", "8.1", "8.2", "8.3",
        )
    ]


def get_php_handlers(php_versions: typing.List[version.PHPVersion]) -> typing.List[str]:
    php_handlers = {"{}-cgi", "{}-fastcgi", "{}-fpm", "{}-fpm-dedicated"}
    return [handler.format(f"plesk-php{php.major}{php.minor}") for php in php_versions for handler in php_handlers]


def get_outdated_php_handlers(first_modern: version.PHPVersion) -> typing.List[str]:
    return get_php_handlers([php for php in get_known_php_versions() if php < first_modern])


def get_php_handlers_by_condition(condition: typing.Callable[[version.PHPVersion], bool]) -> typing.List[str]:
    return get_php_handlers([php for php in get_known_php_versions() if condition(php)])


def get_php_versions_by_condition(condition: typing.Callable[[version.PHPVersion], bool]) -> typing.List[version.PHPVersion]:
    return [php for php in get_known_php_versions() if condition(php)]
