# Copyright 1999-2023. Plesk International GmbH. All rights reserved.
import unittest

import src.dist as dist


class TestDistro(unittest.TestCase):

    def test_is_ubuntu_18_deb_based(self):
        self.assertTrue(dist._is_deb_based(dist.Distro.UBUNTU18))

    def test_is_ubuntu_20_deb_based(self):
        self.assertTrue(dist._is_deb_based(dist.Distro.UBUNTU20))

    def test_is_centos_7_rhel_based(self):
        self.assertTrue(dist._is_rhel_based(dist.Distro.CENTOS7))

    def test_is_alma_8_rhel_based(self):
        self.assertTrue(dist._is_rhel_based(dist.Distro.ALMALINUX8))

    def test_is_ubuntu_18_not_rhel_based(self):
        self.assertFalse(dist._is_rhel_based(dist.Distro.UBUNTU18))

    def test_is_ubuntu_20_not_rhel_based(self):
        self.assertFalse(dist._is_rhel_based(dist.Distro.UBUNTU20))

    def test_is_centos_7_not_deb_based(self):
        self.assertFalse(dist._is_deb_based(dist.Distro.CENTOS7))

    def test_is_alma_8_not_deb_based(self):
        self.assertFalse(dist._is_deb_based(dist.Distro.ALMALINUX8))
