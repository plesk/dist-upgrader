# Copyright 2023-2024. WebPros International GmbH. All rights reserved.
import unittest

import src.mariadb as mariadb


class MariaDBVersionsTests(unittest.TestCase):
    def test_parse_simple(self):
        php = mariadb.MariaDBVersion("10.6.12")
        self.assertEqual(php.major, 10)
        self.assertEqual(php.minor, 6)
        self.assertEqual(php.patch, 12)

    def test_parse_utility_output(self):
        php = mariadb.MariaDBVersion("mysql  Ver 15.1 Distrib 10.6.12-MariaDB, for debian-linux-gnu (x86_64) using  EditLine wrapper")
        self.assertEqual(php.major, 10)
        self.assertEqual(php.minor, 6)
        self.assertEqual(php.patch, 12)

    def test_parse_wrong_string(self):
        with self.assertRaises(ValueError):
            mariadb.MariaDBVersion("nothing")

    def test_compare_equal(self):
        maria_ver1 = mariadb.MariaDBVersion("10.6.12")
        maria_ver2 = mariadb.MariaDBVersion("10.6.12")
        self.assertEqual(maria_ver1, maria_ver2)

    def test_compare_less_minor(self):
        maria_ver1 = mariadb.MariaDBVersion("10.2.4")
        maria_ver2 = mariadb.MariaDBVersion("10.3.4")
        self.assertLess(maria_ver1, maria_ver2)

    def test_compare_less_major(self):
        maria_ver1 = mariadb.MariaDBVersion("8.2.4")
        maria_ver2 = mariadb.MariaDBVersion("9.2.4")
        self.assertLess(maria_ver1, maria_ver2)

    def test_compare_less_patch(self):
        maria_ver1 = mariadb.MariaDBVersion("10.3.3")
        maria_ver2 = mariadb.MariaDBVersion("10.3.4")
        self.assertLess(maria_ver1, maria_ver2)

    def test_compare_less_major_exponent(self):
        maria_ver1 = mariadb.MariaDBVersion("8.2.4")
        maria_ver2 = mariadb.MariaDBVersion("10.2.4")
        self.assertLess(maria_ver1, maria_ver2)

    def test_compare_less_major_and_minor(self):
        maria_ver1 = mariadb.MariaDBVersion("8.2.2")
        maria_ver2 = mariadb.MariaDBVersion("9.3.4")
        self.assertLess(maria_ver1, maria_ver2)

    def test_compare_less_major_greater_minor_patch(self):
        maria_ver1 = mariadb.MariaDBVersion("5.2.2")
        maria_ver2 = mariadb.MariaDBVersion("6.1.1")
        self.assertLess(maria_ver1, maria_ver2)
