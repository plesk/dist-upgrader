# Copyright 2023-2026. WebPros International GmbH. All rights reserved.
import os
import shutil
import subprocess
import tempfile
import unittest
import unittest.mock

import src.selinux as selinux


class GetConfiguredModeTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "config")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def _write_config(self, content):
        with open(self.config_path, "w") as config:
            config.write(content)

    def test_enforcing(self):
        self._write_config("""# This file controls the state of SELinux on the system.
SELINUX=enforcing
SELINUXTYPE=targeted
""")
        self.assertEqual(selinux.get_configured_mode(self.config_path), selinux.SelinuxMode.ENFORCING)

    def test_permissive(self):
        self._write_config("SELINUX=permissive\nSELINUXTYPE=targeted\n")
        self.assertEqual(selinux.get_configured_mode(self.config_path), selinux.SelinuxMode.PERMISSIVE)

    def test_disabled(self):
        self._write_config("SELINUX=disabled\nSELINUXTYPE=targeted\n")
        self.assertEqual(selinux.get_configured_mode(self.config_path), selinux.SelinuxMode.DISABLED)

    def test_mixed_case_value(self):
        self._write_config("SELINUX=Enforcing\n")
        self.assertEqual(selinux.get_configured_mode(self.config_path), selinux.SelinuxMode.ENFORCING)

    def test_value_with_trailing_whitespace_and_quotes(self):
        self._write_config("SELINUX=\"enforcing\"   \n")
        self.assertEqual(selinux.get_configured_mode(self.config_path), selinux.SelinuxMode.ENFORCING)

    def test_commented_out_assignment_is_ignored(self):
        self._write_config("""# SELINUX= can take one of these three values:
#SELINUX=enforcing
SELINUX=permissive
""")
        self.assertEqual(selinux.get_configured_mode(self.config_path), selinux.SelinuxMode.PERMISSIVE)

    def test_trailing_comment_is_ignored(self):
        # libselinux matches the value by prefix, so it reads this as enforcing and the host
        # really does boot enforcing - the check has to agree with it
        self._write_config("SELINUX=enforcing # keep it strict\n")
        self.assertEqual(selinux.get_configured_mode(self.config_path), selinux.SelinuxMode.ENFORCING)

    def test_trailing_comment_without_separating_space_is_ignored(self):
        self._write_config("SELINUX=permissive#for now\n")
        self.assertEqual(selinux.get_configured_mode(self.config_path), selinux.SelinuxMode.PERMISSIVE)

    def test_quoted_value_with_trailing_comment(self):
        self._write_config("SELINUX=\"disabled\"  # no selinux here\n")
        self.assertEqual(selinux.get_configured_mode(self.config_path), selinux.SelinuxMode.DISABLED)

    def test_value_that_is_only_a_comment(self):
        self._write_config("SELINUX=# nothing assigned\n")
        self.assertEqual(selinux.get_configured_mode(self.config_path), selinux.SelinuxMode.UNKNOWN)

    def test_first_effective_assignment_wins(self):
        self._write_config("SELINUX=permissive\nSELINUX=enforcing\n")
        self.assertEqual(selinux.get_configured_mode(self.config_path), selinux.SelinuxMode.PERMISSIVE)

    def test_empty_value(self):
        self._write_config("SELINUX=\nSELINUXTYPE=targeted\n")
        self.assertEqual(selinux.get_configured_mode(self.config_path), selinux.SelinuxMode.UNKNOWN)

    def test_unrecognized_value(self):
        self._write_config("SELINUX=foo\nSELINUXTYPE=targeted\n")
        self.assertEqual(selinux.get_configured_mode(self.config_path), selinux.SelinuxMode.UNKNOWN)

    def test_no_assignment_at_all(self):
        self._write_config("# nothing useful here\nSELINUXTYPE=targeted\n")
        self.assertEqual(selinux.get_configured_mode(self.config_path), selinux.SelinuxMode.UNKNOWN)

    def test_non_existent_file(self):
        self.assertEqual(
            selinux.get_configured_mode(os.path.join(self.temp_dir, "no_such_config")),
            selinux.SelinuxMode.UNKNOWN,
        )

    def test_undecodable_bytes_do_not_raise(self):
        with open(self.config_path, "wb") as config:
            config.write(b"# r\xe9sum\xe9 of the admin\nSELINUX=enforcing\n")
        self.assertEqual(selinux.get_configured_mode(self.config_path), selinux.SelinuxMode.ENFORCING)


class GetBooleanPersistedStateTests(unittest.TestCase):
    BOOLEAN_NAME = "httpd_can_network_connect"

    SEMANAGE_OUTPUT_TEMPLATE = """SELinux boolean                State  Default Description

abrt_anon_write                (off  ,  off)  Allow abrt to anon write
httpd_can_network_connect      ({runtime}  ,  {persisted})  Allow httpd to can network connect
httpd_can_network_connect_db   (off  ,  off)  Allow httpd to can network connect db
"""

    SEMANAGE_HEADER_ONLY_OUTPUT = """SELinux boolean                State  Default Description

"""

    def _get_state(self, output):
        with unittest.mock.patch("src.selinux.os.path.exists", return_value=True):
            with unittest.mock.patch("src.selinux.subprocess.check_output", return_value=output):
                return selinux.get_boolean_persisted_state(self.BOOLEAN_NAME)

    def test_runtime_on_persisted_on(self):
        output = self.SEMANAGE_OUTPUT_TEMPLATE.format(runtime="on", persisted="on")
        self.assertIs(self._get_state(output), True)

    def test_runtime_on_persisted_off(self):
        # A non-persistent 'setsebool' without '-P': the persisted value is what counts.
        # assertIs, not assertFalse: None would mean the line was not parsed at all
        output = self.SEMANAGE_OUTPUT_TEMPLATE.format(runtime="on", persisted="off")
        self.assertIs(self._get_state(output), False)

    def test_runtime_off_persisted_off(self):
        output = self.SEMANAGE_OUTPUT_TEMPLATE.format(runtime="off", persisted="off")
        self.assertIs(self._get_state(output), False)

    def test_boolean_with_shared_prefix_does_not_match(self):
        output = """SELinux boolean                State  Default Description

httpd_can_network_connect_db   (on   ,  on)   Allow httpd to can network connect db
"""
        self.assertIsNone(self._get_state(output))

    def test_header_only_output(self):
        self.assertIsNone(self._get_state(self.SEMANAGE_HEADER_ONLY_OUTPUT))

    def test_empty_output(self):
        self.assertIsNone(self._get_state(""))

    def test_semanage_is_missing(self):
        with unittest.mock.patch("src.selinux.os.path.exists", return_value=False):
            with unittest.mock.patch("src.selinux.subprocess.check_output") as check_output_mock:
                self.assertIsNone(selinux.get_boolean_persisted_state(self.BOOLEAN_NAME))
                check_output_mock.assert_not_called()

    def test_semanage_call_fails(self):
        with unittest.mock.patch("src.selinux.os.path.exists", return_value=True):
            with unittest.mock.patch(
                "src.selinux.subprocess.check_output",
                side_effect=subprocess.CalledProcessError(1, "semanage"),
            ):
                self.assertIsNone(selinux.get_boolean_persisted_state(self.BOOLEAN_NAME))
