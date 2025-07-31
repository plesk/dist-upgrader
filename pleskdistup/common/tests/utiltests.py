# Copyright 2023-2025. WebPros International GmbH. All rights reserved.
import unittest

import src.util as util


class TestDictOfListsMerge(unittest.TestCase):
    def test_same_field(self):
        self.assertEqual(
            util.merge_dicts_of_lists(
                {"a": [1, 2, 3]},
                {"a": [4, 5, 6]}
            ),
            {"a": [1, 2, 3, 4, 5, 6]}
        )

    def test_different_fields(self):
        self.assertEqual(
            util.merge_dicts_of_lists(
                {"a": [1, 2, 3]},
                {"b": [4, 5, 6]}
            ),
            {"a": [1, 2, 3], "b": [4, 5, 6]}
        )

    def test_first_empty(self):
        self.assertEqual(
            util.merge_dicts_of_lists(
                {},
                {"a": [4, 5, 6]}
            ),
            {"a": [4, 5, 6]}
        )

    def test_second_empty(self):
        self.assertEqual(
            util.merge_dicts_of_lists(
                {"a": [1, 2, 3]},
                {}
            ),
            {"a": [1, 2, 3]}
        )

    def test_both_empty(self):
        self.assertEqual(
            util.merge_dicts_of_lists(
                {},
                {}
            ),
            {}
        )

    def test_complex(self):
        self.assertEqual(
            util.merge_dicts_of_lists(
                {"a": [1, 2, 3], "b": [4, 5, 6]},
                {"a": [7, 8, 9], "c": [10, 11, 12]}
            ),
            {"a": [1, 2, 3, 7, 8, 9], "b": [4, 5, 6], "c": [10, 11, 12]}
        )


class TestMultiSplit(unittest.TestCase):
    def test_single_delimiter(self):
        self.assertEqual(
            util.multi_split("apple,banana,orange", [","]),
            ["apple", "banana", "orange"]
        )

    def test_multiple_delimiters(self):
        self.assertEqual(
            util.multi_split("apple;banana:orange", [";", ":"]),
            ["apple", "banana", "orange"]
        )

    def test_three_delimiters(self):
        self.assertEqual(
            util.multi_split("apple,banana;orange:grape", [",", ";", ":"]),
            ["apple", "banana", "orange", "grape"]
        )

    def test_empty_delimiters(self):
        self.assertEqual(
            util.multi_split("apple,,banana;:orange", []),
            ["apple,,banana;:orange"]
        )

    def test_keep_empty_strings(self):
        self.assertEqual(
            util.multi_split("apple,,banana;:orange", [",", ";", ":"]),
            ["apple", "", "banana", "", "orange"]
        )

    def test_skip_empty_strings(self):
        self.assertEqual(
            util.multi_split("apple,,banana;:orange", [",", ";", ":"], remove_empty=True),
            ["apple", "banana", "orange"]
        )

    def test_no_delimiters(self):
        self.assertEqual(
            util.multi_split("applebananaorange", [",", ";", ":"]),
            ["applebananaorange"]
        )

    def test_empty_string(self):
        self.assertEqual(
            util.multi_split("", [",", ";", ":"]),
            [""]
        )
