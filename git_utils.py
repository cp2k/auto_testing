#!/usr/bin/python
# -*- coding: utf-8 -*-

import subprocess as sp
from datetime import datetime
import time
import os
from os import path
from traceback import print_exc

devnull = open("/dev/null", "w")
quiet = dict(stdout=devnull, stderr=devnull)
#===============================================================================
def main():
    while(True):
        try:
            check_for_updates()
            print("sleeping for 60 seconds...")
            time.sleep(60)
        except:
            print_exc()
            print("Something went wrong, sleeping for 5 minutes...")
            time.sleep(300)

#===============================================================================
def git_rev_parse(arg):
    p = sp.Popen(["git","rev-parse", arg], stdout=sp.PIPE, cwd="./cp2k/")
    output = p.communicate()[0]
    assert(p.wait()==0)
    return(output.strip())

#===============================================================================
def git_branch(args):
    p = sp.Popen(["git","branch"]+args.split(), stdout=sp.PIPE, cwd="./cp2k/")
    output = p.communicate()[0]
    assert(p.wait()==0)
    branches = [b.strip() for b in output.strip().split("\n")]
    return(branches)

#===============================================================================
def git_notes_append(ref, sha1, message):
    print("Appending commit note")
    p = sp.Popen(["git","notes","--ref",ref,"append","-F","-",sha1], stdin=sp.PIPE, cwd="./cp2k/")
    p.communicate(message)
    assert(p.wait()==0)

#===============================================================================
def git_notes_exist(ref, sha1):
    rtncode = sp.call(["git","notes","--ref",ref,"list",sha1], cwd="./cp2k/", **quiet)
    assert(rtncode in (0,1))
    return(rtncode == 0) # a note exists

#===============================================================================
def git_notes_show(ref, sha1):
    p = sp.Popen(["git","notes","--ref",ref,"show",sha1], stdout=sp.PIPE, cwd="./cp2k/")
    output = p.communicate()[0]
    assert(p.wait()==0)
    return(output.strip())

#===============================================================================
def git_fetch():
    # TODO get list of remotes from git itself
    sp.check_call("git fetch oschuett_dev".split(), cwd="./cp2k/")
    sp.check_call("git fetch github_cp2k".split(), cwd="./cp2k/")

#===============================================================================
def git_push_notes():
    # TODO get list of remotes from git itself
    sp.check_call("git push oschuett_dev refs/notes/*".split(), cwd="./cp2k/")
    sp.check_call("git push github_cp2k  refs/notes/*".split(), cwd="./cp2k/")

#EOF
