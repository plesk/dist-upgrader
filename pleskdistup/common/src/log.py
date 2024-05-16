# Copyright 2023-2024. WebPros International GmbH. All rights reserved.
import logging

import typing


class logger():
    files_logger = logging.getLogger("distupgrade_files")

    is_streams_enabled = False
    streams_logger = logging.getLogger("distupgrade_streams")

    @staticmethod
    def init_logger(logfiles: typing.List[str], streams: typing.List[typing.Any],
                    console: bool = False, loglevel: int = logging.INFO) -> None:
        logger.files_logger.setLevel(loglevel)
        logger.streams_logger.setLevel(loglevel)

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        file_handlers = []
        for logfile in logfiles:
            file_handlers.append(logging.FileHandler(logfile))

        stream_handlers: typing.List[logging.StreamHandler] = [logging.FileHandler('/dev/console', mode='w')] if console else []
        for stream in streams:
            stream_handlers.append(logging.StreamHandler(stream))
        if len(stream_handlers):
            logger.is_streams_enabled = True

        for handler in file_handlers + stream_handlers:
            handler.setFormatter(formatter)

        for handler in file_handlers:
            logger.files_logger.addHandler(handler)

        for handler in stream_handlers:
            logger.streams_logger.addHandler(handler)

    @staticmethod
    def reinit_logger(logfiles: typing.List[str], streams: typing.List[typing.Any],
                      console: bool = False, loglevel: int = logging.INFO) -> None:
        logger.files_logger = logging.getLogger("distupgrade_files")
        logger.streams_logger = logging.getLogger("distupgrade_streams")
        logger.init_logger(logfiles, streams, console, loglevel)

    @staticmethod
    def debug(msg: str, to_file: bool = True, to_stream: bool = True) -> None:
        if to_file:
            logger.files_logger.debug(msg)

        if to_stream and logger.is_streams_enabled:
            logger.streams_logger.debug(msg)

    @staticmethod
    def info(msg: str, to_file: bool = True, to_stream: bool = True) -> None:
        if to_file:
            logger.files_logger.info(msg)

        if to_stream and logger.is_streams_enabled:
            logger.streams_logger.info(msg)

    @staticmethod
    def warn(msg: str, to_file: bool = True, to_stream: bool = True) -> None:
        if to_file:
            logger.files_logger.warn(msg)

        if to_stream and logger.is_streams_enabled:
            logger.streams_logger.warn(msg)

    @staticmethod
    def err(msg: str, to_file: bool = True, to_stream: bool = True) -> None:
        if to_file:
            logger.files_logger.error(msg)

        if to_stream and logger.is_streams_enabled:
            logger.streams_logger.error(msg)


def init_logger(logfiles: typing.List[str], streams: typing.List[typing.Any],
                console: bool = False, loglevel: int = logging.INFO) -> None:
    logger.init_logger(logfiles, streams, console, loglevel)


def reinit_logger(logfiles: typing.List[str], streams: typing.List[typing.Any],
                  console: bool = False, loglevel: int = logging.INFO) -> None:
    logger.reinit_logger(logfiles, streams, console, loglevel)


def debug(msg: str, to_file: bool = True, to_stream: bool = True) -> None:
    logger.debug(msg, to_file, to_stream)


def info(msg: str, to_file: bool = True, to_stream: bool = True) -> None:
    logger.info(msg, to_file, to_stream)


def warn(msg: str, to_file: bool = True, to_stream: bool = True) -> None:
    logger.warn(msg, to_file, to_stream)


def err(msg: str, to_file: bool = True, to_stream: bool = True) -> None:
    logger.err(msg, to_file, to_stream)
