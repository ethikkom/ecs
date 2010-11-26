# -*- coding: utf-8 -*-
'''
mercurial functions for fabric
'''

from __future__ import with_statement

import os,sys,re
from os.path import join as pathjoin
from fabric.api import *
from fabric.utils import abort, warn
from fabric.contrib.files import exists

# helper
########################################

# Generic Fab Functions
########################################

def repo_clone(basedir,targetdir,sourceurl,branch="default",postexecstr=None):
    ''' clone/update repository, postexecstr is run with targetdir as currentdir
    magic: deletes all pyc files after clone/update
    warning: will not be successfull if a password is needed '''

    if not exists(targetdir): 
        with cd(basedir):
            run("hg clone %s %s" % (sourceurl,targetdir))
    else:
        with cd(targetdir):
            run("hg pull %s" % sourceurl)
    with cd(targetdir):
        run("hg update %s" % branch)
        run("find . -name '*.pyc' | xargs rm -f")
    if postexecstr:
        with cd(targetdir):
            run(postexecstr)
