# Copyright 2023-2024. WebPros International GmbH. All rights reserved.
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
