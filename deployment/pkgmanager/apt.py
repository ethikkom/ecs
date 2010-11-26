# -*- coding: utf-8 -*-

from fabric.api import settings, local

from deployment.pkgmanager.base import PkgManagerBase
from deployment.utils import packageline_split

class Apt(PkgManagerBase):
    platform = '(all|apt|!win|!mac|!suse|!openbsd)'
    resource = "apt-get"
    env_vars = "DEBIAN_FRONTEND=noninteractive"
    pkgmanager = "apt-get"
    pkgmanageroptions = "-y -q install"

    def get_missing_prerequisites(self, packages):
        prerequisites = list(self.get_prerequisites(packages))
        for pkgline in prerequisites:
            pkgname = ' '.join(packageline_split(pkgline)[4].split(','))
            with settings(warn_only=True):
                result = local("dpkg -l %s >/dev/null 2>/dev/null" % pkgname)
            if result.failed:
                yield pkgline
            
