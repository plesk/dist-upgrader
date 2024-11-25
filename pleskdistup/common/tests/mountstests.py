# Copyright 2023-2024. WebPros International GmbH. All rights reserved.
import unittest
import tempfile

import src.mounts as mounts


class FstabMisorderingTests(unittest.TestCase):
    def setUp(self):
        self.test_file_path = tempfile.mktemp()

    def test_no_file(self):
        self.assertEqual(mounts.get_fstab_configuration_misorderings("noexist.txt"), [])

    def test_empty_file(self):
        with open(self.test_file_path, "w") as _:
            pass
        self.assertEqual(mounts.get_fstab_configuration_misorderings(self.test_file_path), [])

    def test_empty_string(self):
        with open(self.test_file_path, "w") as f:
            f.write("")
        self.assertEqual(mounts.get_fstab_configuration_misorderings(self.test_file_path), [])

    def test_one_mount_point(self):
        with open(self.test_file_path, "w") as f:
            f.write("# comment\n")
            f.write("/dev/sda1 / ext4 defaults 0 1\n")
        self.assertEqual(mounts.get_fstab_configuration_misorderings(self.test_file_path), [])

    def test_no_misorderings(self):
        with open(self.test_file_path, "w") as f:
            f.write("# comment\n")
            f.write("/dev/sda1 / ext4 defaults 0 1\n")
            f.write("/dev/sda2 /var ext4 defaults 0 1\n")
            f.write("proc /proc proc defaults 0 0\n")
            f.write("devpts /dev/pts devpts gid=5,mode=620 0 0\n")
            f.write("tmpfs /dev/shm tmpfs defaults 0 0\n")
        self.assertEqual(mounts.get_fstab_configuration_misorderings(self.test_file_path), [])

    def test_one_misordering(self):
        with open(self.test_file_path, "w") as f:
            f.write("# comment\n")
            f.write("/dev/sda2 /var ext4 defaults 0 1\n")
            f.write("/dev/sda1 / ext4 defaults 0 1\n")
            f.write("proc /proc proc defaults 0 0\n")
            f.write("devpts /dev/pts devpts gid=5,mode=620 0 0\n")
            f.write("tmpfs /dev/shm tmpfs defaults 0 0\n")
        self.assertEqual(mounts.get_fstab_configuration_misorderings(self.test_file_path), [("/", "/var")])

    def test_two_misorderings_for_one_parent(self):
        with open(self.test_file_path, "w") as f:
            f.write("# comment\n")
            f.write("/dev/sda2 /var ext4 defaults 0 1\n")
            f.write("/dev/sda3 /var/log ext4 defaults 0 1\n")
            f.write("/dev/sda1 / ext4 defaults 0 1\n")
            f.write("proc /proc proc defaults 0 0\n")
            f.write("devpts /dev/pts devpts gid=5,mode=620 0 0\n")
            f.write("tmpfs /dev/shm tmpfs defaults 0 0\n")
        self.assertEqual(mounts.get_fstab_configuration_misorderings(self.test_file_path), [("/", "/var"), ("/", "/var/log")])

    def test_several_different_misorderings(self):
        with open(self.test_file_path, "w") as f:
            f.write("# comment\n")
            f.write("/dev/sda2 /var ext4 defaults 0 1\n")
            f.write("/dev/sda1 / ext4 defaults 0 1\n")
            f.write("/dev/sda5 /home/test ext4 defaults 0 1\n")
            f.write("/dev/sda4 /home ext4 defaults 0 1\n")
            f.write("proc /proc proc defaults 0 0\n")
            f.write("devpts /dev/pts devpts gid=5,mode=620 0 0\n")
            f.write("tmpfs /dev/shm tmpfs defaults 0 0\n")
        self.assertEqual(mounts.get_fstab_configuration_misorderings(self.test_file_path), [("/", "/var"), ("/home", "/home/test")])

    def test_file_without_root(self):
        with open(self.test_file_path, "w") as f:
            f.write("# comment\n")
            f.write("/dev/sda2 /var ext4 defaults 0 1\n")
            f.write("/dev/sda5 /home/test ext4 defaults 0 1\n")
            f.write("/dev/sda4 /home ext4 defaults 0 1\n")
            f.write("proc /proc proc defaults 0 0\n")
            f.write("devpts /dev/pts devpts gid=5,mode=620 0 0\n")
            f.write("tmpfs /dev/shm tmpfs defaults 0 0\n")
        self.assertEqual(mounts.get_fstab_configuration_misorderings(self.test_file_path), [("/home", "/home/test")])
