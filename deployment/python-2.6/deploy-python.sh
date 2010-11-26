#!/usr/bin/env bash
for a in `cat apt-build-dep.list`; do sudo apt-get build-dep $a; done
for a in `cat apt-packages.list`; do sudo apt-get install $a; done
for a in `cat download-urls.list`; do fn=`echo "$a"| sed -re "s/.+\/([^\/]+)/\1/g"`; if test ! -f $fn ; then wget "$a"; fi; done
if test -d ./Python-2.6 ; then rm -rf ./Python-2.6/; fi
tar xzf Python-2.6.tgz
cd Python-2.6
./configure --prefix=/opt/python2.6
patch < ../python2.6-disable-old-modules.patch
make
sudo make install
cd ..
sudo ln -s /opt/python2.6/bin/python2.6 /usr/bin
sudo ln -s /opt/python2.6/bin/python2.6-config /usr/bin
#sudo sh setuptools-0.6c11-py2.6.egg
#sudo ln -s /opt/python2.6/bin/easy_install-2.6 /usr/bin