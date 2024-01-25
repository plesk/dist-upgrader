# Copyright 2023-2024. WebPros International GmbH. All rights reserved.
# vim:ft=python:

include_defs('//product.defs.py')


python_binary(
    name = 'dist-upgrader.pex',
    platform = 'py3',
    build_args = ['--python-shebang', '/usr/bin/env python3'],
    main_module = 'pleskdistup.main',
    deps = [
        '//pleskdistup:lib',
    ],
)

genrule(
    name = 'dist-upgrader',
    srcs = [':dist-upgrader.pex'],
    out = 'dist-upgrader',
    cmd = 'cp "$(location :dist-upgrader.pex)" "$OUT" && chmod +x "$OUT"',
)

python_test(
    name = 'dist-upgrader.tests',
    srcs = glob(['./tests/*.py']),
    deps = [
        '//pleskdistup:lib',
    ],
    base_module = '',
    main_module = 'tests.test_main',
    platform = 'py3',
)
