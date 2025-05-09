# Copyright 2023-2025. WebPros International GmbH. All rights reserved.
import unittest
import os
import tempfile

import src.motd as motd
import src.files as files


class InprogressSshLoginMessageTests(unittest.TestCase):
    def setUp(self):
        self.motd_path = tempfile.mktemp()

    def tearDown(self):
        for path in [self.motd_path, self.motd_path + files.DEFAULT_BACKUP_EXTENSION]:
            if os.path.exists(path):
                os.remove(path)

    def test_add_simple_message(self):
        expected_message = "one"
        motd.add_inprogress_ssh_login_message(expected_message, self.motd_path)
        with open(self.motd_path) as motd_file:
            self.assertEqual(motd_file.read(), expected_message)

    def test_add_two_messages(self):
        expected_message = "one\ntwo\n"
        motd.add_inprogress_ssh_login_message("one\n", self.motd_path)
        motd.add_inprogress_ssh_login_message("two\n", self.motd_path)
        with open(self.motd_path) as motd_file:
            self.assertEqual(motd_file.read(), expected_message)

    def test_old_backed_up(self):
        with open(self.motd_path, "w") as motd_file:
            motd_file.write("old\n")

        motd.add_inprogress_ssh_login_message("new\n", self.motd_path)

        with open(self.motd_path) as motd_file:
            self.assertEqual(motd_file.read(), "old\nnew\n")

        with open(self.motd_path + files.DEFAULT_BACKUP_EXTENSION) as motd_file:
            self.assertEqual(motd_file.read(), "old\n")

    def test_restore(self):
        with open(self.motd_path, "w") as motd_file:
            motd_file.write("old")

        motd.add_inprogress_ssh_login_message("new", self.motd_path)

        motd.restore_ssh_login_message(self.motd_path)

        with open(self.motd_path) as motd_file:
            self.assertEqual(motd_file.read(), "old")

    def test_restore_no_backup(self):
        motd.add_inprogress_ssh_login_message("new", self.motd_path)
        motd.restore_ssh_login_message(self.motd_path)

        self.assertFalse(os.path.exists(self.motd_path))
        self.assertFalse(files.backup_exists(self.motd_path))


class FinishSshLoginMessageTests(unittest.TestCase):
    def setUp(self):
        self.motd_path = tempfile.mktemp()

    def tearDown(self):
        for path in [self.motd_path, self.motd_path + files.DEFAULT_BACKUP_EXTENSION, self.motd_path + ".next"]:
            if os.path.exists(path):
                os.remove(path)

    def test_publish_simple_message(self):
        expected_message = """
===============================================================================
Message from the Plesk dist-upgrader tool:
one
You can remove this message from the {} file.
===============================================================================
""".format(motd.MOTD_PATH)

        motd.add_finish_ssh_login_message("one\n", self.motd_path)
        motd.publish_finish_ssh_login_message(self.motd_path)
        with open(self.motd_path) as motd_file:
            self.assertEqual(motd_file.read(), expected_message)

    def test_publish_several_messages(self):
        expected_message = """
===============================================================================
Message from the Plesk dist-upgrader tool:
one
two
You can remove this message from the {} file.
===============================================================================
""".format(motd.MOTD_PATH)
        motd.add_finish_ssh_login_message("one\n", self.motd_path)
        motd.add_finish_ssh_login_message("two\n", self.motd_path)
        motd.publish_finish_ssh_login_message(self.motd_path)
        with open(self.motd_path) as motd_file:
            self.assertEqual(motd_file.read(), expected_message)

    def test_file_next_is_removed(self):
        motd.add_finish_ssh_login_message("one", self.motd_path)
        motd.publish_finish_ssh_login_message(self.motd_path)
        self.assertFalse(os.path.exists(self.motd_path + ".next"))

    def test_backed_up_message_saved(self):
        expected_message = """old

===============================================================================
Message from the Plesk dist-upgrader tool:
one
two
You can remove this message from the {} file.
===============================================================================
""".format(motd.MOTD_PATH)

        with open(self.motd_path + files.DEFAULT_BACKUP_EXTENSION, "w") as motd_file:
            motd_file.write("old\n")

        motd.add_inprogress_ssh_login_message("new\n", self.motd_path)

        motd.add_finish_ssh_login_message("one\n", self.motd_path)
        motd.add_finish_ssh_login_message("two\n", self.motd_path)
        motd.publish_finish_ssh_login_message(self.motd_path)

        with open(self.motd_path) as motd_file:
            self.assertEqual(motd_file.read(), expected_message)
