#!/usr/bin/python
# -*- coding: utf-8 -*-

import subprocess as sp
from datetime import datetime
import time
import os
from os import path
from traceback import print_exc
from auto_tester_utils import *
import socket
import sys
import re

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
            update_www()
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

        reports = [ do_build(branch) ]
        update_www() #TODO: useless since notes are not updated, not even locally
        if("PASS" in reports[-1]):
            reports.append(do_regtests(branch))

        msg = "\n".join(reports)
        print msg
        git_notes_append(ref, head_sha1, msg)
        git_push_notes()
        git_fetch()
        update_www()



#===============================================================================
def do_build(branch):
    test_name = "build_gfortran_pdbg"
    print("Running "+test_name+" on branch "+branch)

    try:
       old_sha1 = git_rev_parse("HEAD")
       sp.check_call(["git", "checkout", branch], cwd="./cp2k/", **quiet)

       # were we already on this branch, then don't clean before build
       if(branch in git_branch("-r --contains "+old_sha1)):
           print("Last time we compiled the same branch, not doing cleanup")
       else:
           print("Cleaning up first.")
           sp.check_call(["git", "clean", "-fd"], cwd="./cp2k/", **quiet)
           sp.check_call("make clean realclean distclean", shell=True, cwd="./cp2k/cp2k/makefiles/", **quiet)

       sp.check_call("cp ./arch/* ./cp2k/cp2k/arch/", shell=True)

       branch_dir = "branches/"+branch

       if(not path.exists(branch_dir)):
           sp.check_call(["mkdir", "-p", branch_dir])
           sp.check_call(("ssh cp2k.org mkdir -p test.cp2k.org/auto_tester/s01/"+branch_dir).split())

       timestamp = datetime.now().replace(microsecond=0).isoformat()

       log_fn = branch_dir+"/"+timestamp+"_make.out"
       log_f = open(log_fn, "w")
       print("Starting make (%s)"%log_fn)
       rtncode = sp.call("make -j ARCH=Linux-s01 VERSION=pdbg", shell=True, stdout=log_f, stderr=log_f, cwd="./cp2k/cp2k/makefiles/")
       log_f.close()

       sp.check_call(["scp", "./"+log_fn , "cp2k.org:test.cp2k.org/auto_tester/s01/"+log_fn], **quiet)

       if(rtncode != 0):
           return(test_name+" FAIL make returned code %d http://test.cp2k.org/auto_tester/s01/%s"%(rtncode, log_fn))

       return(test_name+" PASS  http://test.cp2k.org/auto_tester/s01/%s"%(log_fn))

    except:
       return(test_name+" FAIL "+repr(sys.exc_info()[1]))

#===============================================================================
def do_regtests(branch):
    test_name = "regtest_gfortran_pdbg"
    try:
       branch_dir = "branches/"+branch
       regtest_conf_fn = branch_dir+"/regtest.conf"
       f = open(regtest_conf_fn, "w")
       f.write("dir_base="+os.getcwd()+"/"+branch_dir+"\n")
       f.write("cp2k_dir=../../../cp2k/cp2k\n")
       f.write("cp2k_version=pdbg\n")
       f.write("dir_triplet=Linux-s01\n")
       f.write("ARCH=Linux-s01\n")
       f.write("maxtasks=16\n")
       f.write('cp2k_run_prefix="mpirun -np 2 "\n')
       f.close()

       if(not path.exists(branch_dir+"/LAST-Linux-s01-pdbg")):
           sp.check_call(["cp", "-rl","./branches/github_cp2k/master/LAST-Linux-s01-pdbg", branch_dir])

       timestamp = datetime.now().replace(microsecond=0).isoformat()
       log_fn = branch_dir+"/"+timestamp+"_regtest.out"
       log_f = open(log_fn, "w")
       print("Starting do_regtest (%s)"%log_fn)
       cmd = ["./cp2k/cp2k/tools/do_regtest","-config",regtest_conf_fn]
       cmd += ["-restrictdir", "QS/regtest-dm-ls-scf"]

       rtncode = sp.call(cmd, stdout=log_f, stderr=log_f)
       log_f.close()

       sp.check_call(["scp", "./"+log_fn , "cp2k.org:test.cp2k.org/auto_tester/s01/"+log_fn], **quiet)

       if(rtncode != 0):
           return(test_name+" FAIL do_regtest returned code %d http://test.cp2k.org/auto_tester/s01/%s"%(rtncode, log_fn))

       return(test_name+" "+regtest_report(log_fn) +" http://test.cp2k.org/auto_tester/s01/"+log_fn)

    except:
       return(test_name+" FAIL "+repr(sys.exc_info()[1]))


#===============================================================================
def update_www():
    sys.stdout.write("Updating www report...")
    cmd = "git log --remotes --decorate  --show-notes=* --date-order -n 10".split()
    cmd += [r"--pretty=tformat:{'H':r'%H', 'an':r'%an', 'ae':r'%ae', 'N':r'''%N''', 's':r'%s', 'b':r'''%b''' },"]
    output = check_output(cmd)
    commits = eval("["+output+"]")
    
    #print commits

    timestamp = datetime.now().replace(microsecond=0).isoformat()
    html = "<html><head><meta charset='utf-8'>"
    html += "<title>CP2K Auto-Tester Report from %s</title>"%timestamp
    html += "</head><body>"

    for c in commits:
        html += '<div style="border:1px solid gray; margin:10px; padding:5px;">'
        html += '<a href="https://github.com/cp2k/cp2k/commit/%s"><h3>%s</h3></a>'%(c['H'], c['s'])
        html += "SHA1: %s<br>"%c['H']
        html += 'Author: '+c['an'] + "<br>" # + " &lt;" +c['ae'] + "&gt; <br>"
        branches = []
        for branch in git_branch("-r --contains "+c['H']):
            n = branch.split("/", 1)[1]
            branches.append('<a href="https://github.com/cp2k/cp2k/commits/%s">%s</a>'%(n,n))
        html += "Branch(es): "+(", ".join(branches))
        html += format_notes(c['N'])
        #html += "<pre>"+c['N']+"</pre>"
            #for line in c['N'].split("\n"):
            #    print line
        html += "</div>"

    html += "</body></html>"

    f = open("index.html", "w")
    f.write(html)
    f.close()

    sp.check_call("scp index.html cp2k.org:test.cp2k.org/auto_tester/".split(), **quiet)

    print("done.")

#===============================================================================
def format_notes(notes):
    if(len(notes.strip()) == 0): return("")

    html = '<table border=1>'
    for line in notes.strip().split("\n"):
        #print line
        m = re.match("^(\w+) (\w+) (.*?)( http://\S+)?$", line)
        if(m==None):
            return "<pre>"+notes+"</pre>"

        test_name = m.group(1)
        test_result = m.group(2)
        test_msg = m.group(3)
        test_url = m.group(4)

        html += "<tr><td>%s</td>"%test_name

        if(test_result=="PASS"):
            html += '<td style="background-color:green;">PASS</td>'
        elif(test_result=="FAIL"):
             html += '<td style="background-color:red;">FAIL</td>'
        else:
            raise(Exception("Unkown test result: "+test_result))

        html += "<td>%s</td>"%test_msg
        if(test_url):
            html += '<td><a target="_blank" href="%s">log</td>'%test_url
        else:
            html += '<td>no log</td>'

        html += "</tr>"

    html += "</table>"
    return(html)
#===============================================================================
main()
#EOF
