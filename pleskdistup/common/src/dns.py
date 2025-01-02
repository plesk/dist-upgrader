# Copyright 2023-2025. WebPros International GmbH. All rights reserved.
import os
from typing import Deque, List
from collections import deque

from . import log


def get_all_includes_from_bind_config(config_file: str, chroot_dir: str = "") -> List[str]:
    includes: List[str] = []

    if os.path.isabs(config_file):
        config_file = chroot_dir + config_file
    else:
        config_file = os.path.join(chroot_dir, config_file)

    if not os.path.exists(config_file):
        return includes

    queue: Deque[str] = deque([config_file])

    while queue:
        current_file = queue.popleft()
        if not os.path.exists(current_file):
            continue

        with open(current_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("include"):
                    include_file = line.split('"')[1]

                    if not os.path.isabs(include_file):
                        log.warn(f"Relative include path directive {line!r} from {current_file!r} is not supported. Skipping.")
                        continue

                    include_file = chroot_dir + include_file

                    includes.append(include_file)
                    queue.append(include_file)

    return includes
