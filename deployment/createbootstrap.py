#!/usr/bin/env python

"""
== SCOPE ==
 * Prerequisites: running python (plus python development on posix machines)
 * Intention: Setup a virtual environment including fabric; All further setup will be done via fabric
 * Target:
   * developer machines
   * buildbot daemons (both linux and windows)
   * virtual machines
   * production target hardware

TODO: FMD1 get --onlyfrozen --nofridge working, check if idempotent calling is working, recognize if inside activated environment, and warn if open files in activated environment
"""

import sys, os, os.path, imp

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

here = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(here)
script_name = os.path.join(base_dir, 'bootstrap.py')
virtualenv = import_from(os.path.join(here, 'virtualenv.py'))


EXTRA_TEXT = """
# is generated, See createbootstrap.py 

import shutil, subprocess
import os, os.path
from optparse import SUPPRESS_HELP

extra_here = os.path.dirname(os.path.abspath(__file__))

def extend_parser(parser):
    parser.add_option("--baseline", action="store_true", dest="baseline_env", default=False, 
        help="Install only mimimal (baseline) environment, useful for WSGI")
    parser.add_option("--clean", action="store_true", dest="wipeout_env", default=False,
        help="Wipeout Destination Directory if existing")

    #parser.add_option("--only-download", action="store_false", dest="try_frozen", default=True,
    #    help="ignore frozen (already downloaded) packages")
    #parser.add_option("--only-frozen", action="store_false", dest="try_download", default=True, 
    #    help="try only frozen (already downloaded) packages, fail if not available")

    parser.add_option("--real", action="store_false", dest="dryrun", default=True,
        help=SUPPRESS_HELP)
    parser.add_option("--environment", action="store_false", dest="dummy", default=True,
        help=SUPPRESS_HELP)
    parser.add_option("--only-show-prereq", action="store_false", dest="dummy", default=True,
        help=SUPPRESS_HELP)

    parser.remove_option("--clear")
    parser.remove_option("--relocatable")
    parser.remove_option("--distribute")
    parser.remove_option("--unzip-setuptools")
    parser.remove_option("--no-site-packages")
    parser.set_defaults(no_site_packages=True, unzip_setuptools=True, use_distribute=True)

    
def adjust_options(options, args):  
    if options.wipeout_env:
        if not args:
            print('requested to delete destination dir, but no destination dir set')
        else:
            if len(args) > 1:
                print('not deleting destinationdir, because multiple args supplied')
            else:
                dir = args[0]
                if os.path.exists(dir):
                    print('Deleting tree %s', dir)
                    shutil.rmtree(dir)
                else:
                    print('Do not need to delete %s; already gone', dir)

def after_install(options, home_dir):
    base_dir = os.path.abspath(home_dir)
    download_store = os.path.join(extra_here, "deployment", "virtualenv_support")

    if sys.platform == 'win32':
        script_dir = os.path.join(base_dir, 'Scripts')
        script_activate = os.path.join(script_dir, 'activate.bat')
    else:
        script_dir = os.path.join(base_dir, 'bin')
        script_activate = os.path.join(script_dir, 'activate')
    fs_ensure_dir(script_dir)

    if not options.baseline_env:
        logger.indent += 2
        try:
            if sys.platform == 'win32':
                pywin32apifilename= 'pywin32-214.win32-py'+str(sys.version_info[0])+ "."+ str(sys.version_info[1])+ '.exe'
                call_subprocess([os.path.abspath(os.path.join(script_dir, 'python')), 
                    os.path.abspath(os.path.join(script_dir,'easy_install-script.py')),
                    '--always-unzip', os.path.join(download_store, pywin32apifilename)],
                    filter_stdout=filter_python_develop,show_stdout=False)
            
                pycryptofilename= 'pycrypto-2.1.0.win32-py'+str(sys.version_info[0])+ "."+ str(sys.version_info[1])+ '.exe'
                call_subprocess([os.path.abspath(os.path.join(script_dir, 'python')), 
                    os.path.abspath(os.path.join(script_dir,'easy_install-script.py')),
                    '--always-unzip', os.path.join(download_store, pycryptofilename)],
                    filter_stdout=filter_python_develop,show_stdout=False)
            else:
                call_subprocess([os.path.abspath(os.path.join(script_dir, 'easy_install')),
                    '--always-unzip', os.path.join(download_store, 'pycrypto-2.1.0.tar.gz')],
                    filter_stdout=filter_python_develop,show_stdout=False)
          
            call_subprocess([os.path.abspath(os.path.join(script_dir, 'pip')),
                'install', os.path.join(download_store, 'bitprophet-fabric-0.9.1-172-gd9472d9.tar.gz')],
                # 'bitprophet-fabric-8556ace.tar.gz')],
                filter_stdout=filter_python_develop,show_stdout=False)
        finally:
            logger.indent -= 2

    etc_dir = os.path.join(base_dir, 'etc')
    bootstrap_config = os.path.join(etc_dir, 'bootstrap.config')
    if not os.path.exists(bootstrap_config):
        fs_ensure_dir(etc_dir)
        logger.notify('Touching %s' % bootstrap_config)
        f = open(bootstrap_config, 'w')
        f.write("bootstrapver=3")
        f.close()

    logger.notify('Run "%s%s" to activate the environment' % (". " if sys.platform != 'win32' else "", script_activate))
    if not options.baseline_env:
        logger.notify('Run "fab developer" to install development packages')

def fs_ensure_dir(dir):
    if not os.path.exists(dir):
        logger.info('Creating directory %s' % dir)
        os.makedirs(dir)

def filter_python_develop(line):
    if not line.strip():
        return Logger.DEBUG
    for prefix in ['Searching for', 'Reading ', 'Best match: ', 'Processing ',
                   'Moving ', 'Adding ', 'running ', 'writing ', 'Creating ',
                   'creating ', 'Copying ']:
        if line.startswith(prefix):
            return Logger.DEBUG
    return Logger.NOTIFY
"""

def main():
    
    text = virtualenv.create_bootstrap_script(EXTRA_TEXT, python_version='2.6')
    if os.path.exists(script_name):
        f = open(script_name)
        cur_text = f.read()
        f.close()
    else:
        cur_text = ''
    print 'Updating %s' % script_name
    if cur_text == text:
        print 'No update'
    else:
        print 'Script changed; updating...'
        f = open(script_name, 'w')
        f.write(text)
        f.close()

if __name__ == '__main__':
    main()
