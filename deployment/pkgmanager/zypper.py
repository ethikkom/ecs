# -*- coding: utf-8 -*-

from fabric.api import local, settings

from deployment.pkgmanager.base import PkgManagerBase
from deployment.utils import packageline_split

class Zypper(PkgManagerBase):
    platform = '(all|suse|!win|!apt|!mac|!openbsd)'
    resource = "zypper"
    pkgmanager = "zypper"
    pkgmanageroptions = "--quiet --non-interactive install"

    def get_missing_prerequisites(self, packages):
        prerequisites = list(self.get_prerequisites(packages))
        for pkgline in prerequisites:
            pkgname = packageline_split(pkgline)[4]
            with settings(warn_only=True):
                # using the rpm tool directly is much faster then using zypper
                result = local("rpm -q %s >/dev/null 2>/dev/null" % pkgname)
            if result.failed:
                yield pkgline

