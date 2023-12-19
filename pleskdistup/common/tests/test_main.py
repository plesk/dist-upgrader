# Copyright 1999-2023. Plesk International GmbH. All rights reserved.

import logging
import sys

import __test_main__

from src import log


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
