# -*- coding: utf-8 -*-

from fabric.api import settings, local

from deployment.pkgmanager.base import PkgManagerBase
from deployment.utils import packageline_split

class OpenBSD(PkgManagerBase):
    platform = '(all|openbsd|!win|!mac|!suse|!apt)'
    resource = "pkg"
    env_vars = 'PKG_PATH="ftp://ftp.wu-wien.ac.at/pub/OpenBSD/`uname -r`/packages/`arch -s`/"'
    pkgmanager = "pkg_add"
    pkgmanageroptions = "-v"

    def get_missing_prerequisites(self, packages):
        prerequisites = list(self.get_prerequisites(packages))
        cmd = "pkg_info|sed -r 's/^(.*)-[0123456789]+.*/\\1/'"
        installed_packages = local(cmd).splitlines()
        for pkgline in prerequisites:
            pkgname = packageline_split(pkgline)[4]
            if '--' in pkgname:
                pkgname, flavor = pkgname.split('--', 1)
            if not pkgname in installed_packages:
                yield pkgline

