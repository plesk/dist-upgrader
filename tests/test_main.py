# Copyright 2023-2024. WebPros International GmbH. All rights reserved.

import logging
import sys

# Import Buck default test main module
# See https://buck.build/rule/python_test.html
import __test_main__

from pleskdistup.common import log


def init_logger():
    log.init_logger(
        ["tests.log"],
        [],
        loglevel=logging.DEBUG,
    )


def main():
    init_logger()
    __test_main__.main(sys.argv)


if __name__ == '__main__':
    main()
