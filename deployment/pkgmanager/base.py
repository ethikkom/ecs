# -*- coding: utf-8 -*-

import sys
import os
import re
from fabric.api import local, settings, abort, warn

from deployment.utils import packageline_split, fabdir
from deployment.fridge import try_frozen

def _abort_failed(result):
    if result.failed:
        abort("Failed, Code %d, Log: %s" % (result.return_code, "".join((result.stdout,result.stderr))))
 
class PkgManagerBase(object):
    platform = '(all|!win|!apt|!mac|!suse|!openbsd)'
    resource = "false"
    env_vars = ""
    pkgmanager = "false"
    pkgmanageroptions = ""
    easy_install = 'easy_install'

    def _report_missing(self, missing, warn_only=False):
        if warn_only:
            warn(missing)
        else:
            abort(missing)

    def get_prerequisites(self, packages):
        for packageline in packages.splitlines():
            (name, pkgtype, platform, resource, _, _, _) = packageline_split(packageline)
            if name is None:
                continue
            if pkgtype == 'req' and re.match(self.platform, platform) and re.match(self.resource, resource):
                yield packageline

    def get_missing_prerequisites(self, packages):
        raise NotImplementedError

    def get_prerequisites_status(self, packages):
        preq_list = []
        missing_prerequisites = set(self.get_missing_prerequisites(packages))
        for preq in self.get_prerequisites(packages):
            if preq in missing_prerequisites:
                preq_list.append(('m', preq,))
            else:
                preq_list.append(('i', preq))
        return preq_list
    
    def check_prerequisites(self, packages, warn_only=True, verbose=True):
        if verbose:
            print 'Information: Checking if prerequisites are installed'
        for pkgline in self.get_missing_prerequisites(packages):
            self._report_missing("missing package: %s" % pkgline, warn_only)

    def install_prerequisites(self, packages, use_sudo=True):
        sudooption = "sudo" if use_sudo else ""
        pkg_list = ' '.join([packageline_split(x)[4] for x in self.get_missing_prerequisites(packages)])
        if pkg_list:
            with settings(warn_only=True):
                result = local("%s %s %s %s %s" % (sudooption, self.env_vars, self.pkgmanager, self.pkgmanageroptions, pkg_list))
            print(result.stdout)
            if result.failed:
                print(result.stderr)
                abort("Install of prerequisites failed")
    
    def get_packages(self, packages):
        for pkgline in packages.splitlines():
            (name, pkgtype, platform, resource, url, opt1, opt2) = packageline_split(pkgline)
            if name is None:
                continue
            if re.match(self.platform, platform):
                if pkgtype == 'inst' or pkgtype == 'instbin':
                    yield pkgline

    def install_packages(self, packages, upgrade=False):
        upgradeoption = ""
        if upgrade: upgradeoption= "--upgrade"
        
        for packageline in self.get_packages(packages):
            (name, pkgtype, platform, resource, url, opt1, opt2) = packageline_split(packageline)
            if resource in ["pypi"]:
                pass
            elif resource in ["http", "https", "ftp"]:
                url = "".join((resource,":",url))
            elif resource in ["file", "dir"]:
                url = os.path.join(fabdir(), url)
            else:
                abort("unimplemented resource %s" % (resource))        

            # try to take package from the fridge (externals/frozen)
            resource, url = try_frozen(resource,url)
            
            if pkgtype == "inst":
                print("Information: installing %s from %s on matching platform %s" % (name, resource, platform))
                if resource in ["pypi", "http", "https", "ftp"]:        
                    with settings(warn_only=True):
                        if resource == "pypi":
                            if sys.platform == "win32":
                                url=url.replace('\\','^')
                            else:
                                url="".join(('"',url,'"'))
                                url=url.replace('\\','')
                        result=local('pip install --no-deps %s %s' % (upgradeoption, url))
                elif resource in ["file", "dir"]:
                    with settings(warn_only=True):
                        result=local('%s --always-copy --always-unzip --no-deps %s' % (self.easy_install, url))
                else:
                    abort("unimplemented resource %s" % (resource))
                _abort_failed(result)
                
            elif pkgtype == "instbin":
                if resource in ["http", "https", "ftp", "file"]:    
                    with settings(warn_only=True):
                        result=local('%s --always-copy --always-unzip --no-deps %s' % (self.easy_install, url))                    
                    _abort_failed(result)
                else:
                    abort("unimplemented resource %s" % (resource))

            else:
                warn("unimplemented package type %s in line: %s" % (pkgtype, packageline))

