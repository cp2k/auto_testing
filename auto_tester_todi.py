#!/usr/bin/python
# -*- coding: utf-8 -*-

import subprocess as sp
from datetime import datetime
import time
import os
from os import path
from traceback import print_exc
import socket
from git_utils import *
import re

devnull = open("/dev/null", "w")
quiet = dict(stdout=devnull, stderr=devnull)
#===============================================================================
def main():

    if("todi" not in socket.gethostname()):
        print("Run this only on todi")
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

    ref = "regtest-todi"

    #git_fetch("oschuett_dev")

    remote_branches = git_branch("-r")

    print("Checking branches "+(", ".join(remote_branches)))
    for branch in reversed(remote_branches):
        head_sha1 = git_rev_parse(branch)
        print branch
        if(git_notes_exist(ref, head_sha1)):
            print("found note")
            note = git_notes_show(ref, head_sha1)
            if("RUNNING" in note):
                check_job(ref, head_sha1)
            continue


        if("dbcsr" not in branch):
            print("not dbcsr")
            continue
        #msg = do_tests(branch)
        
        #git_notes_append(ref, head_sha1, msg)
        #git_push_notes()
        #git_fetch()

#===============================================================================
def squeue(jobid):
    p = sp.Popen(["squeue","--jobs="+jobid,"--format=%T","--noheader"], stdout=sp.PIPE)
    output = p.communicate()[0]
    assert(p.wait()==0)
    return(output.strip())

#===============================================================================
def check_job(ref, head_sha1):
    note = git_notes_show(ref, head_sha1)
    jobid = re.search("\(jobid: (\d+)\)", note).group(1)
    print jobid
    state = squeue(jobid)

#===============================================================================
def do_tests(branch):
    print("Testing branch "+branch)
    old_sha1 = git_rev_parse("HEAD")
    sp.check_call(["git", "checkout", branch], cwd="./cp2k/", **quiet)

   # # were we already on this branch, then don't clean before build
   # if(branch in git_branch("-r --contains "+old_sha1)):
   #     print("Last time we compiled the same branch, not doing cleanup")
   # else:
   #     sp.check_call(["git", "clean", "-fd"], cwd="./cp2k/", **quiet)
   #     sp.check_call("make clean realclean distclean", shell=True, cwd="./cp2k/cp2k/makefiles/")

    sp.check_call("cp ./arch/* ./cp2k/cp2k/arch/", shell=True)

    branch_dir = "branches/"+branch


    if(not path.exists(branch_dir)):
        sp.check_call(["mkdir", "-p", branch_dir])
        #sp.check_call(["cp", "-rl","./branches/github_cp2k/master/LAST-Linux-pdbg", branch_dir])


    timestamp = datetime.now().replace(microsecond=0).isoformat()

    log_fn = branch_dir+"/"+timestamp+"_make.out"
    log_f = open(log_fn, "w")
    print("Starting make (%s)"%log_fn)
    rtncode = sp.call("make -j ARCH=Linux-todi VERSION=pdbg", shell=True, stdout=log_f, stderr=log_f, cwd="./cp2k/cp2k/makefiles/")
    log_f.close()

    if(rtncode != 0):
        return("Build failed, log: "+log_fn)



    dir_triplet = "Linux-todi_"+timestamp
    sp.check_call(["mkdir", "-p", "./cp2k/cp2k/exe/"+dir_triplet])
    sp.check_call(["cp", "-l", "./cp2k/cp2k/exe/Linux-todi/cp2k.pdbg", "./cp2k/cp2k/exe/"+dir_triplet+"/cp2k.pdbg"])

    regtest_conf_fn = timestamp+"_regtest.conf"
    f = open(branch_dir+"/"+regtest_conf_fn, "w")
    f.write("dir_base="+os.getcwd()+"/"+branch_dir+"\n")
    f.write("cp2k_dir=../../../cp2k/cp2k\n")
    f.write("cp2k_version=pdbg\n")
    f.write("dir_triplet="+dir_triplet+"\n")
    f.write("ARCH="+dir_triplet+"\n")
    f.write("maxtasks=128\n")
    f.write('cp2k_run_prefix="aprun -n 2 -F share"\n')
    f.write("make=true\n")
    f.close()

    job_fn = branch_dir+"/"+timestamp+"_regtest.job"
    f = open(job_fn, "w")
    f.write("#!/bin/bash\n")
    f.write("#SBATCH --job-name=cp2k_regtest\n")
    f.write("#SBATCH --ntasks=256\n")
    f.write("#SBATCH --partition=day\n")
    f.write("#SBATCH --time=0:59:00\n")
    f.write("#SBATCH --account=s441\n\n")
    f.write("cd "+os.getcwd()+"/"+branch_dir+"\n")
    f.write("../../../cp2k/cp2k/tools/do_regtest -config "+regtest_conf_fn+"\n")
    f.close()

    print("would submit :"+ job_fn)
    sys.exit(1)
#    print("Starting do_regtest (%s)"%log_fn)
#    cmd = ["./cp2k/cp2k/tools/do_regtest","-config",regtest_conf_fn]
#    rtncode = sp.call(cmd, stdout=log_f, stderr=log_f)
#    log_f.close()
#
#    if(rtncode != 0):
#        return("Regtests failed, log: "+log_fn)
#
#    last_lines = open(log_fn, "r").read().split("\n")[-10:]
#    summary  = "\n".join(last_lines)
#    summary += "\n log: "+log_fn
#    return(summary)
#
#===============================================================================
main()
#EOF
