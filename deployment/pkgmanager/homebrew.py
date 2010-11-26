# -*- coding: utf-8 -*-
from fabric.api import settings, local

from deployment.pkgmanager.base import PkgManagerBase
from deployment.utils import packageline_split

class Homebrew(PkgManagerBase):
    platform = '(all|mac|!win|!apt|!suse|!openbsd)'
    resource = "homebrew"
    pkgmanager = "brew"
    pkgmanageroptions = "install"

    def get_missing_prerequisites(self, packages):
        prerequisites = list(self.get_prerequisites(packages))
        for pkgline in prerequisites:
            pkgname = packageline_split(pkgline)[4]
            result = local("brew list %s &>/dev/null; echo $?" % pkgname)
            if not result.strip() == '0':
                yield pkgline

