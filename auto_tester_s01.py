#!/usr/bin/python
# -*- coding: utf-8 -*-

import subprocess as sp
from datetime import datetime
import time
import os
from os import path
from traceback import print_exc
from git_utils import *
import socket
import sys

devnull = open("/dev/null", "w")
quiet = dict(stdout=devnull, stderr=devnull)
#===============================================================================
def main():

    if("s01" not in socket.gethostname()):
        print("Run this only on s01")
        sys.exit(1)

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
def check_for_updates():
    git_fetch()

    remote_branches = git_branch("-r")

    ref = "regtest-s01"

    print("Checking branches "+(", ".join(remote_branches)))
    for branch in reversed(remote_branches):
        head_sha1 = git_rev_parse(branch)

        if(git_notes_exist(ref, head_sha1)): 
            continue

        msg = do_tests(branch)
        git_notes_append(ref, head_sha1, msg)
        git_push_notes()
        git_fetch()


#===============================================================================
def do_tests(branch):
    print("Testing branch "+branch)
    old_sha1 = git_rev_parse("HEAD")
    sp.check_call(["git", "checkout", branch], cwd="./cp2k/", **quiet)

    # were we already on this branch, then don't clean before build
    if(branch in git_branch("-r --contains "+old_sha1)):
        print("Last time we compiled the same branch, not doing cleanup")
    else:
        sp.check_call(["git", "clean", "-fd"], cwd="./cp2k/", **quiet)
        sp.check_call("make clean realclean distclean", shell=True, cwd="./cp2k/cp2k/makefiles/")

    sp.check_call("cp ./arch/* ./cp2k/cp2k/arch/", shell=True)

    branch_dir = "branches/"+branch
    regtest_conf_fn = branch_dir+"/regtest.conf"

    if(not path.exists(branch_dir)):
        sp.check_call(["mkdir", "-p", branch_dir])

        f = open(regtest_conf_fn, "w")
        f.write("dir_base="+os.getcwd()+"/"+branch_dir+"\n")
        f.write("cp2k_dir=../../../cp2k/cp2k\n")
        f.write("cp2k_version=pdbg\n")
        f.write("dir_triplet=Linux-s01\n")
        f.write("ARCH=Linux-s01\n")
        f.write("maxtasks=16\n")
        f.write('cp2k_run_prefix="mpirun -np 2 "\n')
        f.close()

        #sp.check_call(["cp", "-rl","./branches/github_cp2k/master/LAST-Linux-s01-pdbg", branch_dir])


    timestamp = datetime.now().replace(microsecond=0).isoformat()

    log_fn = branch_dir+"/"+timestamp+"_make.out"
    log_f = open(log_fn, "w")
    print("Starting make (%s)"%log_fn)
    rtncode = sp.call("make -j ARCH=Linux-s01 VERSION=pdbg", shell=True, stdout=log_f, stderr=log_f, cwd="./cp2k/cp2k/makefiles/")
    log_f.close()

    if(rtncode != 0):
        return("Build failed, log: "+log_fn)

    log_fn = branch_dir+"/"+timestamp+"_regtest.out"
    log_f = open(log_fn, "w")
    print("Starting do_regtest (%s)"%log_fn)
    cmd = ["./cp2k/cp2k/tools/do_regtest","-config",regtest_conf_fn]
    rtncode = sp.call(cmd, stdout=log_f, stderr=log_f)
    log_f.close()

    if(rtncode != 0):
        return("Regtests failed, log: "+log_fn)

    last_lines = open(log_fn, "r").read().split("\n")[-10:]
    summary  = "\n".join(last_lines)
    summary += "\n log: "+log_fn
    return(summary)

#===============================================================================
main()
#EOF
