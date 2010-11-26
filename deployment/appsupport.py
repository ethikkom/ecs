### APP INTERFACE ###
# in every application folder there is a file called "application.py".
# the "appenv" coomand imports the package_bundles dictionary from that file
#
# eg.:
#
# package_bundles = {
#     'default': """
# jinja2:inst:all:pypi:jinja2
# buildbot:inst:all:pypi:buildbot
#     """,
# }
#
# install the default package bundle of the ecs application
# $ fab appenv:ecs
#
# to install the developer bundle type
# $ fab appenv:ecs,flavor=developer
#

import os
import subprocess
import tempfile
import getpass
import platform

from fabric.api import env, local
from fabric.utils import abort

from deployment.install import install_packages, install_prerequisites, list_prerequisites
from deployment.utils import import_from, strbool, write_template, write_template_dir

### helpers ###

def _get_appconfig(appname):
    dirname = os.path.dirname(env.real_fabfile)
    appconfigfile = os.path.join(dirname, appname, 'application.py')
    appconfig = import_from(appconfigfile)
    return appconfig

def _get_package_bundle(appname, flavor='default'):
    appconfig = _get_appconfig(appname)

    try:
        package_bundles = appconfig.package_bundles
    except AttributeError:
        abort('package_bundles is not defined')
    
    try:
        package_bundle = package_bundles[flavor]
    except KeyError:
        abort('No flavor "%s"\n' % flavor)

    return package_bundle


### fab targets ###

def app(appname, action, *args, **kwargs):
    ''' execute application specific function
    usage: action, *args, **kwargs
    '''
    appconfig = _get_appconfig(appname)

    if hasattr(appconfig, action):
        getattr(appconfig, action).__call__(*args, **kwargs)
    else:
        abort('Error: There is no action "%s"\n' % action)

def appreq(appname, flavor='default', only_list=False, use_sudo=True):
    ''' install the prerequisites of an environment for an given application
    usage: appname, flavor="default", only_list=False, use_sudo=True
    '''
    only_list = strbool(only_list)
    use_sudo = strbool(use_sudo)

    package_bundle = _get_package_bundle(appname, flavor)
    install_prerequisites(package_bundle, only_list, use_sudo)

def appreqlist(appname, flavor='default'):
    package_bundle = _get_package_bundle(appname, flavor)
    list_prerequisites(package_bundle)

def appenv(appname, flavor='default', upgrade=False, ignore_missing_prerequisites=False):
    ''' install the environment for an given application
    usage: appname, flavor="default", upgrade=False, ignore_missing_prerequisites=False
    '''
    upgrade = strbool(upgrade)
    ignore_missing_prerequisites = strbool(ignore_missing_prerequisites)

    package_bundle = _get_package_bundle(appname, flavor)
    install_packages(package_bundle, upgrade, ignore_missing_prerequisites)

def appsys(appname, use_sudo=True, dry=False, hostname=platform.node(), ip='127.0.0.2'):
    ''' do the system setup for a given app '''
    use_sudo = strbool(use_sudo)
    dry = strbool(dry)

    appconfig = _get_appconfig(appname)

    try:
        system_setup = appconfig.system_setup
    except AttributeError:
        pass
    else:
        system_setup(appname, use_sudo=use_sudo, dry=dry, hostname=hostname, ip=ip)

def apptest(appname, flavor='default'):
    ''' run the test for an application '''
    appconfig = _get_appconfig(appname)

    try:
        test_flavors = appconfig.test_flavors
    except AttributeError:
        abort('test_flavors is not defined')
    
    try:
        test_flavor = test_flavors[flavor]
    except KeyError:
        abort('No flavor "%s"\n' % flavor)

    testp = subprocess.Popen(test_flavor, cwd=os.path.join(dirname, appname), shell=True)
    testp.wait()

