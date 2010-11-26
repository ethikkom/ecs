#!/usr/bin/env python
# -*- coding: utf-8 -*-

import getopt
import sys
import re
import os
from pprint import pprint

class FixmeFinder():
    
    patterns = {}
    c_patterns = {}
    parse_files = []
    results = []
    final_results = []
    indir = None
    outdir = None
    ignored_dirs = []
    extensions_2_parse = [".py", ".sh", ".html", ".conf", ".css", ".js"]
    exclude_dirs = ["ecs/static/MooDialog", "ecs/static/MooEditable", "ecs/static/CACHE",
                    "environment", "externals", "docs", "legacy", "sandbox", ".hg"]
    base_path = None
    #hudson:
    #ecs/static/Moo**, ecs/static/CACHE/**, ecs/static/js/moo*
    # environment/**,externals/**,docs/**,legacy/**,sandbox/**,deployment/virtualenv.py,bootstrap.py
    
    
    
    def __init__(self, indir, outdir=None, verbose=False):
        results = []
        self.indir = indir
        self.outdir = outdir
        self.verbose = verbose
        #regex pattern and score modificator - its case insensitive
        self.patterns = {'FIXME': 4, 'TODO': 2, 'XXX': 1}
        #fixme*4+todo*2+xxx  = rank
        
        for pat, mod in self.patterns.items():
            #print pat
            self.c_patterns[pat] = re.compile(r"\b%s\b" % pat, re.IGNORECASE)
        
        self.base_path = os.path.abspath(self.indir)
        
        return
        
    
    def find_fixmes(self, output_matched_lines=True):
        print "starting to parse dir: %s" % os.path.abspath(self.indir)
        self.parse_dir_index(self.indir)
        print "%s files to parse" % len(self.parse_files)
        print "ignored dirs: "
        for idir in self.ignored_dirs:
            print idir
        
        self.parse_all_files()
        
        self.final_results = sorted(self.results, key=lambda result: result[1], reverse=True)
        for res in self.final_results:
            print res[1], res[2], os.path.relpath(res[0], self.indir)
            if output_matched_lines:
                for line in res[3]:
                    print "\t%s" % line.lstrip()
        
        
        return
    
    
    def parse_all_files(self):
        for fname in self.parse_files:
            self.parse_file(fname)
        
        
    def parse_dir_index(self, dir):
        for dirname, dirnames, filenames in os.walk(dir, topdown=True,followlinks=False):
            tmpdirs = list(dirnames)
            for d in tmpdirs:
                relpath_from_base = os.path.relpath(os.path.join(dirname,d), self.base_path)
                if relpath_from_base in self.exclude_dirs:
                    dirnames.remove(d)
                    self.ignored_dirs.append(relpath_from_base)
                
            for f in filenames:
                fname,ext = os.path.splitext(f)
                if ext in self.extensions_2_parse and f != "fixmefinder.py":
                    self.parse_files.append(os.path.join(dirname, f))
            
    
    def parse_file(self, filename):
        
        filescore = 0
        linenum = 1
        matched_lines = []
        pattern_counts = {}
        for pattern, mod in self.patterns.items():
            pattern_counts[pattern] = 0
        
        f = open(filename, 'r')
        for line in f.readlines():
            for pattern, mod in self.patterns.items():
                match = self.c_patterns[pattern].search(line)
                if match:
                    pattern_counts[pattern] += 1
                    matched_lines.append(line)
            linenum += 1

        f.close()
        
        scores = {}
        for pattern, score in pattern_counts.items():
            filescore += score * self.patterns[pattern]
            scores[pattern] = score
        
        if filescore > 0:
            self.results.append((filename, filescore, scores, matched_lines))
        
        return filescore


def usage():
    print "%s -i <INDIR> " % sys.argv[0]
    print "search for fixmes/todos/xxx's in dir <INDIR>"
    print
    
    
if __name__ == "__main__":
    #parse args
    try:
        opts, args = getopt.getopt(sys.argv[1:], "i:o:f:vh", ["indir=", "outdir=", "file=", "help"])
    except getopt.GetoptError, err:
        # print help information and exit:
        print str(err) # will print something like "option -a not recognized"
        usage()
        sys.exit(2)
    outdir = None
    indir = None
    verbose = False
    for o, a in opts:
        if o == "-v":
            verbose = True
        elif o in ("-i", "--indir"):
            indir = os.path.abspath(a)
        elif o in ("-o", "--outdir"):
            outdir = a
        elif o in ("-f", "--file"):
            ff = FixmeFinder(indir, outdir, verbose)
            ff.parse_file(a)
            print wf.results
            sys.exit(0)
        elif o in ("-h", "--help"):
            usage()
            sys.exit(0)
        else:
            assert False, "unhandled option"
    #execute
    ff = FixmeFinder(indir, outdir, verbose)
    ff.find_fixmes()
    
    
