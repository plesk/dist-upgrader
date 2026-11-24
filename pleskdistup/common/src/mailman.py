# Copyright 2026. WebPros International GmbH. All rights reserved.
"""Settings of mailman-web, the Django application behind Postorius and HyperKitty."""
import os
import re

MAILMAN_WEB_CONFIG = "/etc/mailman3/mailman-web.py"
ALLAUTH_ACCOUNT_MIDDLEWARE = "allauth.account.middleware.AccountMiddleware"

# We expect exactly this format, since the Plesk bootstrapper writes it like this,
# and we don't want to support custom mailman 3 installations, at least for now.
_MIDDLEWARE_START_RE = re.compile(r"^\s*MIDDLEWARE\s*=\s*[(\[]\s*$", re.MULTILINE)


def config_lacks_middleware(middleware: str, config_path: str = MAILMAN_WEB_CONFIG) -> bool:
    """Whether the config defines a multi-line MIDDLEWARE without the given middleware."""
    if not os.path.exists(config_path):
        return False

    with open(config_path) as f:
        content = f.read()
    return _MIDDLEWARE_START_RE.search(content) is not None and middleware not in content


def add_middleware(middleware: str, config_path: str = MAILMAN_WEB_CONFIG) -> None:
    """Insert the middleware as the first entry of the multi-line MIDDLEWARE."""
    with open(config_path) as f:
        content = f.read()

    match = _MIDDLEWARE_START_RE.search(content)
    if match is None:
        return

    with open(config_path, "w") as f:
        f.write(content[:match.end()] + f"\n    '{middleware}'," + content[match.end():])
