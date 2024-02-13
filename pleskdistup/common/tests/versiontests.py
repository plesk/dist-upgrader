# Copyright 2023-2024. WebPros International GmbH. All rights reserved.
import unittest

import src.version as version


class KernelVersionTests(unittest.TestCase):

    def _check_parse(self, version_string, expected):
        kernel = version.KernelVersion(version_string)
        self.assertEqual(str(kernel), expected)

    def test_kernel_parse_simple(self):
        self._check_parse("3.10.0-1160.95.1.el7.x86_64", "3.10.0-1160.95.1.el7.x86_64")

    def test_kernel_parse_small_build(self):
        self._check_parse("3.10.0-1160.el7.x86_64", "3.10.0-1160.el7.x86_64")

    def test_kernel_parse_large_build(self):
        self._check_parse("2.25.16-1.2.3.4.5.el7.x86_64", "2.25.16-1.2.3.4.5.el7.x86_64")

    def test_kernel_parse_no_build(self):
        self._check_parse("3.10.0.el7.x86_64", "3.10.0.el7.x86_64")

    def test_kernel_parse_virtuozo(self):
        self._check_parse("3.10.0-1160.90.1.vz7.200.7", "3.10.0-1160.90.1.vz7")

    def test_kernel_parse_small(self):
        self._check_parse("3.14.43-1", "3.14.43-1")

    def test_kernel_start_with_prefix(self):
        self._check_parse("kernel-3.10.0-1160.95.1.el7.x86_64", "3.10.0-1160.95.1.el7.x86_64")

    def test_kernel_start_with_plus_prefix(self):
        self._check_parse("kernel-plus-3.10.0-327.36.3.el7.centos.plus.x86_64", "3.10.0-327.36.3.el7.centos.plus.x86_64")

    def test_kernel_parse_plus(self):
        kernel = version.KernelVersion("3.10.0-327.36.3.el7.centos.plus.x86_64")
        self.assertEqual(str(kernel), "3.10.0-327.36.3.el7.centos.plus.x86_64")
        self.assertEqual(kernel.distro, "el7.centos.plus")
        self.assertEqual(kernel.arch, "x86_64")

    def test_kernel_starts_with_realtime_prefix(self):
        self._check_parse("kernel-rt-core-3.10.0-1160.95.1.rt7.130.el7.x86_64", "3.10.0-1160.95.1.rt7.130.el7.x86_64")

    def test_kernel_parse_realtime(self):
        kernel = version.KernelVersion("3.10.0-1160.95.10.rt7.130.el7.x86_64")
        self.assertEqual(str(kernel), "3.10.0-1160.95.10.rt7.130.el7.x86_64")
        self.assertEqual(kernel.build, "1160.95.10")
        self.assertEqual(kernel.distro, "rt7.130.el7")
        self.assertEqual(kernel.arch, "x86_64")

    def test_compare_simple_equal(self):
        kernel1 = version.KernelVersion("3.10.0-1160.95.1.el7.x86_64")
        kernel2 = version.KernelVersion("3.10.0-1160.95.1.el7.x86_64")
        self.assertEqual(kernel1, kernel2)

    def test_compare_simple_less_build(self):
        kernel1 = version.KernelVersion("3.10.0-1160.95.1.el7.x86_64")
        kernel2 = version.KernelVersion("3.10.0-1160.95.2.el7.x86_64")
        self.assertLess(kernel1, kernel2)

    def test_compare_simple_less_patch(self):
        kernel1 = version.KernelVersion("3.10.0-1160.95.1.el7.x86_64")
        kernel2 = version.KernelVersion("3.10.2-1160.95.1.el7.x86_64")
        self.assertLess(kernel1, kernel2)

    def test_compare_simple_less_patch_exponent(self):
        kernel1 = version.KernelVersion("3.10.1-1160.95.1.el7.x86_64")
        kernel2 = version.KernelVersion("3.10.10-1160.95.1.el7.x86_64")
        self.assertLess(kernel1, kernel2)

    def test_compare_simple_less_minor(self):
        kernel1 = version.KernelVersion("3.10.0-1160.95.1.el7.x86_64")
        kernel2 = version.KernelVersion("3.11.0-1160.95.1.el7.x86_64")
        self.assertLess(kernel1, kernel2)

    def test_compare_simple_less_minor_exponent(self):
        kernel1 = version.KernelVersion("3.10.0-1160.95.1.el7.x86_64")
        kernel2 = version.KernelVersion("3.101.0-1160.95.1.el7.x86_64")
        self.assertLess(kernel1, kernel2)

    def test_compare_simple_less_major(self):
        kernel1 = version.KernelVersion("3.10.0-1160.95.1.el7.x86_64")
        kernel2 = version.KernelVersion("4.10.0-1160.95.1.el7.x86_64")
        self.assertLess(kernel1, kernel2)

    def test_compare_simple_less_major_exponent(self):
        kernel1 = version.KernelVersion("3.10.0-1160.95.1.el7.x86_64")
        kernel2 = version.KernelVersion("30.10.0-1160.95.1.el7.x86_64")
        self.assertLess(kernel1, kernel2)

    def test_compare_different_length_build(self):
        kernel1 = version.KernelVersion("3.10.0-957.5.1.el7.x86_64")
        kernel2 = version.KernelVersion("3.10.0-1160.95.1.el7.x86_64")
        self.assertLess(kernel1, kernel2)

    def test_compare_different_build_subversion(self):
        kernel1 = version.KernelVersion("3.10.0-957.el7.x86_64")
        kernel2 = version.KernelVersion("3.10.0-1160.99.1.el7.x86_64")
        self.assertLess(kernel1, kernel2)

    def test_compare_different_length_build_after_dot(self):
        kernel1 = version.KernelVersion("3.10.0-1160.95.1.23.el7.x86_64")
        kernel2 = version.KernelVersion("3.10.0-1160.95.11.23.el7.x86_64")
        self.assertLess(kernel1, kernel2)

    def test_compare_simple_build_vs_short(self):
        kernel1 = version.KernelVersion("3.10.0-1160.95.1.el7.x86_64")
        kernel2 = version.KernelVersion("3.10.0-1160.el7.x86_64")
        self.assertGreater(kernel1, kernel2)

    def test_find_last_kernel(self):
        kernels_strings = [
            "3.10.0-1160.76.1.el7.x86_64",
            "3.10.0-1160.95.1.el7.x86_64",
            "3.10.0-1160.el7.x86_64",
            "3.10.0-1160.45.1.el7.x86_64",
        ]
        kernels = [version.KernelVersion(s) for s in kernels_strings]

        self.assertEqual(str(max(kernels)), "3.10.0-1160.95.1.el7.x86_64")

    def test_sort_kernels(self):
        kernels_strings = [
            "3.10.0-1160.76.1.el7.x86_64",
            "3.10.0-1160.95.1.el7.x86_64",
            "3.10.0-1160.el7.x86_64",
            "3.10.0-1160.45.1.el7.x86_64",
        ]
        kernels = [version.KernelVersion(s) for s in kernels_strings]
        kernels.sort(reverse=True)

        expected = [
            "3.10.0-1160.95.1.el7.x86_64",
            "3.10.0-1160.76.1.el7.x86_64",
            "3.10.0-1160.45.1.el7.x86_64",
            "3.10.0-1160.el7.x86_64",
        ]

        self.assertEqual([str(k) for k in kernels], expected)


class PHPVersionTests(unittest.TestCase):

    def test_php_parse_simple(self):
        php = version.PHPVersion("PHP 5.2")
        self.assertEqual(php.major, 5)
        self.assertEqual(php.minor, 2)

    def test_php_parse_plesk_package(self):
        php = version.PHPVersion("plesk-php52")
        self.assertEqual(php.major, 5)
        self.assertEqual(php.minor, 2)

    def test_php_parse_plesk_package_7(self):
        php = version.PHPVersion("plesk-php70")
        self.assertEqual(php.major, 7)
        self.assertEqual(php.minor, 0)

    def test_php_parse_version_small_string(self):
        php = version.PHPVersion("5.2")
        self.assertEqual(php.major, 5)
        self.assertEqual(php.minor, 2)

    def test_php_parse_version_large_string(self):
        php = version.PHPVersion("5.2.24")
        self.assertEqual(php.major, 5)
        self.assertEqual(php.minor, 2)

    def test_php_parse_wrong_string(self):
        with self.assertRaises(ValueError):
            version.PHPVersion("nothing")

    def test_compare_equal(self):
        php1 = version.PHPVersion("PHP 5.2")
        php2 = version.PHPVersion("PHP 5.2")
        self.assertEqual(php1, php2)

    def test_compare_less_minor(self):
        php1 = version.PHPVersion("PHP 5.2")
        php2 = version.PHPVersion("PHP 5.3")
        self.assertLess(php1, php2)

    def test_compare_less_major(self):
        php1 = version.PHPVersion("PHP 5.2")
        php2 = version.PHPVersion("PHP 6.2")
        self.assertLess(php1, php2)

    def test_compare_less_major_exponent(self):
        php1 = version.PHPVersion("PHP 5.2")
        php2 = version.PHPVersion("PHP 15.2")
        self.assertLess(php1, php2)

    def test_compare_less_major_and_minor(self):
        php1 = version.PHPVersion("PHP 5.2")
        php2 = version.PHPVersion("PHP 6.3")
        self.assertLess(php1, php2)

    def test_compare_less_major_greater_minor(self):
        php1 = version.PHPVersion("PHP 5.2")
        php2 = version.PHPVersion("PHP 6.1")
        self.assertLess(php1, php2)

    def test_compare_less_major_greater_minor_croocked(self):
        php1 = version.PHPVersion("PHP 6.1")
        php2 = version.PHPVersion("PHP 5.2")
        self.assertGreater(php1, php2)
