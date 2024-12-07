#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------
# Created By  : Kangjoo Lee (kangjoo.lee@yale.edu)
# Last Updated: 08/06/2024
# -------------------------------------------------------------------------


# =========================================================================
#                    --   Run pipeline template  --
#      Analysis of Co-Activation Patterns(CAP) in fMRI data (HCP-YA)
# =========================================================================

# Imports
import math
import h5py
import os
import shutil
import random
import sklearn.model_selection
import numpy as np
import argparse
import itertools
import pandas as pd
import logging
from pycap_functions.pycap_loaddata import *
from pycap_functions.pycap_frameselection import *
from pycap_functions.pycap_gen import *
from pycap_functions.pycap_datasplit import *
import pycap_functions.pycap_exceptions as exceptions
import pycap_functions.pycap_utils as utils
import time


def dir_path(path):
    if os.path.isdir(path):
        return path
    else:
        raise argparse.ArgumentTypeError(f"readable_dir:{path} is not a valid path")

def file_path(path):
    if os.path.exists(path):
        return path
    else:
        raise argparse.ArgumentTypeError(f"file {path} does not exist!")

def local_path(path):
    if path[0] != '/':
        return path
    else:
        raise argparse.ArgumentTypeError(f"{path} must be a local path from the specified sessions_folder!")


parser = argparse.ArgumentParser()
parser.add_argument("--save_image", type=str, default='no', help="Save CAP images or not (y/n)")
parser.add_argument("--sessions_folder", type=dir_path, help="Home directory path")
parser.add_argument("--analysis_folder", type=dir_path, help="Output directory path")
parser.add_argument("--permutations", type=int, default=1, help="Range of permutations to run, default 1.")
parser.add_argument("--sessions_list", required=True,
                    help="Path to list of sessions", type=file_path)
parser.add_argument("--parc_file", type=file_path, required=False ,help="Path to parcellation template, required to save CAP image for parcellated data")
parser.add_argument("--overwrite", type=str, default="no", help='Whether to overwrite existing data')
parser.add_argument("--log_path", default='./prep_run_hcp.log', help='Path to output log', required=False)
parser.add_argument("--mask", default=None, help="Brain mask, required for dense data and saving CAP image.")
parser.add_argument("--bold_type", default=None, help="BOLD data type (CIFTI/NIFTI), if not supplied will use file extention")
parser.add_argument("--cluster_args", type=str, required=True, help="Args for sklearn clustering in form 'key1=val1,key2=val2'. " \
                    "Must have key '_method', corresponding to a function in sklearn.clustering")
parser.add_argument("--tag", default="", help="Tag for saving files, useful for doing multiple analyses in the same folder (Optional).")
args = parser.parse_args()  # Read arguments from command line

if args.tag != "":
    args.tag += "_"
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(message)s',
                    filename=args.log_path,
                    filemode='w')
console = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

logging.info("PyCap Post Start")
#Wait for a moment so run_pycap.py log tracking can keep up
time.sleep(1)

# -------------------------------------------
#           Setup input parameters
# -------------------------------------------

overwrite = args.overwrite.lower()# == "yes"

class Param:
    pass


param = Param()

param.mask = args.mask
if not args.bold_type:
    param.bold_type = utils.get_bold_type(args.bold_path)
else:
    param.bold_type = args.bold_type

param.tag = args.tag

param.overwrite = overwrite

# # - parameters for clustering
param.cluster_args = utils.string2dict(args.cluster_args)
param.savecapimg = args.save_image


# -------------------------------------------
#              Setup input data
# -------------------------------------------


class FileIn:
    pass


filein = FileIn()
filein.sessions_folder = args.sessions_folder
filein.sublistfull, filein.groups = parse_sfile(args.sessions_list)
filein.pscalar_filen = args.parc_file

for split_i in range(args.permutations):
    #adjust to non-index count
    split = split_i + 1

    logging.info(f"Running permutation {split}")

    split_dir = os.path.join(args.analysis_folder, f"perm{split}")
        
    filein.outpath = split_dir
    filein.datadir = os.path.join(split_dir, "data/")
    param.overwrite = args.overwrite
    # -------------------------------------------
    # - Population split-half list of subjects
    # -------------------------------------------

    split_2_sublist, split_1_sublist = subsplit(filein=filein, param=param)

    # -------------------------------------------
    # - Run the whole process for split_1 and split_2 datasets
    # -------------------------------------------
    for sp in [1, 2]:
        if sp == 1:
            param.spdatatag = "split1"
            filein.sublist = split_1_sublist
        elif sp == 2:
            param.spdatatag = "split2"
            filein.sublist = split_2_sublist

        msg = "============================================"
        logging.info(msg)
        msg = "Start processing " + param.spdatatag + "..."
        logging.info(msg)
        msg = "    >> np.unique(filein.sublist) : " + str(np.unique(filein.sublist))
        logging.info(msg)

        data_all_fsel, sublabel_all_fsel = load_groupdata(filein, param)

        msg = "    >> np.unique(sublabel_all_fsel) : " + str(np.unique(sublabel_all_fsel))
        logging.info(msg)

        finalcluster2cap_any(inputdata=data_all_fsel, filein=filein, param=param)

        # -------------------------------------------
        # - Delete variable to save space
        # -------------------------------------------
        del data_all_fsel, sublabel_all_fsel

        msg = "\n"
        logging.info(msg)


    # - Notify job completion
    logging.info(f"--- STEP COMPLETE ---")
