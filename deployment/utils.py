# -*- coding: utf-8 -*-
'''
utils functions for fabric
'''

from __future__ import with_statement

import subprocess
import getpass
import platform
import os, sys, tempfile, shutil, imp, errno
from fabric.api import *
from fabric.utils import warn, abort
#from fabric.utils import abort, warn, fastprint
#from fabric.contrib.files import exists, contains, append, comment, uncomment
import tarfile
from functools import wraps

# wrapper & utility
# ###################

def fabdir():
    """ Return directory of running fab file """
    return (os.path.dirname(os.path.abspath(env.real_fabfile)))

def get_homedir():
    if sys.platform in ['win32', 'cygwin']:
        from win32com.shell import shell,shellcon
        home = shell.SHGetFolderPath(0, shellcon.CSIDL_PROFILE, None, 0)
        return home
        #return os.environ['USERPROFILE']
    else:
        return os.environ['HOME']

def deprecated(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        warn('function %s is deprecated' % f.__name__)
        return f(*args, **kwargs)
    return wrapper

def strbool(text):
    ''' return either the boolean value (if isinstance(text,bool) or True if string is one of True or Yes (case insensitiv) or False'''
    if isinstance(text,bool):
        return text
    else:
        text = text.upper()
        return text in ['TRUE', 'YES']

def import_from(filename):
    ''' import python file from filename '''
    path, file = os.path.split(os.path.abspath(filename))
    name, ext = os.path.splitext(file)
    if not os.path.exists(filename):
        raise ImportError, name
    m = imp.load_source(name, filename)
    if not m:
        raise ImportError, name
    return m

def package_merge(packagelist):
    ''' merge package strings together, and sort out duplicates'''
    try:
        from ordereddict import OrderedDict
    except ImportError:
        from deployment.ordereddict import OrderedDict
    
    x= "".join(packagelist)
    y= OrderedDict()
    line = 0
    
    for a in x.splitlines():
        if a.strip():
            if a[0] == "#":
                line+=1
                y.update({a: line})
            else:
                if a not in y:
                    line+=1
                    y.update({a:line})
                else:
                    pass # warn("removing duplicate: "+ str(a))
        else:
            line+=1
            y.update({"": line})
    z = "\n".join(y)
    return z

def packageline_split(packageline):
    name = pkgtype = platform = resource = url = opt1 = opt2 = None
    
    if not packageline.strip() == "": # ignore empty lines
        if not packageline.strip().startswith('#'): # ignore lines beginning with '#'
            (name, dummy, line) = packageline.partition(":")
            (pkgtype, dummy, line) = line.partition(":")
            (platform, dummy, line) = line.partition(":")
            (resource, dummy, line) = line.partition(":")
            (url, dummy, line) = line.partition(":")
            (opt1, dummy, line) = line.partition(":")
            (opt2, dummy, line) = line.partition(":")
            # maxsplit=6 means 7 parameters max (6 expected (but could be empty too), and one for the rest)

    return (name, pkgtype, platform, resource, url, opt1, opt2)


# local functions
# ###############


def clean_pyc(verbose=False):
    '''
    delete all *.pyc, *.pyo files from the fabfile root
    use verbose=True to print each file deleted
    '''
    verbose = strbool(verbose)
    exts = [".pyc", ".pyo"]
    
    for root, dirs, files in os.walk(fabdir()):
        for file in files:
            ext = os.path.splitext(file)[1]
            if ext in exts:
                full_path = os.path.join(root, file)
                if verbose:
                    print full_path
                os.remove(full_path)
             
                
def install_upstart(appname, upgrade=False, use_sudo=True, dry=False):
    ''' install the upstart file for a given application '''
    dirname = os.path.dirname(env.real_fabfile)
    appconfigfile = os.path.join(dirname, appname, 'application.py')
    appconfig = import_from(appconfigfile)

    try:
        upstart_targets = appconfig.upstart_targets
    except AttributeError:
        print 'No upstart targets'
        return
    
    user = getpass.getuser()

    for target in upstart_targets.keys():
        jobname = 'ecs-%s-%s-%s' % (appname, target, user)
        upstart_conf = os.path.join('/', 'etc', 'init', '%s.conf' % jobname)
        upstart_conf_template = os.path.join(os.path.dirname(__file__), 'templates', 'upstart.conf')

        if upgrade == False and os.path.exists(upstart_conf):
            abort('The upstart file "%s" does already exist' % upstart_conf)

        with tempfile.NamedTemporaryFile() as f:
            write_template(upstart_conf_template, f.name, {
                'description': 'ecs-%s-%s-%s' % (appname, target, user),
                'user': user,
                'appdir': os.path.join(dirname, appname),
                'environment': os.environ['VIRTUAL_ENV'],
                'command': upstart_targets[target],
                'target': target,
            })
            if not dry:
                install = ['sudo'] if use_sudo else []
                install += ['install', '-m', '644', '-o', 'root', '-g', 'root', f.name, upstart_conf]
                local(subprocess.list2cmdline(install))

                # (re)start the job
                restart = 'sudo ' if use_sudo else ''
                restart += 'restart %s || ' % jobname
                restart += 'sudo ' if use_sudo else ''
                restart += 'start %s' % jobname
                local(restart)

def apache_setup(appname, use_sudo=True, dry=False, hostname=None, ip=None):
    dirname = os.path.dirname(env.real_fabfile)
    write_template_dir(os.path.join(dirname, appname, 'templates', 'apache2'), os.path.join(dirname, appname, 'apache2'), context={
        'hostname': hostname,
        'ip': ip,
        'user': getpass.getuser(),
        'source': dirname,
        'home': os.path.expanduser('~'),
        'config': '/etc/apache2/ecs',
        'sitepackages': os.path.abspath(os.path.join(dirname, '..', 'environment', 'lib', 'python2.6', 'site-packages')),
        'appname': appname,
    }, preserve_mode=True)
    if not dry:
        cp = ['sudo'] if use_sudo else []
        cp += ['cp', '-RP', os.path.join(dirname, appname, 'apache2'), '/etc']
        local(subprocess.list2cmdline(cp))

def which(file, mode=os.F_OK | os.X_OK, path=None):
    """Locate a file in the user's path, or a supplied path. The function
    yields full paths in which the given file matches a file in a directory on
    the path. on windows it uses the PATHEXT Variable to check for file+ extension
    """
    if not path:
        path = os.environ.get("PATH", os.defpath)
    exts = filter(None, os.environ.get('PATHEXT', '').split(os.pathsep))

    for dir in path.split(os.pathsep):
        full_path = os.path.join(dir, file)
        if os.path.exists(full_path) and os.access(full_path, mode):
            yield full_path
        for ext in exts:
            full_ext = full_path + ext
            if os.path.exists(full_ext) and os.access(full_ext, mode):
                yield full_ext
    
def tarball_create(filename, directories, compression="gz", recursive=True, exclude=None):
    ''' creates/appends to filename, compression can be blank (no), "gz" (gzip) or "bz2" (bzip2)'''
    recursive = strbool(recursive)
    tar = tarfile.open(filename, "".join(("w:",compression)))
    for a in directories:
        tar.add(a, recursive=recursive, exclude=exclude)
    tar.close()

def tarball_extract(filename, destinationdir, compression="gz", members=None):
    ''' extracts tarball filename to destinationdir, compression can be blank (no, "gz" (gzip) or "bz2" (bzip2), default = "gz"'''
    tar = tarfile.open(filename, "".join(("r:",compression)))
    tar.extractall(destinationdir, members)
    tar.close()

def write_template_dir(source_dir, destination_dir, *args, **kwargs):
    for dirpath, dirnames, filenames in os.walk(source_dir):
        relative_path = dirpath[len(os.path.commonprefix([dirpath, source_dir])):].lstrip(os.path.sep)
        target_dir = os.path.join(destination_dir, relative_path)
        if not os.path.isdir(target_dir):
            os.mkdir(target_dir)
        for filename in filenames:
            src_filename = os.path.join(dirpath, filename)
            dst_filename = os.path.join(target_dir, filename)
            if os.path.islink(src_filename):
                link_target = os.readlink(src_filename)
                os.symlink(link_target, dst_filename)
                continue
            write_template(src_filename, dst_filename, *args, **kwargs)

def write_template(source, destination, context=None, use_jinja=False, force=False, preserve_mode=False):
    """ Render a template text file, stolen from fabric.contrib, modified to our needs

    ``source`` should be the path to a text file which may contain Python
    string interpolation formatting and will be rendered with the given context
    dictionary ``context`` (if given.)

    Alternately, if ``use_jinja`` is set to True and you have the Jinja2
    templating library available, Jinja will be used to render the template
    instead. 

    The resulting rendered file will be copied if different from the contents
    of the ``destination`` filename to the ``destination`` filename.
    If the destination file already exists, it will be renamed with a ``.bak``
    extension.

    If force == True, then ``destination`` file will always be overwritten 
    regardless if different

    """
    use_jinja = strbool(use_jinja)
    force = strbool(force)
    abssource = os.path.abspath(source)
    basename = os.path.basename(abssource)
    dirname = os.path.dirname(abssource)

    # This temporary file should not be automatically deleted on close, as we
    # need it there to upload it (Windows locks the file for reading while open).
    tempfile_fd, tempfile_name = tempfile.mkstemp()
    output = open(tempfile_name, "w+b")

    text = None
    if use_jinja:
        try:
            from jinja2 import Environment, FileSystemLoader
            jenv = Environment(loader=FileSystemLoader(dirname))
            text = jenv.get_template(basename).render(**context or {})
        except ImportError, e:
            abort("tried to use Jinja2 but was unable to import: %s" % e)
    else:
        with open(abssource) as inputfile:
            text = inputfile.read()
        if context:
            text = text % context
    output.write(text)
    output.close()
    os.close(tempfile_fd)

    if os.path.exists(destination):
        f = open(destination)
        old_text = f.read()
        f.close()
    else:
        old_text = None

    if old_text == text and not force:
        warn('not updating %s , because identical output and force=False' % destination)
        os.remove(tempfile_name)
    else:
        if os.path.exists(destination):
            shutil.copyfile(destination, "".join((destination,".bak")))
        shutil.move(tempfile_name, destination)
        if preserve_mode:
            source_mode = os.stat(source).st_mode
            os.chmod(destination, source_mode)

        
# remote functions
# #################

def apache(command="status", use_sudo=True):
    ''' Remote Control Apache, command=(reload|restart|start|stop|status),use_sudo=True '''
    APACHE_COMMANDS= ('reload', 'restart', 'start', 'stop', 'status')
    use_sudo = strbool(use_sudo)
    if command not in APACHE_COMMANDS:
        abort("unkown command %s for apache" % (command))
    else:
        if use_sudo:
            sudo("/etc/init.d/apache2 %s" % (command),shell=False)
        else:
            run("/etc/init.d/apache2 %s" % (command),shell=False)

def contains_exact(filename, text, use_sudo=False, exact=True):
    ''' args: filename, text, use_sudo=False; returns Boolean:True if file contains text, uses grep -qG '''
    use_sudo = strbool(use_sudo)
    exact = strbool(exact)
    r = "grep -qG -- '%s' %s" % (text, filename)
    with settings(hide('warnings'), warn_only=True):
        if use_sudo:
            output=sudo(r)
        else:
            output=run(r)
    return(output.succeeded)

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST:
            pass
        else: raise

def get_pythonexe():
    ''' return python executable '''
    return os.path.normpath(sys.executable)
    
def get_pythonenv():
    ''' get root of python environment (currently running) '''
    try:
        virtualenv_path = os.environ['VIRTUAL_ENV']
    except KeyError:
        raise Exception('You are not inside a virtual environment')    
    
    return virtualenv_path

