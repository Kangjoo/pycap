#!/usr/bin/env python

import subprocess
import os
import time
import logging
from datetime import datetime
from pathlib import Path
import argparse
import pprint
import yaml

def file_path(path):
    """
    Used for argparse, ensures file exists
    """
    if os.path.exists(path):
        return path
    else:
        raise argparse.ArgumentTypeError(f"file {path} does not exist!")
    
#Main function

timestamp = datetime.now().strftime("%Y-%m-%d_%H.%M.%S.%f")
pp = pprint.PrettyPrinter(indent=1)

req_args = {"global":{}}
schedulers = ['NONE','SLURM','PBS']

defaults = {"global":{'scheduler':{'type':"NONE"}},
            "concatenate_bolds":{'overwrite':'no'}}


parser = argparse.ArgumentParser()
parser.add_argument("--config", type=file_path, required=True, help="Path to config file with PyCap parameters")
parser.add_argument("--steps", type=str, help="Comma seperated list of PyCap steps to run. Can also be specified in config")
args = vars(parser.parse_args())

with open(args['config'], 'r') as f:
    config = yaml.safe_load(f)

#Combine command line args with config args, with command line overwriting
args = config | args

if 'steps' not in args.keys():
    print("--steps parameter not supplied! Exiting...")
    exit()

if type(args['steps']) != list:
    args['steps'] = args['steps'].split(',')

#Set global defaults
args['global'] = defaults['global'] | args['global']
parsed_args = {}
parsed_args['global'] = args['global']
#Check schedulers are the same and parse with defaults
first=True
for step in args['steps']:
    if step not in defaults.keys():
        print(f"--steps parameter: '{step}' invalid! Exiting...")
        exit()

    step_args = defaults[step] | args['global'] | args[step]
    if 'type' in step_args['scheduler'].keys():
        step_sched = step_args['scheduler']['type'].upper()
        if step_sched not in schedulers:
            print(f"ERROR: Invalid scheduler {step_sched} provided! Scheduler must be one of '{str(schedulers)}'. Exiting...")
            exit()
    else:
        print(f"ERROR: scheduler specified in config, but missing scheduler type!")
        exit()

    if first: 
        sched_type = step_sched
    elif sched_type != step_sched:
        print(f"ERROR: all specified schedulers must be of same type, expected {sched_type}, found {step_sched}!")
        print(f"If scheduler type unspecified, assumed 'NONE'. Exiting...")
        exit()

    parsed_args[step] = step_args

#Command orchestration

#Contain list of commands to run, either as jobs or directly
commands = []

for step in args['steps']:

    if step not in args.keys():
        print(f"--steps parameter: '{step}' missing config parameters! Exiting...")
        exit()
    
    step_args = parsed_args[step]
    
    pp.pprint(step_args)


    if step == "concatenate_bolds":
        pass

    else:
        print(f"--steps parameter: '{step}' invalid! Exiting...")
        exit()