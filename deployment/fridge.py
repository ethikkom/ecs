# -*- coding: utf-8 -*-
'''
the "fridge"; it eats packages from the internet and stores them for later reuse
'''

import os, sys
import os.path
import hashlib
import shutil
import urllib

from fabric.api import env, settings
from fabric.utils import abort, warn
from fabric.contrib import console

from pip.index import PackageFinder
from pip.req import RequirementSet,InstallRequirement

from deployment.utils import fabdir, import_from, package_merge, packageline_split, strbool


RB_ABORT= "abort-if-existing"
RB_IGNORE= "ignore-if-existing" 
RB_UPDATE= "update-if-different" 
RB_OVERWRITE= "overwrite-existing"
REFILL_BEHAVIOR= (RB_ABORT, RB_IGNORE, RB_UPDATE, RB_OVERWRITE) 

FRIDGE_PLACE = os.path.join('externals', 'fridge') 


def _fridgedir():
    return os.path.join(fabdir(), FRIDGE_PLACE)

def _frozenname(resource, url):
    '''
    hashes resource,url to a filename
    '''
    x = hashlib.md5("".join((resource,url))).hexdigest()
    if url.endswith('.exe'):
        # TODO: easy_install recognizes self-extracting platform binary zip files only if they end with .exe, 
        # we forge this if a original resource url also end with .exe , which works for our sample set
        x += '.exe'
    return x

def _transfer_to_fridge(resource, url, refill_behavior):
    '''
    download any kind of package to the fridge, see refill_fridge for refill_behavior
    '''
    targetpath = os.path.join(_fridgedir(), _frozenname(resource, url))
    if os.path.exists(targetpath):
        if refill_behavior == RB_ABORT:
            abort("could not refill fridge with %s %s , because target already exists and if_exists_abort = True" % (resource, url))
        elif refill_behavior == RB_IGNORE:
            warn("did not refresh fridge with %s %s , because target already exists and reload_existing = False" % (resource, url))
            return
    
    if resource == "pypi":
        req = InstallRequirement.from_line(url)
        pf = PackageFinder([],['http://pypi.python.org/simple'])
        url = pf.find_requirement(req,False).url
    elif resource in ['https', 'http', 'ftp']:
        pass
    
    filename, headers = urllib.urlretrieve(url)
    if os.path.exists(targetpath):
        if refill_behavior == RB_OVERWRITE:
            warn("%s %s already exist and will get overwritten because reload_behavior = %s" % (resource, url, RB_OVERWRITE))
        elif refill_behavior == RB_UPDATE:
            if open(filename,"rb").read() == open(targetpath,"rb").read():
                print ("files %s %s identical, skipped" % (filename, targetpath))
                return
            warn("%s %s already exist and will get overwritten because its different to original and reload_behavior = %s" % (resource, url, RB_UPDATE))
            return
            
    shutil.move(filename, targetpath)
    
       
def _from_fridge(resource, url):
    frozenname = _frozenname(resource, url)
    if os.path.exists(os.path.join(_fridgedir(), frozenname)):
        # print("yummy, taking it from the fridge %s %s" % (resource, url))
        resource = "file"
        url = os.path.join(_fridgedir(), frozenname)
    else:
        raise KeyError('%s %s is not in fridge (%s)' % (resource, url, _frozenname(resource, url)))
    return resource, url
                 
                        
# High Level Functions
#######################

def try_frozen(resource, url):
    '''
    get a frozen package instead of fresh internet package
    
    * if resource is https, http, ftp, pypi
    * if env.fridge_look
    * abort if env.only_frozen but not found
    '''
    
    oldresource, oldurl = resource, url
    
    if not hasattr(env, "fridge_look"):
        env.fridge_look = True
        env.only_frozen = False
      
    if resource in ["https", "http", "ftp", "pypi"]:
        if env.fridge_look:
            if resource == "pypi":
                url=url.replace('\\','')
            try:
                resource, url = _from_fridge(resource, url)
            except KeyError:
                resource, url = oldresource, oldurl
                if env.only_frozen:
                    abort("sorry resource %s %s not found in fridge, and onlyfrozen=True" % (resource, url))

    # return original resource, url if any condition is not met
    return resource, url

def nofridge():
    '''
    disables the usage of the fridge for next fab commands
    eg. fab nofridge appenv:ecs,default gets "fresh" packages from the internet 
    '''
    env.fridge_look = False
    env.only_frozen = False
    
def onlyfrozen():
    '''
    makes usage of the fridge mandatory for next fab commands
    eg. fab onlyfrozen appenv:ecs,default abborts if any package in the list is not available in the fridge 
    '''
    env.fridge_look = True
    env.only_frozen = True
    
def fridge_wipe(force_wipe=False):
    '''
    wipes out fridge_store
    '''
    fdir = os.path.abspath(_fridgedir())
    force_wipe = strbool(force_wipe)
    
    if not os.path.exists(fdir):
        print "No fridge to wipe"
        return
    
    question = "Do you really want to delete the fridge under %s ?" % fdir
    if force_wipe or console.confirm(question, default=False):
        print "Deleting %s" % fdir
        shutil.rmtree(fdir)


def fridge_refill(appname, flavor="default", refill_behavior= RB_IGNORE):
    '''
    refill fridge: appname, flavor, refill_behavior
    
    refill_behavior= 
    "abort-if-existing" abort if file to be downloaded already exists
    "ignore-if-existing" ignore file to be downloaded if already exists 
    "update-if-different" update file if file to be downloaded is unequal stored file 
    "overwrite-existing" download file and overwrite regardless if already there and equal 
    '''
    if refill_behavior not in REFILL_BEHAVIOR:
        abort("refill behavior can be only one of %s" % str(REFILL_BEHAVIOR))
    
    if not os.path.exists(_fridgedir()):
        os.makedirs(_fridgedir())

    appconfigfile = os.path.join(fabdir(), appname, 'application.py')
    appconfig = import_from(appconfigfile)
    try:
        package_bundles = appconfig.package_bundles
    except AttributeError:
        abort('package_bundles is not defined')  
    try:
        package_bundle = package_bundles[flavor]
    except KeyError:
        abort('No flavor "%s"\n' % flavor)
    
    package_bundle= package_merge(package_bundle)
   
    for line in package_bundle.splitlines():       
        (name, pkgtype, platform, resource, url, opt1, opt2) = packageline_split(line)
        if name is None:
            continue
        if resource not in ['https', 'http', 'ftp', 'pypi']:
            continue
        if resource == "pypi":
            url = url.replace('\\','')
        elif resource in ["http", "https", "ftp"]:
            url = "".join((resource,":",url))

        print "freezing ", name, pkgtype, platform, resource, url, opt1, opt2, " as ", _frozenname(resource, url)
        _transfer_to_fridge(resource, url, refill_behavior)
