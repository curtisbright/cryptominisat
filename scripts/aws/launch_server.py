#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import sys
import boto.ec2
import os
import subprocess
import server_option_parser


def get_answer():
    yes = set(['yes', 'y', 'ye'])
    no = set(['no', 'n'])

    choice = raw_input().lower()
    if choice in yes:
        return True
    elif choice in no:
        return False
    else:
        sys.stdout.write("Please respond with 'yes' or 'no'\n")
        exit(0)


def push():
    print("First we push, oherwise we'll forget...")
    ret = os.system("git push")
    if ret != 0:
        print("Oops, couldn't push, exiting before executing")
        exit(-1)

    print("")


if __name__ == "__main__":
    options, args = server_option_parser.parse_arguments()
    print("Options are:")
    for a, b in options.__dict__.iteritems():
        print("-- %-30s : %s" % (a, b))
    assert args == []

    push()
    data = ""
    opt_is_on = False
    for x in sys.argv[1:]:
        if opt_is_on:
            data += " ".join(x.split(","))
            data += "\" "
            opt_is_on = False
            continue
        if x != "--opt":
            data += x + " "
            continue

        opt_is_on = True
        data += "--opt \""

    if ("--git" not in data):
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'])
        data += " --git %s" % revision

    if len(sys.argv) > 1:
        print("Launching with data: %s" % data)
    else:
        print("you must give at least one parameter, probably --s3folder")
        exit(-1)

    sys.stdout.write("Is this OK? [y/n]? ")
    if not get_answer():
        print("Aborting")
        exit(0)

    print("Executing!")

    cloud_init = """#!/bin/bash
set -e

apt-get update
apt-get -y install git python-pip
pip install --force-reinstall --upgrade awscli
pip install --force-reinstall --upgrade boto

cd /home/ubuntu
sudo -H -u ubuntu bash -c 'ssh-keyscan github.com >> ~/.ssh/known_hosts'
sudo -H -u ubuntu bash -c 'git clone --depth 20 https://github.com/msoos/cryptominisat.git'

# Get credentials
cd /home/ubuntu
sudo -H -u ubuntu bash -c 'aws s3 cp s3://msoos-solve-data/solvers/email.conf . --region=us-west-2'

# Start server
cd /home/ubuntu/cryptominisat
sudo -H -u ubuntu bash -c '/home/ubuntu/cryptominisat/scripts/aws/pre-server.py > /home/ubuntu/pre_server_log.txt  2>&1 &'

DATA="%s"
    """ % data

    conn = boto.ec2.connect_to_region("us-west-2")
    conn.run_instances(
        min_count=1,
        max_count=1,
        image_id='ami-a9e2da99',  # Unbuntu 14.04 US-west (Oregon)
        subnet_id="subnet-88ab16ed",
        instance_type='t2.micro',
        instance_profile_arn='arn:aws:iam::907572138573:instance-profile/server',
        user_data=cloud_init,
        key_name='controlkey',
        security_group_ids=['sg-507b3f35'],
        instance_initiated_shutdown_behavior='terminate')
