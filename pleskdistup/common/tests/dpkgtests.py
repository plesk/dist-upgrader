# Copyright 2023-2025. WebPros International GmbH. All rights reserved.
import os
import unittest

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
