# Copyright 2023-2025. WebPros International GmbH. All rights reserved.
import typing
import unittest

import src.php as php
import src.version as version


class TestGetHandlers(unittest.TestCase):
    def test_one(self):
        self.assertEqual(
            sorted(php.get_php_handlers([version.PHPVersion("8.0")])),
            [
                "plesk-php80-cgi",
                "plesk-php80-fastcgi",
                "plesk-php80-fpm",
                "plesk-php80-fpm-dedicated"
            ]
        )

    def test_several_versions(self):
        self.assertEqual(
            sorted(php.get_php_handlers([version.PHPVersion("7.3"), version.PHPVersion("8.0")])),
            [
                "plesk-php73-cgi",
                "plesk-php73-fastcgi",
                "plesk-php73-fpm",
                "plesk-php73-fpm-dedicated",
                "plesk-php80-cgi",
                "plesk-php80-fastcgi",
                "plesk-php80-fpm",
                "plesk-php80-fpm-dedicated"
            ]
        )

    def test_empty(self):
        self.assertEqual(
            php.get_php_handlers([]),
            []
        )


class TestGetOutdatedHandlers(unittest.TestCase):
    def test_version_7_1(self):
        self.assertEqual(
            sorted(php.get_outdated_php_handlers(version.PHPVersion("7.1"))),
            [
                "plesk-php52-cgi",
                "plesk-php52-fastcgi",
                "plesk-php52-fpm",
                "plesk-php52-fpm-dedicated",
                "plesk-php53-cgi",
                "plesk-php53-fastcgi",
                "plesk-php53-fpm",
                "plesk-php53-fpm-dedicated",
                "plesk-php54-cgi",
                "plesk-php54-fastcgi",
                "plesk-php54-fpm",
                "plesk-php54-fpm-dedicated",
                "plesk-php55-cgi",
                "plesk-php55-fastcgi",
                "plesk-php55-fpm",
                "plesk-php55-fpm-dedicated",
                "plesk-php56-cgi",
                "plesk-php56-fastcgi",
                "plesk-php56-fpm",
                "plesk-php56-fpm-dedicated",
                "plesk-php70-cgi",
                "plesk-php70-fastcgi",
                "plesk-php70-fpm",
                "plesk-php70-fpm-dedicated",
            ]
        )

    def test_no_outdated(self):
        self.assertEqual(
            php.get_outdated_php_handlers(version.PHPVersion("5.0")),
            []
        )


class TestGetHandlersByCondition(unittest.TestCase):
    handlers_lower_than_7_1: typing.List[str] = [
        "plesk-php52-cgi",
        "plesk-php52-fastcgi",
        "plesk-php52-fpm",
        "plesk-php52-fpm-dedicated",
        "plesk-php53-cgi",
        "plesk-php53-fastcgi",
        "plesk-php53-fpm",
        "plesk-php53-fpm-dedicated",
        "plesk-php54-cgi",
        "plesk-php54-fastcgi",
        "plesk-php54-fpm",
        "plesk-php54-fpm-dedicated",
        "plesk-php55-cgi",
        "plesk-php55-fastcgi",
        "plesk-php55-fpm",
        "plesk-php55-fpm-dedicated",
        "plesk-php56-cgi",
        "plesk-php56-fastcgi",
        "plesk-php56-fpm",
        "plesk-php56-fpm-dedicated",
        "plesk-php70-cgi",
        "plesk-php70-fastcgi",
        "plesk-php70-fpm",
        "plesk-php70-fpm-dedicated"
    ]

    def test_lower_than_version_7_1(self):
        self.assertListEqual(
            sorted(php.get_php_handlers_by_condition(lambda php: php < version.PHPVersion("7.1"))),
            self.handlers_lower_than_7_1
        )

    def test_not_in_list(self):
        target_versions = [php for php in php.get_known_php_versions() if php >= version.PHPVersion("7.1")]
        self.assertListEqual(
            sorted(php.get_php_handlers_by_condition(lambda php: php not in target_versions)),
            self.handlers_lower_than_7_1
        )

    def test_not_in_complex_list(self):
        target_versions = [version.PHPVersion("5.6")] + [php for php in php.get_known_php_versions() if php >= version.PHPVersion("7.1")]
        self.assertListEqual(
            sorted(php.get_php_handlers_by_condition(lambda php: php not in target_versions)),
            [
                "plesk-php52-cgi",
                "plesk-php52-fastcgi",
                "plesk-php52-fpm",
                "plesk-php52-fpm-dedicated",
                "plesk-php53-cgi",
                "plesk-php53-fastcgi",
                "plesk-php53-fpm",
                "plesk-php53-fpm-dedicated",
                "plesk-php54-cgi",
                "plesk-php54-fastcgi",
                "plesk-php54-fpm",
                "plesk-php54-fpm-dedicated",
                "plesk-php55-cgi",
                "plesk-php55-fastcgi",
                "plesk-php55-fpm",
                "plesk-php55-fpm-dedicated",
                "plesk-php70-cgi",
                "plesk-php70-fastcgi",
                "plesk-php70-fpm",
                "plesk-php70-fpm-dedicated",
            ]
        )


class TestGetPHPCondition(unittest.TestCase):
    def test_get_version_lower(self):
        self.assertListEqual(
                sorted(php.get_php_versions_by_condition(lambda php: php < version.PHPVersion("7.1"))),
                [
                    version.PHPVersion("5.2"),
                    version.PHPVersion("5.3"),
                    version.PHPVersion("5.4"),
                    version.PHPVersion("5.5"),
                    version.PHPVersion("5.6"),
                    version.PHPVersion("7.0"),
                ]
        )

    def test_get_only_7(self):
        self.assertListEqual(
                sorted(php.get_php_versions_by_condition(lambda php: php.major == 7)),
                [
                    version.PHPVersion("7.0"),
                    version.PHPVersion("7.1"),
                    version.PHPVersion("7.2"),
                    version.PHPVersion("7.3"),
                    version.PHPVersion("7.4"),
                ]
        )
