# -*- coding: utf-8 -*-

import os
from zipfile import ZipFile

from fabric.utils import abort, warn

from deployment.utils import get_pythonexe, packageline_split, which
from deployment.fridge import try_frozen
from deployment.pkgmanager.base import PkgManagerBase


class Windows(PkgManagerBase):
    platform = '(all|win|!mac|!apt|!suse|!openbsd)'
    resource = '(http|https|ftp|file)' # XXX resource is used different in windows req
    # workaround Windows 7: easy_install needs administrator rights, no matter how we install; python easy_install-script.py doesnt need
    easy_install = "".join(("python ", os.path.join(os.path.dirname(get_pythonexe()),"easy_install-script.py")))

    def _zip_flatextract(self, filename, destpath, not_deeper_than= -1):
        ''' extracts a zipfile without directory structure, unzips all files of zip on one dir
        use not_deeper_than= -1 for all subdirectories,
        use not_deeper_than= 0 for skipping files of zipfile beyond rootdir,
        use not_deeper_than= 1-X for skipping files of zipfile beyond 1-x subdir  '''
        z=ZipFile(filename, 'r')
        for name in z.namelist():
            if not name.endswith('/'):
                level = len(name.split("/"))
                if not_deeper_than != -1 and (level > (not_deeper_than+1)):
                    # print("debug: skipped %s , level = %i" % (name, level))
                    pass
                else:
                    basename= os.path.basename(name)
                    outfile = open(os.path.join(destpath, basename), 'wb')
                    outfile.write(z.read(name))
                    outfile.close()
        z.close()

    def get_missing_prerequisites(self, packages):        
        prerequisites = list(self.get_prerequisites(packages))
        
        for pkgline in prerequisites:
            (name, pkgtype, platform, resource, url, opt1, opt2) = packageline_split(pkgline)
    
            if opt1 == "unzipflat" or opt1 == "unzipflatroot" or opt1 == "unzipflatsecond":
                if not len(list(which(opt2))):
                    yield pkgline
            
            elif opt1 in ['exec', 'msiexec']:
                full_path = None
                warn("Information: searching c:\ for %s, this may take a while" % opt2)
                for root, dirs, files in os.walk("C:\\"):
                    for file in files:
                        if file == opt2:
                            full_path = os.path.join(root, file)
                            warn("Information: found %s at %s" % (opt2, full_path))
                            break
                    if full_path:
                        break
                if not full_path:
                    yield pkgline
            else:
                raise NotImplementedError

    def install_prerequisites(self, packages, use_sudo=True):
        prerequisites = list(self.get_missing_prerequisites(packages))
        if not prerequisites:
            return
            
        for pkgline in prerequisites:
            (name, pkgtype, platform, resource, url, opt1, opt2) = packageline_split(pkgline)
                
            if resource in ["http", "https", "ftp"]:
                url = "".join((resource,":",url))
            elif resource in ["file", "dir"]:
                url = os.path.join(fabdir(), url)
            
            # try to take windows prerequisite package from the fridge (externals/frozen)
            resource, url = try_frozen(resource, url)
                            
            if opt1 in ["unzipflat", "unzipflatroot", "unzipflatsecond"]:        
                print("Information: installing prerequisite %s" % opt2)
                if resource == "file":
                    filename = url
                else:
                    filename, headers = urlretrieve(url)
                C_extract_levels = {'unzipflat': -1, 'unzipflatroot': 0, 'unzipflatsecond': 1}
                self._zip_flatextract(filename, os.path.dirname(get_pythonexe()), C_extract_levels[opt1])
                if resource != "file":
                    os.remove(filename)
        
            elif opt1 in ['exec', 'msiexec']:
                print("Information: installing prerequisite %s" % opt2)
                if resource == "file":
                    filename = url
                else:
                    filename, headers = urlretrieve(url)
                with settings(warn_only=True):
                    if opt1 == "exec":
                        result = local(filename)
                    elif opt1 == "msiexec":
                        result = local("msiexec /i %s" % filename)
                    print(result.stdout)
                    if result.failed:
                        print(result.stderr)
                        abort("Install of prerequisites failed")
                if resource != "file":
                    os.remove(filename)
            else:
                abort("Unimplemented requirement type in line %s" % pkgline)

