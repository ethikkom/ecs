# old legacy update targets
import os
import sys
import posixpath, ntpath

from fabric.api import env, require, cd, run, sudo, settings, hosts
from fabric.utils import abort, warn
from fabric.contrib.files import exists
from deployment.mercurial import repo_clone as _repo_clone

# ecsdev related
#######################################

C_default_update = ['daemonsstop', 'source', 'envboot', 'envupdate', 'dbupdate', 'daemonsstart', 'wsgireload']
C_default_setup = ['daemonstop', 'makedir', 'source', 'envbaseline', 
                   'envclear', 'envboot', 'envupdate', 'apacheconfig', "wsgiconfig" 
                   'dbclear', 'searchconfig', 'dbupdate', 'massimport', 'daemonstart', 'apacherestart']

def help_update():
    ''' show shredder_update, test_update options '''
    print('''
Usage: fab (shredder_update|test_update)[:component[(,components)+]]

Components have a defined order in which they execute, 
no matter in which order you define them. This order is:
    daemonsstop, makedir, source,
    envbaseline, envclear, envboot, envupdate, 
    daemonsconfig, apacheconfig, searchconfig, 
    dbclear, dbupdate, searchupdate, massimport,
    daemonsstart, wsgireload, apacherestart
if you dont specify any components, the default components will get executed:
    '''+ str(C_default_update)+ '''

Often used components: 
 * source       : checks out / updates latest source 
 * envboot      : bootstraps environment 
 * envupdate    : installs any needed package for the environment
 * dbupdate     : does syncdb, migrate & bootstrap 

 * searchconfig : installes/updates search config for solr
 * searchupdate : deletes woosh_index, calls ./manage.py rebuild_index
 * massimport   : does massimport of mai meeting

 * apacheconfig : installes/updates apache config for ecs wsgi application
 * wsgiconfig   : installes/updates main.wsgi and service.wsgi
 * wsgireload   : touches the wsgi script, to force the reload of the wsgi app
 * apacherestart: restarts the webserver (eg. needed after baseline update)

 * daemonsstop  : stops associated daemon processes (celeryd, ecsmail server)
 * daemonsconfig: re/create upstart and sudoers entries for daemon processes 
 * daemonsstart : starts associated daemon processes (celeryd, ecsmail server)

seldom used components:
 * envclear     : *drops* (destroys) and recreates environment
 * dbclear      : *drops* (destroys) and recreates database 
 * envbaseline  : *drops* (destroys) and recreates baseline environment
 * makedir      : make initial directory structure (only needed on setup) 
''')
    

def __config_common():
    '''
    common to all config 
    '''
    env.targetconfdir = env.targetjoin(env.targetbasedir,env.appconfdir)
    env.targetenvdir = env.targetjoin(env.targetbasedir,env.appenvdir)
    env.targetbaselinedir = env.targetjoin(env.targetbasedir,env.appbaselinedir)
    env.targetsrcdir = env.targetjoin(env.targetbasedir,env.appsrcdir)
    env.targetappdir = env.targetjoin(env.targetsrcdir,env.appname)
    env.initialized = env.targetjoin(env.targetconfdir,"env.initialized")
 
    if env.targetjoin == ntpath.join:
        env.activate = "%s\\Scripts\\activate.bat" % env.targetenvdir
        env.manage = "python .\\manage.py" 
    else:
        env.activate = ". %s/bin/activate" % env.targetenvdir
        env.manage = "./manage.py"

        
def __update(components=None):
    ''' 
    __update[:component[(,components)+]], see fab help_update for details
    '''
    with settings(warn_only=True):
        if not components:
            components = C_default_update
            warn("no components specified, using default: %s" % str(components))
            
        if 'daemonsstop' in components:
            run("sudo /sbin/stop %s" % env.appname+ "-mailserver-"+ env.user)
            run("sudo /sbin/stop %s" % env.appname+ "-mainapp_celeryd-"+ env.user)
            
        if 'makedir' in components:
            if not exists(env.initialized):
                with cd(env.targetbasedir):
                    run("mkdir %s; touch %s" % (env.targetconfdir, env.initialized))
                    run("mkdir %s; mkdir %s; mkdir log; mkdir public_html; mkdir .python-eggs" % \
                        (env.targetjoin(env.targetconfdir,"apache.wsgi"), env.targetjoin(env.targetconfdir,"apache.conf")))
                        
        if 'source' in components:
            # TODO: is hardcoded major version, autovm makes same thing in a different place, violates "single source"
            stampversion="""python -c "import sys; id,num,branch=sys.argv[1:4]; print ('ECS_VERSION= \\'0.9-%s-%s-%s\\'' % (num,id,branch))" `hg -q identify --id --num --branch` > ecs/version.py"""
            _repo_clone (env.targetbasedir, env.targetsrcdir, env.apprepo, env.appbranch, stampversion)

        if ('envbaseline' in components):
            abort("unfinished")

        if ('envclear' in components):
            # TODO: refactor whole function to object and run envboot,envupdate after envclear
            run("if test -d %s; then rm -r %s; fi" % (env.targetenvdir, env.targetenvdir))
            run("if test -d %s; then rm -r %s; fi" % (env.targetjoin(env.targetsrcdir, 'download-cache'), env.targetjoin(env.targetsrcdir, 'download-cache')))

        with cd(env.targetsrcdir):
            if ('envboot' in components):               
                run("./bootstrap.py %s" % env.targetenvdir)
            if ('envupdate' in components):
                run("%s; fab appreq:ecs,flavor=%s,only_list=True; fab appenv:ecs,flavor=%s" % (env.activate, env.appenv, env.appenv))
            if ('envupgrade' in components):
                run("%s; fab appenv:ecs,flavor=%s,upgrade=True" % (env.activate, env.appenv))
        
        if 'daemonsconfig' in components:
            abort("unimplemented")
        
        if ('apacheconfig' in components): 
            abort("needs refactoring")
            with cd(env.targetconfdir):
                # FIXME: apache.conf and apache.wsgi should be rendered as template and updated every time we get called here
                run("if test ! -e apache.conf/%s; then cp %s apache.conf/%s; fi" % \
                    ("".join((env.appname,'-',env.apacheconf)), env.targetjoin(env.targetappdir, env.apacheconf), "".join((env.appname,'-',env.apacheconf))))
                # FIXME if we override apache.wsgi, we should think of a safe way to touch the wsgi for reloading the app
                run("if test ! -e apache.wsgi/%s; then cd apache.wsgi; ln -s %s/%s %s; fi" % \
                    ("".join((env.appname,"-",env.appwsgi)), env.targetappdir, env.appwsgi, "".join((env.appname, "-", env.appwsgi))))
 
        if ('wsgiconfig' in components):
            run("%s; cd %s; fab app:ecs,wsgi_config,ecs" % (env.activate, env.targetappdir))
            
        if ('searchconfig' in components):
            with cd(env.targetsrcdir):
                run("%s; cd %s; %s build_solr_schema > %s" % (env.activate, env.targetappdir, env.manage, env.targetjoin(env.targetconfdir, "solr-schema.xml")))
                sudo("cp %s %s" % (env.targetjoin(env.targetconfdir, "solr-schema.xml"), env.targetjoin("/", "etc", "solr", "schema.xml")))
            
        if ('dbclear' in components):
            run("dropdb %s; createdb %s" % (env.user, env.user))
            
        if 'dbupdate' in components:
            with cd(env.targetconfdir):
                run("%s; cd %s; ./manage.py syncdb --noinput; ./manage.py migrate --noinput --all; ./manage.py bootstrap" % (env.activate, env.targetappdir))

        if 'searchupdate' in components:
            with cd(env.targetconfdir):
                run("%s; cd %s; if test -d woosh_index; then rm -rf woosh_index; fi; ./manage.py rebuild_index" % (env.activate, env.targetappdir))

        if 'massimport' in components:
            with cd(env.targetconfdir):
                run("%s; cd %s; ./manage.py massimport -t ../docs/incoming/ethikkommission/legacy_import/mai-meeting.doc", (env.activate, env.targetappdir))
                run("%s; cd %s; ./manage.py massimport -c ../docs/incoming/ethikkommission/legacy_import/mai-meeting.categorize", (env.activate, env.targetappdir))

        if 'daemonsstart' in components:
            run("sudo /sbin/start %s" % env.appname+ "-mainapp_celeryd-"+ env.user)
            run("sudo /sbin/start %s" % env.appname+ "-mailserver-"+ env.user)
            
        if 'wsgireload' in components:
            run("touch %s" % (env.targetjoin(env.targetconfdir,"apache.wsgi","".join((env.appname,"-", env.appwsgi)))))

        if 'apacherestart' in components:
            with cd(env.targetsrcdir):
                run("%s; fab apache:restart" % (env.activate))


# test.ecsdev.ep3.at Deployment (test environment)
########################################
# XXX: in difference to shredder env, in the test env username=databaseusername=databasename!=fabname; this should be corrected (to test)
def __config_test():
    require("user")
    env.appenv = 'testing' # testing packages  
    env.apprepo = 'ssh://%s@ecsdev.ep3.at//home/ecsdev/hg-projects/ecs' % env.user
    env.appbranch = "testing" # testing branch
    (env.appname, env.appwsgi, env.apacheconf) =  ("ecs", "main.wsgi", "apache.conf")
    # FIXME: is hardcoded, should go to ecs/application
    env.appconfdir = "config"
    env.appenvdir = "environment"
    env.appbaselinedir = "baseline"
    env.appsrcdir = "src"
    env.apphostname = "test.ecsdev.ep3.at"
    env.targetjoin = posixpath.join
    env.targetbasedir = env.targetjoin("/home", env.user)
    __config_common()
 

@hosts("testecs@ecsdev.ep3.at")
def test_update(*args):
    '''
    update Stakeholder Test Server; see fab help_update
    USAGE: fab test_update[:component[(,component)+]]
    see fab help_update for components and default component list
    '''
    with settings(warn_only=True):
        components = args if args else None
        __config_test()
        __update(components)


# s.ecsdev.ep3.at Deployment (shredder environment)
########################################
def __config_shredder():
    require("user")
    env.appenv = 'default' # default packages  
    env.apprepo = 'ssh://%s@ecsdev.ep3.at//home/ecsdev/hg-projects/ecs' % env.user
    env.appbranch = "default" # default branch
    (env.appname, env.appwsgi, env.apacheconf) =  ("ecs", "main.wsgi", "apache.conf")
    # FIXME: is hardcoded, should go to ecs/application
    env.appconfdir = "config"
    env.appenvdir = "environment"
    env.appbaselinedir = "baseline"
    env.appsrcdir = "src"
    env.apphostname = "s.ecsdev.ep3.at"
    env.targetjoin = posixpath.join
    env.targetbasedir = env.targetjoin("/home", env.user)
    __config_common()

@hosts("shredder@ecsdev.ep3.at")
def shredder_update(*args):
    '''
    update Shredder Server; see fab help_update
    USAGE: fab shredder_update[:component[(,component)+]]
    see fab update_help for components and default component list
    '''
    with settings(warn_only=True):
        components = args if args else None
        __config_shredder()
        __update(components)
