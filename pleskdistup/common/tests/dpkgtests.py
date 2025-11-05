# Copyright 2023-2025. WebPros International GmbH. All rights reserved.
import os
import unittest
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
