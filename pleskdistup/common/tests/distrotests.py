# Copyright 2023-2024. WebPros International GmbH. All rights reserved.
import unittest

import src.dist as dist


class TestDistro(unittest.TestCase):
    def test_str(self):
        obj = dist.Debian("10")
        self.assertEqual(str(obj), "Debian 10")

    def test_debian(self):
        obj = dist.Debian("10")
        self.assertTrue(obj.deb_based)
        self.assertFalse(obj.rhel_based)
        self.assertEqual(obj.name, "Debian")
        self.assertEqual(obj.version, "10")

    def test_ubuntu(self):
        obj = dist.Ubuntu("18")
        self.assertTrue(obj.deb_based)
        self.assertFalse(obj.rhel_based)
        self.assertEqual(obj.name, "Ubuntu")
        self.assertEqual(obj.version, "18")

    def test_almalinux(self):
        obj = dist.AlmaLinux("8")
        self.assertFalse(obj.deb_based)
        self.assertTrue(obj.rhel_based)
        self.assertEqual(obj.name, "AlmaLinux")
        self.assertEqual(obj.version, "8")

    def test_centos(self):
        obj = dist.CentOs("7")
        self.assertFalse(obj.deb_based)
        self.assertTrue(obj.rhel_based)
        self.assertEqual(obj.name, "CentOS")
        self.assertEqual(obj.version, "7")
