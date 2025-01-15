# Copyright 2023-2025. WebPros International GmbH. All rights reserved.
import unittest

import src.strings as strings


class TestStringReplaceFunction(unittest.TestCase):

    def test_string_replace(self):
        replace_function = strings.create_replace_string_function("old", "new")
        line = "old text"
        self.assertEqual(replace_function(line), "new text")

    def test_empty_string(self):
        line = ""
        replace_function = strings.create_replace_string_function("old", "new")
        self.assertEqual(replace_function(line), "")

    def test_no_replace(self):
        replace_function = strings.create_replace_string_function("old", "new")
        line = "text"
        self.assertEqual(replace_function(line), "text")

    def test_multiple_occurrences(self):
        replace_function = strings.create_replace_string_function("old", "new")
        line = "old old old"
        self.assertEqual(replace_function(line), "new new new")

    def test_case_sensitivity(self):
        replace_function = strings.create_replace_string_function("Old", "new")
        line = "old Old OLD"
        self.assertEqual(replace_function(line), "old new OLD")

    def test_full_match(self):
        replace_function = strings.create_replace_string_function("old", "new")
        line = "old"
        self.assertEqual(replace_function(line), "new")


class TestStringReplaceByRegexpFunction(unittest.TestCase):

    def test_string_replace(self):
        replace_function = strings.create_replace_regexp_function(r"old", "new")
        line = "old text"
        self.assertEqual(replace_function(line), "new text")

    def test_empty_string(self):
        line = ""
        replace_function = strings.create_replace_regexp_function(r"old", "new")
        self.assertEqual(replace_function(line), "")

    def test_no_replace(self):
        replace_function = strings.create_replace_regexp_function(r"old", "new")
        line = "text"
        self.assertEqual(replace_function(line), "text")

    def test_multiple_occurrences(self):
        replace_function = strings.create_replace_regexp_function(r"old", "new")
        line = "old old old"
        self.assertEqual(replace_function(line), "new new new")

    def test_case_sensitivity(self):
        replace_function = strings.create_replace_regexp_function(r"Old", "new")
        line = "old Old OLD"
        self.assertEqual(replace_function(line), "old new OLD")

    def test_full_match(self):
        replace_function = strings.create_replace_regexp_function(r"old", "new")
        line = "old"
        self.assertEqual(replace_function(line), "new")

    def test_special_characters(self):
        func = strings.create_replace_regexp_function(r'\d+', 'number')
        self.assertEqual(func('123 abc 456'), 'number abc number')

    def test_group_replacement(self):
        func = strings.create_replace_regexp_function(r'(\d+)', r'number(\1)')
        self.assertEqual(func('123 abc 456'), 'number(123) abc number(456)')
