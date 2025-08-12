# Copyright 2023-2025. WebPros International GmbH. All rights reserved.
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

    def test_mount_point_is_swap(self):
        with open(self.test_file_path, "w") as f:
            f.write("# comment\n")
            f.write("/dev/sda2 /var ext4 defaults 0 1\n")
            f.write("/dev/sda5 swap swap defaults 0 1\n")
            f.write("/dev/sda4 /home ext4 defaults 0 1\n")

        self.assertEqual(mounts.get_fstab_configuration_misorderings(self.test_file_path), [])


class FstabDuplicateTests(unittest.TestCase):
    def setUp(self):
        self.test_file_path = tempfile.mktemp()

    def test_no_file(self):
        self.assertEqual(mounts.get_fstab_duplicate_mount_points("noexist.txt"), {})

    def test_empty_file(self):
        with open(self.test_file_path, "w") as _:
            pass
        self.assertEqual(mounts.get_fstab_duplicate_mount_points(self.test_file_path), {})

    def test_no_duplicates(self):
        with open(self.test_file_path, "w") as f:
            f.write("# comment\n")
            f.write("/dev/sda1 / ext4 defaults 0 1\n")
            f.write("/dev/sda2 /var ext4 defaults 0 1\n")
            f.write("/dev/sda3 /home ext4 defaults 0 1\n")
        self.assertEqual(mounts.get_fstab_duplicate_mount_points(self.test_file_path), {})

    def test_one_duplicate_mount_point(self):
        with open(self.test_file_path, "w") as f:
            f.write("# comment\n")
            f.write("/dev/sda1 / ext4 defaults 0 1\n")
            f.write("/dev/sda2 /home ext4 defaults 0 1\n")
            f.write("UUID=1234-5678 /home xfs defaults 0 0\n")

        result = mounts.get_fstab_duplicate_mount_points(self.test_file_path)
        self.assertEqual(len(result), 1)
        self.assertIn("/home", result)
        self.assertEqual(len(result["/home"]), 2)
        self.assertIn("UUID=1234-5678 /home xfs defaults 0 0", result["/home"])
        self.assertIn("/dev/sda2 /home ext4 defaults 0 1", result["/home"])

    def test_multiple_duplicate_mount_points(self):
        with open(self.test_file_path, "w") as f:
            f.write("/dev/sda1 / ext4 defaults 0 1\n")
            f.write("/dev/sda2 /home ext4 defaults 0 1\n")
            f.write("UUID=1234-5678 /home xfs defaults 0 0\n")
            f.write("/dev/sda3 /var ext4 defaults 0 1\n")
            f.write("/dev/sdb1 /var xfs defaults 0 0\n")
            f.write("LABEL=data /home ext4 defaults 0 1\n")

        result = mounts.get_fstab_duplicate_mount_points(self.test_file_path)
        self.assertEqual(len(result), 2)

        self.assertIn("/home", result)
        self.assertEqual(len(result["/home"]), 3)
        self.assertIn("UUID=1234-5678 /home xfs defaults 0 0", result["/home"])
        self.assertIn("/dev/sda2 /home ext4 defaults 0 1", result["/home"])
        self.assertIn("LABEL=data /home ext4 defaults 0 1", result["/home"])

        self.assertIn("/var", result)
        self.assertEqual(len(result["/var"]), 2)
        self.assertIn("/dev/sda3 /var ext4 defaults 0 1", result["/var"])
        self.assertIn("/dev/sdb1 /var xfs defaults 0 0", result["/var"])

    def test_comments_and_empty_lines_ignored(self):
        with open(self.test_file_path, "w") as f:
            f.write("# This is a comment\n")
            f.write("\n")
            f.write("/dev/sda1 / ext4 defaults 0 1\n")
            f.write("# Another comment\n")
            f.write("# LABEL=data /home ext4 defaults 0 1\n")
            f.write("/dev/sda2 /home ext4 defaults 0 1\n")
            f.write("\n")
            f.write("UUID=1234-5678 /home xfs defaults 0 0\n")

        result = mounts.get_fstab_duplicate_mount_points(self.test_file_path)
        self.assertIn("/home", result)
        self.assertEqual(len(result["/home"]), 2)
        self.assertIn("UUID=1234-5678 /home xfs defaults 0 0", result["/home"])
        self.assertIn("/dev/sda2 /home ext4 defaults 0 1", result["/home"])
