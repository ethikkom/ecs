# -*- coding: utf-8 -*-

from deployment.pkgmanager.base import PkgManagerBase

class Macports(PkgManagerBase):
    platform = '(all|mac|!win|!apt|!suse|!openbsd)'
    resource = "macports"
    pkgmanager = "port"
    pkgmanageroptions = "install"

    def get_missing_prerequisites(self, packages):
        prerequisites = list(self.get_prerequisites(packages))
        for pkgline in prerequisites:
            pkgname = packageline_split(pkgline)[4]
            result = local("port installed '%s' 2>/dev/null|grep '(active)'|wc -l" % pkgname)
            if not result.strip() == '1':
                yield pkgline

