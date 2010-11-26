# -*- coding: utf-8 -*-
'''
auth functions for fabric
'''

from __future__ import with_statement

from os.path import join as pathjoin
from fabric.api import *
from fabric.utils import abort, warn, fastprint
from fabric.contrib.files import exists, contains, append, comment, uncomment
from .utils import contains_exact, strbool

def user_add(username,options=None):
    ''' add host user, args=username,options=None; default appended options: "--disabled-password --gecos username,,, --quiet" '''
    if options is None:
        add_options = ""
    else:
        add_options = options
    sudo("adduser --disabled-password --quiet --gecos %s,,, %s  %s" % (username, add_options, username))

def user_add_togroup(username,groupname):
    ''' add host user to host group, args=username,groupname '''
    sudo("adduser %s %s" % (username, groupname))

def user_remove_fromgroup(username,groupname):
    ''' remove host user from host group, args=username,groupname '''
    sudo("deluser %s %s" % (username, groupname))

def user_remove(username,purge=False):
    ''' remove host user from host, args=username,purge=False {deletes user group if empty; purge=True deletes files from homedir}'''
    purge = strbool(purge)
    if purge:
        options = "--remove-home"
    else:
        options = ""
    with settings(warn_only=True):
        sudo("deluser %s %s" % (options, username))
        sudo("deluser --only-if-empty --group %s" % (username))

def user_homedir(username):
    ''' get homedir of user; args=username '''
    with settings(hide('warnings','stdout'), warn_only=True):
        output= run('getent passwd %s | sed -re "s/([^:]*:){5}([^:]*):.*/\\2/g"' % (username))
    if output.succeeded:
        return output
    else:
        raise KeyError('could not get homedir for user %s' % (username))

def __get_authorized_file(username):
    homedir = user_homedir(username)
    authorized_dir = pathjoin(homedir,".ssh")
    authorized_file = pathjoin(authorized_dir,"authorized_keys")
    if not exists(authorized_file,use_sudo=True):
        sudo('''targetuser=%s; sshdir=%s; authorized=%s; 
        mkdir -p $sshdir; if test ! -f $authorized; then touch $authorized; chown $targetuser:$targetuser -R $sshdir''' % (username, authorized_dir, authorized_file))
    return authorized_file

def __get_authorized_keys(publickeyfile):
    f = open(publickeyfile); keys= f.readlines(); f.close;
    r = []
    for key in keys:
        key=key.strip("\n")
        if key.strip():
            if key.strip()[0] != "#":
                r.append(key)
    return r

def authorize_add(username, publickeyfile):
    ''' args: (remote) username, (local) publickeyfile; add publickeyfile entries to authorized_keys of user'''
    authorized_file = __get_authorized_file(username)
    keys = __get_authorized_keys(publickeyfile)
    for key in keys:
        disabled_key = "#"+ key
        if contains_exact(authorized_file, disabled_key, use_sudo=True):
            warn("public key commented out, uncommenting it")
            uncomment(authorized_file, key, use_sudo=True)
        elif contains_exact(authorized_file, key, use_sudo=True):
            warn("public key exists and activ, nothing done")
            pass
        else:
            warn("public key does not exist, adding")
            append(authorized_file, key, use_sudo=True)

def authorize_remove(username, publickeyfile):
    ''' args: (remote) username, (local) publickeyfile; remove publickeyfile entries from authorized_keys of user'''
    authorized_file = __get_authorized_file(username)
    keys = __get_authorized_keys(publickeyfile)
    for key in keys:
        if contains_exact(authorized_file, key, use_sudo=True):
            warn("public key exists, commeting it out")
            comment(authorized_file, key, use_sudo=True)
    
def authorize_status(username, publickeyfile):
    ''' args: username,publickeyfile; return list of Boolean if publickey is in authorized_keys'''
    authorized_file = __get_authorized_file(username)
    keys = __get_authorized_keys(publickeyfile)
    r = []
    for key in keys:
        disabled_key = "#"+ key
        if contains_exact(authorized_file, key, use_sudo=True):
            r.append(("Activ",key))
        elif contains_exact(authorized_file, disabled_key, use_sudo=True):
            r.append(("Disabled",key))
        else:
            r.append(("Not-Existing",key))
    warn(str(r))
