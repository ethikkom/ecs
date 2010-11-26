#!/usr/bin/env python
# -*- coding: utf-8 -*-


from xml.dom.minidom import *
import getopt
import sys
import os
from pprint import pprint
from decimal import *


class CoverageFinder(object):
    
    results = []
    xmlfilename = None
    IGNORE_INIT_PY = False
    
    def __init__(self, xmlfilename, basedir, IGNORE_INIT_PY=True):
        getcontext().prec = 3
        self.IGNORE_INIT_PY = IGNORE_INIT_PY
        self.basedir = basedir
        if not os.path.exists(xmlfilename):
            print "coverage.xml not found"
            print "was looking for: %s" % xmlfilename
            print "did u run ./manage.py test?"
        else:
            self.xmlfilename = xmlfilename
    
    
    def parse(self):
        if not self.xmlfilename:
            return
        
        #dom = parse("../../../ecs/coverage.xml")
        dom = parse(self.xmlfilename)
        reports = dom.getElementsByTagName("coverage")
        
        for report in reports:
            self.handleReport(report)
        
    def handlePackages(self, packages):
        realpackages = packages.getElementsByTagName("package")
        for package in realpackages:
            self.handlePackage(package)
        
    def handlePackage(self, package):
        classeslist = package.getElementsByTagName("classes")
        for classes in classeslist:
            self.handleClasses(classes)
        
    def handleClasses(self, classes):
        realclasses = classes.getElementsByTagName("class")
        for classdef in realclasses:
            self.handleClass(classdef)
        
    def handleClass(self, classdef):
        fname = classdef.getAttribute("filename")
        percentage = Decimal(classdef.getAttribute("line-rate")) * Decimal(100)
        if(self.IGNORE_INIT_PY and "__init__.py" in fname ):
            return
        self.results.append((fname, percentage))
        
    def handleReport(self, report):
        packages = report.getElementsByTagName("packages")
        for package in packages:
            self.handlePackages(package)
        
            
    def output(self):
        self.results = sorted(self.results, key=lambda result: result[1], reverse=False)
        for result in self.results:
            filename = os.path.relpath(os.path.normpath(result[0]), self.basedir)
            print result[1], "%", "\t", filename
    
    
if __name__ == "__main__":
    
    coveragefile = os.path.join(os.getenv("VIRTUAL_ENV"), os.pardir, "src", "ecs", "coverage.xml")
    basedir = os.path.curdir
    cf = CoverageFinder(coveragefile, basedir, IGNORE_INIT_PY=True)
    cf.parse()
    cf.output()
