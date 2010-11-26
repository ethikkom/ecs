# -*- coding: utf-8 -*-

import sys

from deployment.utils import which


def _get_pkg_manager():
    from deployment.pkgmanager.apt import Apt
    from deployment.pkgmanager.zypper import Zypper
    from deployment.pkgmanager.macports import Macports
    from deployment.pkgmanager.homebrew import Homebrew
    from deployment.pkgmanager.windows import Windows
    from deployment.pkgmanager.openbsd import OpenBSD

    supported_systems = (
        ('linux2',   'apt-get', Apt     ),
        ('linux2',   'zypper',  Zypper  ),
        ('darwin',   'brew',    Homebrew),
        ('darwin',   'port',    Macports),
        ('win32',     None,     Windows ),
        ('cygwin',    None,     Windows ),
        ('openbsd4', 'pkg_add', OpenBSD ),
    )

    for platform, command, pkg_manager in supported_systems:
        if sys.platform == platform:
            if not command or len(list(which(command))):
                return pkg_manager()

    return None

pkg_manager = _get_pkg_manager()

