# Copyright 2023-2025. WebPros International GmbH. All rights reserved.
import unittest
import unittest.mock as mock

import src.debconf as debconf


class TestParseShowOutput(unittest.TestCase):
    def test_empty_output(self):
        self.assertEqual(debconf.parse_show_output(""), {})

    def test_seen_and_unseen_markers(self):
        output = """  grub-pc/timeout: 5
* grub2/linux_cmdline_default: nomodeset consoleblank=0
"""
        self.assertEqual(debconf.parse_show_output(output), {
            "grub-pc/timeout": ["5"],
            "grub2/linux_cmdline_default": ["nomodeset consoleblank=0"],
        })

    def test_empty_value_is_empty_list(self):
        self.assertEqual(debconf.parse_show_output("* grub2/linux_cmdline:\n"), {"grub2/linux_cmdline": []})

    def test_value_with_colon(self):
        self.assertEqual(debconf.parse_show_output("  some/question: http://example.com:8080/\n"),
                         {"some/question": ["http://example.com:8080/"]})

    def test_lines_without_question_are_skipped(self):
        output = """
  grub-pc/timeout: 5

garbage line
"""
        self.assertEqual(debconf.parse_show_output(output), {"grub-pc/timeout": ["5"]})

    def test_single_device(self):
        self.assertEqual(debconf.parse_show_output("* grub-pc/install_devices: /dev/sda\n"),
                         {"grub-pc/install_devices": ["/dev/sda"]})

    def test_several_devices(self):
        self.assertEqual(debconf.parse_show_output("* grub-pc/install_devices: /dev/sda, /dev/sdb\n"),
                         {"grub-pc/install_devices": ["/dev/sda", "/dev/sdb"]})

    def test_several_devices_by_id(self):
        output = "* grub-pc/install_devices: /dev/disk/by-id/nvme-Amazon_Elastic_Block_Store_vol0910121651753e1ee, " \
                 "/dev/disk/by-id/nvme-Amazon_Elastic_Block_Store_vol035a3674add2b5ab2\n"
        self.assertEqual(debconf.parse_show_output(output), {
            "grub-pc/install_devices": [
                "/dev/disk/by-id/nvme-Amazon_Elastic_Block_Store_vol0910121651753e1ee",
                "/dev/disk/by-id/nvme-Amazon_Elastic_Block_Store_vol035a3674add2b5ab2",
            ],
        })

    def test_comma_without_space_is_not_separator(self):
        self.assertEqual(debconf.parse_show_output("* grub2/linux_cmdline: console=ttyS0,115200\n"),
                         {"grub2/linux_cmdline": ["console=ttyS0,115200"]})

    def test_password_omitted(self):
        self.assertEqual(debconf.parse_show_output("* some/password: (password omitted)\n"),
                         {"some/password": ["(password omitted)"]})

    def test_full_grub_pc_output(self):
        output = """  grub2/update_nvram: true
  grub-pc/hidden_timeout: false
* grub2/linux_cmdline:
  grub2/enable_os_prober: false
  grub-pc/chainload_from_menu.lst: true
* grub2/linux_cmdline_default: nomodeset consoleblank=0
  grub-pc/mixed_legacy_and_grub2: true
  grub2/device_map_regenerated:
  grub2/kfreebsd_cmdline:
  grub-pc/postrm_purge_boot_grub: false
  grub-pc/install_devices_disks_changed:
  grub2/kfreebsd_cmdline_default: quiet
  grub-pc/partition_description:
  grub-pc/install_devices_failed_upgrade: true
  grub2/force_efi_extra_removable: false
  grub-pc/install_devices_empty: false
  grub-pc/timeout: 5
* grub-pc/install_devices: /dev/sda, /dev/sdb
  grub-pc/disk_description:
  grub-pc/install_devices_failed: false
  grub-pc/kopt_extracted: false
"""
        self.assertEqual(debconf.parse_show_output(output), {
            "grub2/update_nvram": ["true"],
            "grub-pc/hidden_timeout": ["false"],
            "grub2/linux_cmdline": [],
            "grub2/enable_os_prober": ["false"],
            "grub-pc/chainload_from_menu.lst": ["true"],
            "grub2/linux_cmdline_default": ["nomodeset consoleblank=0"],
            "grub-pc/mixed_legacy_and_grub2": ["true"],
            "grub2/device_map_regenerated": [],
            "grub2/kfreebsd_cmdline": [],
            "grub-pc/postrm_purge_boot_grub": ["false"],
            "grub-pc/install_devices_disks_changed": [],
            "grub2/kfreebsd_cmdline_default": ["quiet"],
            "grub-pc/partition_description": [],
            "grub-pc/install_devices_failed_upgrade": ["true"],
            "grub2/force_efi_extra_removable": ["false"],
            "grub-pc/install_devices_empty": ["false"],
            "grub-pc/timeout": ["5"],
            "grub-pc/install_devices": ["/dev/sda", "/dev/sdb"],
            "grub-pc/disk_description": [],
            "grub-pc/install_devices_failed": ["false"],
            "grub-pc/kopt_extracted": ["false"],
        })


class TestGetPackageValues(unittest.TestCase):
    @mock.patch("src.util.logged_check_call", return_value="* grub-pc/install_devices: /dev/sda, /dev/sdb\n")
    def test_runs_debconf_show(self, mock_call):
        self.assertEqual(debconf.get_package_values("grub-pc"),
                         {"grub-pc/install_devices": ["/dev/sda", "/dev/sdb"]})
        mock_call.assert_called_once_with(["/usr/bin/debconf-show", "grub-pc"])
