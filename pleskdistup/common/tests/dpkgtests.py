# Copyright 2023-2025. WebPros International GmbH. All rights reserved.
import os
import subprocess
import unittest
import unittest.mock as mock
import shutil

import src.dpkg as dpkg


class TestGetDPKGRepositoriesUrls(unittest.TestCase):

    def tearDown(self):
        if os.path.exists("test.list"):
            os.remove("test.list")

    def test_no_config_file(self):
        self.assertEqual(dpkg.get_repositories_urls("nonexistent.list"), set())

    def test_simple_repository(self):
        with open("test.list", "w") as test_file:
            test_file.write('''
deb http://example.com/repo/ubuntu focal main
deb-src http://example.com/repo/ubuntu focal main
''')
        self.assertEqual(dpkg.get_repositories_urls("test.list"), set(["http://example.com/repo/ubuntu/dists/focal"]))

    def test_repository_with_comments(self):
        with open("test.list", "w") as test_file:
            test_file.write('''
deb http://example.com/repo/ubuntu focal main
# This is a comment
deb-src http://example.com/repo/ubuntu focal main
# Another comment
''')
        self.assertEqual(dpkg.get_repositories_urls("test.list"), set(["http://example.com/repo/ubuntu/dists/focal"]))

    def test_repository_with_spaces(self):
        with open("test.list", "w") as test_file:
            test_file.write('''
deb    http://example.com/repo/ubuntu    focal    main
deb-src    http://example.com/repo/ubuntu    focal    main
''')
        self.assertEqual(dpkg.get_repositories_urls("test.list"), set(["http://example.com/repo/ubuntu/dists/focal"]))

    def test_repository_with_tabs(self):
        with open("test.list", "w") as test_file:
            test_file.write('''
deb\thttp://example.com/repo/ubuntu\tfocal\tmain
deb-src http://example.com/repo/ubuntu focal main
''')
        self.assertEqual(dpkg.get_repositories_urls("test.list"), set(["http://example.com/repo/ubuntu/dists/focal"]))

    def test_https_repository(self):
        with open("test.list", "w") as test_file:
            test_file.write('''
deb https://example.com/repo/ubuntu focal main
deb-src http://example.com/repo/ubuntu focal main
''')
        self.assertEqual(dpkg.get_repositories_urls("test.list"), set(["https://example.com/repo/ubuntu/dists/focal", "http://example.com/repo/ubuntu/dists/focal"]))


class TestGetDPKGRepositoryMetafileUrl(unittest.TestCase):

    def test_simple_case(self):
        self.assertEqual(dpkg.get_repository_metafile_url("http://example.com/repo/ubuntu/dists/focal"), "http://example.com/repo/ubuntu/dists/focal/Release")


class TestFindEnabledRepository(unittest.TestCase):
    TEST_DIR = "./test.list.d"

    def setUp(self):
        os.makedirs(self.TEST_DIR, exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.TEST_DIR):
            shutil.rmtree(self.TEST_DIR)

        if os.path.exists(os.path.join(self.TEST_DIR, "test.list")):
            os.remove(os.path.join(self.TEST_DIR, "test.list"))

    def test_no_config_file(self):
        self.assertFalse(dpkg.is_repository_url_enabled("example.com"))

    def test_repository_not_present(self):
        with open(os.path.join(self.TEST_DIR, "test.list"), "w") as test_file:
            test_file.write('''
deb http://example.com/repo/ubuntu focal main
deb-src http://example.com/repo/ubuntu focal main
''')
        self.assertFalse(dpkg.is_repository_url_enabled("nonexistent.repo", sources_dir=self.TEST_DIR))

    def test_repository_present(self):
        with open(os.path.join(self.TEST_DIR, "test.list"), "w") as test_file:
            test_file.write('''
deb http://example.com/repo/ubuntu focal main
deb-src http://example.com/repo/ubuntu focal main
''')
        self.assertTrue(dpkg.is_repository_url_enabled("example.com/repo/ubuntu", sources_dir=self.TEST_DIR))

    def test_repository_present_but_commented(self):
        with open(os.path.join(self.TEST_DIR, "test.list"), "w") as test_file:
            test_file.write('''
deb http://example2.com/repo/ubuntu focal main
deb-src http://example2.com/repo/ubuntu focal main
# deb http://example.com/repo/ubuntu focal main
# deb-src http://example.com/repo/ubuntu focal main
''')
        self.assertFalse(dpkg.is_repository_url_enabled("example.com/repo/ubuntu", sources_dir=self.TEST_DIR))

    def test_multiple_files(self):
        with open(os.path.join(self.TEST_DIR, "test1.list"), "w") as test_file:
            test_file.write('''
deb http://example1.com/repo/ubuntu focal main
deb-src http://example1.com/repo/ubuntu focal main
''')
        with open(os.path.join(self.TEST_DIR, "test2.list"), "w") as test_file:
            test_file.write('''
deb http://example2.com/repo/ubuntu focal main
deb-src http://example2.com/repo/ubuntu focal main
''')
        self.assertTrue(dpkg.is_repository_url_enabled("example1.com/repo/ubuntu", sources_dir=self.TEST_DIR))
        self.assertTrue(dpkg.is_repository_url_enabled("example2.com/repo/ubuntu", sources_dir=self.TEST_DIR))


def _dpkg_query_result(returncode: int, stdout: str) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


class TestPackageStatus(unittest.TestCase):

    @mock.patch("src.dpkg.log.warn")
    @mock.patch("src.dpkg.subprocess.run", return_value=_dpkg_query_result(1, ""))
    def test_unknown_package(self, _, mock_warn):
        self.assertIsNone(dpkg.get_package_status("grub-pc"))
        self.assertFalse(dpkg.is_package_installed("grub-pc"))
        self.assertFalse(dpkg.is_package_present("grub-pc"))
        mock_warn.assert_not_called()

    @mock.patch("src.dpkg.log.warn")
    @mock.patch("src.dpkg.subprocess.run", return_value=_dpkg_query_result(2, ""))
    def test_dpkg_query_fatal_error(self, _, mock_warn):
        self.assertIsNone(dpkg.get_package_status("grub-pc"))
        self.assertFalse(dpkg.is_package_installed("grub-pc"))
        self.assertFalse(dpkg.is_package_present("grub-pc"))
        mock_warn.assert_called()

    @mock.patch("src.dpkg.subprocess.run", return_value=_dpkg_query_result(0, "not-installed"))
    def test_not_installed(self, _):
        self.assertEqual(dpkg.get_package_status("grub-pc"), "not-installed")
        self.assertFalse(dpkg.is_package_installed("grub-pc"))
        self.assertFalse(dpkg.is_package_present("grub-pc"))

    @mock.patch("src.dpkg.subprocess.run", return_value=_dpkg_query_result(0, "config-files"))
    def test_config_files_only(self, _):
        self.assertEqual(dpkg.get_package_status("grub-pc"), "config-files")
        self.assertFalse(dpkg.is_package_installed("grub-pc"))
        self.assertFalse(dpkg.is_package_present("grub-pc"))

    @mock.patch("src.dpkg.subprocess.run", return_value=_dpkg_query_result(0, "half-configured"))
    def test_half_configured(self, _):
        self.assertEqual(dpkg.get_package_status("grub-pc"), "half-configured")
        self.assertFalse(dpkg.is_package_installed("grub-pc"))
        self.assertTrue(dpkg.is_package_present("grub-pc"))

    @mock.patch("src.dpkg.subprocess.run", return_value=_dpkg_query_result(0, "unpacked"))
    def test_unpacked(self, _):
        self.assertEqual(dpkg.get_package_status("grub-pc"), "unpacked")
        self.assertFalse(dpkg.is_package_installed("grub-pc"))
        self.assertTrue(dpkg.is_package_present("grub-pc"))

    @mock.patch("src.dpkg.subprocess.run", return_value=_dpkg_query_result(0, "installed"))
    def test_installed(self, mock_run):
        self.assertEqual(dpkg.get_package_status("grub-pc"), "installed")
        self.assertTrue(dpkg.is_package_installed("grub-pc"))
        self.assertTrue(dpkg.is_package_present("grub-pc"))
        for call in mock_run.call_args_list:
            self.assertEqual(call[0][0], ["/usr/bin/dpkg-query", "--showformat", "${db:Status-status}", "--show", "grub-pc"])
