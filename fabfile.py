#!/usr/bin/env python
'''
ECS-Project Master Fabric File 

'''

from __future__ import with_statement

import os, sys
import posixpath, ntpath

from fabric.utils import abort, warn

from deployment.utils import fabdir as _fabdir
from deployment.utils import strbool as _strb

from deployment.utils import clean_pyc
from deployment.appsupport import app, appenv, appreq, appsys, apptest, appreqlist
from deployment.fridge import nofridge, onlyfrozen, fridge_refill, fridge_wipe
from deployment.ada import ticket

from update_targets import help_update, shredder_update, test_update


# execute fab foo if this file is being called directly
if __name__ == '__main__':
    FABRIC = 'fab'
    argv = [FABRIC] + sys.argv[1:]
    os.execvp(FABRIC, argv)
# abort if virtualenv is not active
if not 'VIRTUAL_ENV' in os.environ.keys():
    abort('virtualenv is not active')


# General
#######################################

def t(*args, **kwargs):
    ''' shortcut for ticket , see fab ticket:help '''
    ticket(*args,**kwargs) 
    
def developer(upgrade=False):
    ''' shortcut for fab appenv:ecs,flavor=developer '''
    appenv('ecs', flavor='developer', upgrade=upgrade)

def fixmefinder(verbose=False):
    '''print a sorted list of counted FIXME's TODO's & XXX's'''
    from deployment.fixmefinder import FixmeFinder
    verbose = _strb(verbose)
    ff = FixmeFinder(_fabdir(), None, False)
    ff.find_fixmes(output_matched_lines=verbose)  

def coveragefinder():
    '''print a sorted list of unit test coverage'''
    from deployment.coveragefinder import CoverageFinder
    coveragefile = os.path.join(_fabdir(), "coverage.xml")
    if not os.path.exists(coveragefile):
        abort("""
you need to generate a ecs/coverage.xml file to use coveragefinder: to make one,
add 'NOSE_ARGS=("--with-xunit",)' into your local_settings.py
run 'fab appenv:ecs,quality_addon' once per environment creation and 
run 'oppath="$PYTHONPATH"; PYTHONPATH=`pwd`; coverage run ecs/manage.py test; PYTHONPATH="$oppath"'
        """)
    cf = CoverageFinder(coveragefile, _fabdir(), IGNORE_INIT_PY=True)
    cf.parse()
    cf.output() 


    
