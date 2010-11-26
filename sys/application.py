

system_packages = """

"""

from deployment.utils import install_upstart, apache_setup

package_bundles = {
    'default': system_packages,
    'system': system_packages,
}

test_flavors = {
    'default': 'false', # TODO: implement
}

def system_setup(appname, use_sudo=True, dry=False, hostname=None, ip=None):
    pass

