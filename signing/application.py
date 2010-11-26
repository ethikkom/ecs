

system_packages = """
apache2:req:apt:apt-get:apache2-mpm-prefork

tomcat:req:apt:apt-get:tomcat6-user
# needs installation of wars from signing into tomcat-user dir; needs modification of setting files
# needs apache config snippets
# needs tomcat user setup
# needa apache proxy-ajp enabled
# needs apache-tomcat upstart.conf
#

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
    install_upstart(appname, use_sudo=use_sudo, dry=dry)
    apache_setup(appname, use_sudo=use_sudo, dry=dry, hostname=hostname, ip=ip)

