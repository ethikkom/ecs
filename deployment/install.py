# -*- coding: utf-8 -*-
'''
install functions for fabric
'''

from __future__ import with_statement

import os,sys,re
from urlparse import urlparse
from urllib import urlretrieve

from fabric.api import warn, abort, settings, local
from deployment.utils import strbool, fabdir, which, packageline_split, get_pythonenv

from deployment.pkgmanager import pkg_manager

   
def install_conf(conffile, upgrade=False, ignore_missing_prerequisites=False, only_postconfig=False):
    ''' install a legacy .conf file '''
    
    def install_postconfig(postconfigdata):
        ''' run a postconfig string, internal '''
        postconfig= 'PYTHONENV=%s; PYTHONVER=%s; FABDIR=%s; '+postconfigdata
        pythonver = '%d.%d' % sys.version_info[:2]
        postconfig= postconfig % (get_pythonenv(), pythonver, fabdir())
        result= local(postconfig, capture=False)
        _abort_failed(result)

    upgrade = strbool(upgrade)
    ignore_missing_prerequisites = strbool(ignore_missing_prerequisites)
    only_postconfig = strbool(only_postconfig)

    with open(conffile) as f:
        data= f.read()

    depstart= re.search('#DEPENDENCIES-BEGIN', data, re.MULTILINE)
    depend = re.search('#DEPENDENCIES-END', data, re.MULTILINE)
    if (depstart is None) or (depend is None):
        abort("Can not find dependencies begin or end (#DEPENDENCIES-BEGIN/#DEPENDENCIES-END) in conffile")
    packagelist= data[depstart.end():depend.start()]

    configstart= re.search('#POSTCONFIG-BEGIN', data, re.MULTILINE)
    configend = re.search('#POSTCONFIG-END', data, re.MULTILINE)
    if (configstart is not None) and (configend is not None):
        warn("Found postconfig")
        postconfig= data[configstart.end():configend.start()]
    else:
        postconfig= ""
    
    if not only_postconfig:
        install_packages(packagelist, upgrade, ignore_missing_prerequisites)
    if postconfig:
        install_postconfig(postconfig)


def install_prerequisites(packages, only_list=False, use_sudo=True):
    ''' Install the prerequisites of a package list; Usage: install_prerequisites:packages,only_list=False,use_sudo=True '''
    only_list = strbool(only_list)
    use_sudo = strbool(use_sudo)

    if pkg_manager is None:
        abort("No pkt manager found for your system, you're on your own")

    if only_list:
        pkg_manager.check_prerequisites(packages, warn_only=only_list)
    else:
        pkg_manager.install_prerequisites(packages, use_sudo=use_sudo)

           
def install_packages(packages, upgrade=False, ignore_missing_prerequisites=False):
    ''' Install a packagelist localy; Usage: install_packages:packages,upgrade=False,ignore_missing_prerequisites=False
    # WARNING: pypi version using < or > needs a backslash prepended !
    '''
    upgrade = strbool(upgrade)
    ignore_missing_prerequisites = strbool(ignore_missing_prerequisites)

    if pkg_manager is None:
        warn("No pkt manager found for your system, you're on your own")
    else:
        pkg_manager.check_prerequisites(packages, warn_only=ignore_missing_prerequisites)

    pkg_manager.install_packages(packages)

def list_prerequisites(packages):
    for preq in pkg_manager.get_prerequisites_status(packages):
        print '%s %s' % preq

def install_list():
    ''' List installed python packages '''
    local('pip freeze', capture=False)

