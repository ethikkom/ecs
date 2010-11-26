#!/usr/bin/env python
from pip.index import PackageFinder
from pip.req import RequirementSet,InstallRequirement
from urllib import urlretrieve
from urlparse import urlparse

a=InstallRequirement.from_line('BeautifulSoup<=3.1')
x=PackageFinder([],['http://pypi.python.org/simple'])
b=x.find_requirement(a,False)
print(b)

print(b.url,urlparse(b.url))
filename,headers=urlretrieve(b.url)
print filename, headers

b.url='http://github.com/django-extensions/django-extensions/tarball/master'
print(b.url,urlparse(b.url))
filename,headers=urlretrieve(b.url)
print filename, headers

