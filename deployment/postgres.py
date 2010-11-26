# -*- coding: utf-8 -*- 
''' 
postgres sql functions for fabric 
'''

from __future__ import with_statement

from fabric.api import *

def sql_run(data):
    ''' run an sql command as sudo -u postgres on user@host '''
    require("hosts","user")
    psqlcmd = '/usr/bin/psql -d template1 -c '
    sudo("".join((psqlcmd,'"',data,'"')), shell=False, user="postgres")

def sql_dropdb(dbname):
    """ Purges Database from SQL Server; usage: dbname"""
    with settings(warn_only=True):
        sql_run('drop database %s;' % (dbname))

def sql_dropuser(dbuser):
    """ Purges database user from SQL Server; usage: dbuser"""
    with settings(warn_only=True):
        sql_run('drop user %s;' % (dbuser))

def sql_createdb(dbname, dbuser, dbpassword=None):
    ''' Creates an postgres database dbname, owned by user dbuser; if dbpassword is set, then user will be created too'''
    with settings(warn_only=True):
        if dbpassword:
            sql_createuser(dbuser,dbpassword)
        sql_run('create database %s with owner %s;' %  (dbname, dbuser))

def sql_createuser(dbuser, dbpassword):
    ''' Creates an postgres database user, and sets password to dbpassword; is idempotent'''
    with settings(warn_only=True):
        sql_run('create user %s;' % (dbuser))
        sql_run('alter user %s with password \'%s\';' % (dbuser, dbpassword))
