# autovm

import os
import subprocess
import stat
import shutil
import time
import os.path
import platform
import tempfile
from fabric.api import local, settings
from fabric.utils import abort, warn
from deployment.utils import strbool, write_template
import inspect


_system_bundle = """
python-vm-builder:req:apt:apt-get:python-vm-builder
qemu:req:apt:apt-get:qemu
qemu:req:win:http://homepage3.nifty.com/takeda-toshiya/qemu/qemu-0.13.0-windows.zip:unzipflat:qemu.exe
qemu-kvm:req:apt:apt-get:qemu-kvm
openssh-client:req:apt:apt-get:openssh-client
jinja2:inst:all:pypi:jinja2
"""

package_bundles = {
    'default': _system_bundle,
    'system': _system_bundle,
}


VMBUILDER_OS = 'ubuntu'
VMBUILDER_HYPERVISOR = 'kvm' # FIXME: switched back to kvm, to keep testscripts running, this should go to 'vmserver' and have kvm/virtualbox support scripts added
VMHOSTKEY = 'vmhostkey'
CHROOT_TARGET = 'prebuilt-chroot'

APPLICATIONS = ['ecs', 'signing']
VM_USER = 'ecsdev'

def help():
    print ''' create a application with the application inside
Usage: fab app:autovm,command[,options]

commands:
  * make_tarball[targetdir,revision,overwrite]
    Creates the source tarball. revision is the source revision you want to bundle
  * createvm[application,use_sudo,hypervisor,revision,hostname,ip,onlychrootcreate,useexistingchroot]
    Creates a virtual machine with the given parameters. If onlychroot is True
    the process of building the vm image is skipped.
  * getshell[running,snapshot,hypervisor]
    Starts the virtual machine (if not already running) and connects via ssh
  * dotests[application,hypervisor]
    Runs the tests for a given application 
  * deletechroot
    Delete the chroot created by $ fab app:autovm,createvm,onlychroot=True
  * deletevm[hypervisor]
    Delete the created virtual machine

Hypervisor has to be one of qemu/kvm/vmserver/virtualbox.

    '''

def _sourcedir():
    dirname=os.path.dirname(os.path.abspath(__file__))
    return dirname

def _targetdir():
    if platform.node() == "ecsdev.ep3.at":
        import getpass
        user = getpass.getuser()
        dirname=os.path.join("/scratch/public-scratch/", user)
        warn("using %s as workingdir" % dirname)
        if not os.path.exists (dirname):
            warn("creating %s as workingdir" % dirname)
            os.makedirs (dirname)
    else:
        warn("using your currentdir as working dir for the vm creation, beware of big files")
        dirname=os.path.dirname(os.path.abspath(__file__))

    freesize = os.statvfs(dirname).f_bfree * os.statvfs(dirname).f_bsize
    if freesize < (2 ** 34):
        abort("sorry, less than 16 Gigabyte of freespace on working drive %s" % dirname)
    return dirname

def _run(args, cwd=None):
    command = subprocess.list2cmdline(args)
    if cwd:
        command = '%s && %s' % (subprocess.list2cmdline(['cd', cwd]), command)

    with settings(warn_only=True):
        p = local(command, capture=False)

    if p.failed:
        raise ValueError('Failed executing: \'%s\'' % command)

def _get_current_revision():
    dirname = _sourcedir()
    p = subprocess.Popen(['hg', '-q', 'identify', '--num'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=dirname)
    revision = p.communicate()[0].strip().strip('+')
    return revision


class RunningVM(object):
    def __init__(self, hypervisor, snapshot=False):
        self.snapshot = snapshot
        self.process = None
        self.targetdirname = _targetdir()
        self.sourcedirname = _sourcedir()
        self.vmbuilderhypervisor = hypervisor
        super(RunningVM, self).__init__()

    def __enter__(self):
        self._start()
        return self   # So, "with RunningVM() as vm" works

    def __exit__(self, type, value, traceback):
        self._stop()
        return False   # don't supress exceptions

    def _start(self):
        print 'Starting vm'
        start_vm = ['./run.sh',  # FIXME: this only works with kvm/qemu
            '-nographic',
            '-net', 'nic',
            '-net', 'user,hostfwd=tcp:127.0.0.1:42022-:22',
        ]
        if self.snapshot:
            start_vm.append('-snapshot')

        self.process = subprocess.Popen(start_vm, cwd=os.path.join(self.targetdirname, VMBUILDER_OS+ "-"+ self.vmbuilderhypervisor), stdin=subprocess.PIPE)
        time.sleep(30) # FIXME: hardcoded sleep time; we are waiting for the vm to start up

    def _stop(self):
        print 'Stopping VM'
        if not self.process:
            raise RuntimeError('The vm is not running')

        self.process.terminate()
        self.process.wait()
        self.process = None

    def do(self, commands, user=None):
        if not self.process:
            raise RuntimeError('The vm is not running')

        command = '; '.join(commands)
        if user:
            command = subprocess.list2cmdline(['sudo', 'su',  '-', user, '-c', command])

        ssh = ['ssh', 'localhost',
            '-o', 'NoHostAuthenticationForLocalhost=yes',
            '-i', os.path.join(self.targetdirname, VMHOSTKEY),
            '-p', '42022',
            '-l', VM_USER,
            command,
        ]

        _run(ssh)

def make_tarball(targetdir, revision=None, overwrite=False):
    """ returns filename of created tarball, use overwrite=True to overwrite existing tarball, uses current revision if revision=None """
    if not revision:
        revision = _get_current_revision()

    tarball = os.path.join(targetdir, 'src-%s.tar.bz2' % revision)
    tarballcmd = ['hg', 'archive',
        '-t', 'tbz2',
        '-r', revision, 
        tarball,
    ]

    if os.path.exists(tarball) and not overwrite:
        return tarball

    _run(tarballcmd, cwd=_sourcedir())
    return tarball


def createvm(application='ecs', use_sudo=True, hypervisor=VMBUILDER_HYPERVISOR, revision=None, hostname=None, ip=None, onlychrootcreate=False, useexistingchroot=True):
    VMBUILDER_CONFIG = 'vmbuilder.cfg'
    POSTINSTALL_FILE = 'postinstall.sh'
    SSLEAY_CONFIG = 'ssleay.cnf'
    APACHE_CONFIG_TARBALL = 'apache2.tar.bz2'

    use_sudo = strbool(use_sudo)
    onlychrootcreate = strbool(onlychrootcreate)
    useexistingchroot = strbool(useexistingchroot)
    sourcedirname = _sourcedir()
    targetdirname = _targetdir()

    freesize = os.statvfs(tempfile.gettempdir()).f_bfree * os.statvfs(tempfile.gettempdir()).f_bsize
    if freesize < (2 ** 32):
        abort("sorry, less than 4 Gigabyte of freespace in temp directory %s" % tempfile.gettempdir())

    if onlychrootcreate and useexistingchroot:
        abbort('only one of onlychrootcreate or useexistingchroot can be set to true')

    if not revision:
        revision = _get_current_revision()
    if not hostname:
        hostname = raw_input('hostname[example.com] ')
        if not hostname:
            hostname = 'example.com'
    if not ip:
        ip = raw_input('ip[127.0.0.2] ')
        if not ip:
            ip = '127.0.0.2'

    # create ssh key config
    private_key = os.path.join(targetdirname, VMHOSTKEY)
    public_key = os.path.join(targetdirname,  VMHOSTKEY+".pub")
    if os.path.exists(private_key):
        os.remove(private_key)
    if os.path.exists(public_key):
        os.remove(public_key)
    ssh_keygen = ['ssh-keygen',
        '-t', 'rsa',
        '-b', '4096',
        '-f', VMHOSTKEY,
        '-N', '',
        '-C', 'autovm@vmhost',
    ]
    _run(ssh_keygen, cwd=targetdirname)

    # create postinstall config
    postinstall_sh = os.path.join(targetdirname, POSTINSTALL_FILE)
    postinstall_sh_template = os.path.join(sourcedirname, 'templates', POSTINSTALL_FILE)
    write_template(postinstall_sh_template, postinstall_sh, {
        'applications': ' '.join(APPLICATIONS),
        'vm_user': VM_USER,
        'revision': revision,
        'hostname': ip,
        'ip': ip,
        'apacheconfigtarball': APACHE_CONFIG_TARBALL,
        'ssleayconfig': SSLEAY_CONFIG,
    })
    os.chmod(postinstall_sh, stat.S_IRWXU|stat.S_IRGRP|stat.S_IXGRP|stat.S_IROTH|stat.S_IXOTH)  # chmod 0755

    # create ssleay config
    ssleay_cnf = os.path.join(targetdirname, SSLEAY_CONFIG)
    ssleay_cnf_template = os.path.join(sourcedirname, 'templates', SSLEAY_CONFIG)
    write_template(ssleay_cnf_template, ssleay_cnf, {
        'hostname': hostname,
    })

    # create vmbuilder config
    vmbuilder_cfg = os.path.join(targetdirname, VMBUILDER_CONFIG)
    vmbuilder_cfg_template = os.path.join(sourcedirname, 'templates', VMBUILDER_CONFIG)
    write_template(vmbuilder_cfg_template, vmbuilder_cfg, {
        'dirname': targetdirname,
        'hostname': hostname,
        'vmhostkeypub': VMHOSTKEY+ ".pub",
        'postinstallfile': POSTINSTALL_FILE,
    })

    # create vmbuilder partition config
    partitions = "root 10000\nswap 1000\n---\n/opt 20000\n"
    with open(os.path.join(targetdirname, VMBUILDER_CONFIG+ ".partition"), "wb") as f:
        f.write(partitions)

    # copy apache config
    shutil.copyfile(os.path.join(sourcedirname, APACHE_CONFIG_TARBALL), os.path.join(targetdirname, APACHE_CONFIG_TARBALL))

    # create actual source tarball
    make_tarball(targetdirname, revision=revision)

    # call the vmbuilder, cross fingers
    vmbuilder = ['sudo'] if use_sudo else []
    vmbuilder += ['vmbuilder', hypervisor, VMBUILDER_OS,
        '--config', os.path.join(targetdirname, VMBUILDER_CONFIG),
        '--part', os.path.join(targetdirname, VMBUILDER_CONFIG+ ".partition"),
    ]
    if onlychrootcreate:
        warn('creating chroot, but dont go futher')
        vmbuilder += ['--only-chroot', '--destdir='+ os.path.join(targetdirname, CHROOT_TARGET),]
    else:
        vmbuilder += ['--destdir='+ os.path.join(targetdirname, VMBUILDER_OS+ "-"+ hypervisor),]
    if useexistingchroot and os.path.exists(os.path.join(targetdirname, CHROOT_TARGET)):
        warn('using prebuild chroot under %s' % os.path.join(targetdirname, CHROOT_TARGET))
        vmbuilder += ['--existing-chroot='+ os.path.join(targetdirname, CHROOT_TARGET),]
        warn('recopy ssh authorized_keys to chroot')
        shutil.copy(os.path.join(targetdirname,  VMHOSTKEY+".pub"), os.path.join(targetdirname, CHROOT_TARGET, 'home', VM_USER, '.ssh', 'authorized_keys'))

    _run(vmbuilder, cwd=targetdirname)


def deletechroot():
    shutil.rmtree(os.path.join(_targetdir(), CHROOT_TARGET))


def deletevm(hypervisor=VMBUILDER_HYPERVISOR):
    shutil.rmtree(os.path.join(_targetdir(), VMBUILDER_OS+ "-"+ hypervisor))

def dotests(application=None, hypervisor=VMBUILDER_HYPERVISOR):
    if application:
        applications = [application]
    else:
        applications = APPLICATIONS

    with RunningVM(hypervisor, snapshot=True) as vm:
        for app in applications:
            test = [
                '. ./environment/bin/activate',
                'cd src',
                'fab apptest:%s' % app,
            ]
            vm.do(test, user=app)

def getshell(running=False, snapshot=False, hypervisor=VMBUILDER_HYPERVISOR):
    running = strbool(running)
    snapshot = strbool(snapshot)
    dirname = _targetdir()
    ssh = ['ssh', 'localhost',
        '-o', 'NoHostAuthenticationForLocalhost=yes',
        '-i', os.path.join(dirname, VMHOSTKEY),
        '-p', '42022',
        '-l', VM_USER,
    ]

    if not running:
        with RunningVM(hypervisor, snapshot=snapshot) as vm:
            os.system('reset && %s' % subprocess.list2cmdline(ssh))
    else:
        os.system('reset && %s' % subprocess.list2cmdline(ssh))

