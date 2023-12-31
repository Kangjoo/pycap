#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Created By  : Kangjoo Lee (kangjoo.lee@yale.edu)
# Created Date: 01/19/2022
# Last Updated: 04/22/2022
# version ='0.0'
# ---------------------------------------------------------------------------
# ===============================================================
#                           Load fMRI data
# ===============================================================


# Imports
import numpy as np
import nibabel as nib
import logging
import os
from scipy import stats
import h5py
# from memory_profiler import profile
# @profile


def load_hpc_norm_subject_wb(dataname):
    # an individual (time points x space) matrix
    data = nib.load(dataname).get_fdata(dtype=np.float32)
    zdata = stats.zscore(data, axis=0)  # Normalize each time-series
    del data
    return zdata



def load_hpc_groupdata_wb(filein, param):
    homedir = filein.homedir
    sublist = filein.sublist
    fname = filein.fname
    gsr = param.gsr
    unit = param.unit
    sdim = param.sdim
    tdim = param.tdim

    msg = "============================================"
    logging.info(msg)
    msg = "[whole-brain] Load " + unit + \
        "-level time-series data preprocessed with " + gsr + ".."
    logging.info(msg)

    data_all = np.empty((len(sublist) * tdim, sdim), dtype=np.float32)
    sublabel_all = np.empty((len(sublist) * tdim, ), dtype=np.int)
    ptr = 0
    for idx, subID in enumerate(sublist):
        # - Load fMRI data
        dataname = os.path.join(homedir, str(subID), "images", "functional", fname)
        zdata = load_hpc_norm_subject_wb(dataname)
        data_all[ptr:ptr+zdata.shape[0], :] = zdata
        # - Create subject label
        subid_v = [subID] * zdata.shape[0]
        subid_v = np.array(subid_v)
        sublabel_all[ptr:ptr+zdata.shape[0], ] = subid_v
        # - Update/delete variables
        ptr += zdata.shape[0]

        msg = "(Subject " + str(idx) + ")" + dataname + " " + \
            ", data:" + str(zdata.shape) + ", label:" + str(subid_v.shape)
        logging.info(msg)

        del zdata, subid_v

    msg = ">> Output: a (" + str(data_all.shape[0]) + " x " + \
        str(data_all.shape[1]) + ") array of (group concatenated time-series x space)."
    logging.info(msg)
    return data_all, sublabel_all


def load_hpc_groupdata_wb_usesaved(filein, param):
    filein.groupdata_wb_filen = filein.datadir + "hpc_groupdata_wb_" + \
        param.unit + "_" + param.gsr + "_" + param.spdatatag + ".hdf5"
    if os.path.exists(filein.groupdata_wb_filen):
        msg = "File exists. Load concatenated fMRI/label data file: " + filein.groupdata_wb_filen
        logging.info(msg)

        f = h5py.File(filein.groupdata_wb_filen, 'r')
        data_all = f['data_all']
        sublabel_all = f['sublabel_all']

    else:
        msg = "File does not exist. Load individual whole-brain fMRI data."
        logging.info(msg)

        data_all, sublabel_all = load_hpc_groupdata_wb(filein=filein, param=param)
        f = h5py.File(filein.groupdata_wb_filen, "w")
        dset1 = f.create_dataset(
            "data_all", (data_all.shape[0], data_all.shape[1]), dtype='float32', data=data_all)
        dset2 = f.create_dataset(
            "sublabel_all", (sublabel_all.shape[0],), dtype='int', data=sublabel_all)
        f.close()

        msg = "Saved the concatenated fMRI/label data: " + filein.groupdata_wb_filen
        logging.info(msg)
    return data_all, sublabel_all



def load_hpc_groupdata_motion(filein, param):
    # load motion parameters estimated using QuNex
    # https://bitbucket.org/oriadev/qunex/wiki/UsageDocs/MovementScrubbing
    # Use outputs from the command `general_compute_bold_list_stats`
    # In (filename).bstats,the columns may be provided in the following order:
    # frame number, n, m, min, max, var, sd, dvars, dvarsm, dvarsme, fd.

    homedir = filein.homedir
    sublist = filein.sublist
    motion_type = param.motion_type
    n_dummy = param.n_dummy
    run_order = param.run_order

    motion_data_all = np.array([])
    subiter = 1
    for subID in sublist:

        # ------------------------------------------
        #       Individual motion data analysis
        # ------------------------------------------
        msg = "     (Subject " + str(subiter) + " runs " + str(run_order) + \
            ") load frame-wise motion estimates(" + motion_type + ").."
        logging.info(msg)
        motion_data_ind = np.array([])

        runiter = 1
        for n_run in run_order:

            # - Load motion estimates in each run from QuNex output
            motion_data_filen = homedir + str(subID) + \
                "/images/functional/movement/bold" + str(n_run) + ".bstats"
            motion_dlist = np.genfromtxt(motion_data_filen, names=True)
            idx = np.where(np.char.find(motion_dlist.dtype.names, motion_type) == 0)
            motion_data_run = np.genfromtxt(motion_data_filen, skip_header=1, usecols=idx[0])

            # - Remove dummy time-frames
            motion_data_run = np.delete(motion_data_run, range(n_dummy), 0)

            # - Concatenate individual runs ( ((n_runs) x n_timeframes) x 1 )
            if runiter == 1:
                motion_data_ind = motion_data_run
            elif runiter > 1:
                motion_data_ind = np.concatenate((motion_data_ind, motion_data_run), axis=0)

            runiter = runiter+1

        # ------------------------------------------
        #       Stack individual motion data
        # ------------------------------------------

        if subiter == 1:
            motion_data_all = motion_data_ind.reshape(-1, 1)
        elif subiter > 1:
            motion_data_all = np.concatenate(
                (motion_data_all, motion_data_ind.reshape(-1, 1)), axis=1)
        subiter = subiter+1

    msg = "     >> Output: a (" + str(motion_data_all.shape[0]) + " x " + str(
        motion_data_all.shape[1]) + ") array of (concatenated " + \
        motion_type + " timeseries x n_subjects)."
    logging.info(msg)

    return motion_data_all



def load_hpc_groupdata_wb_daylabel(filein, param):
    homedir = filein.homedir
    sublist = filein.sublist
    fname = filein.fname
    gsr = param.gsr
    unit = param.unit
    sdim = param.sdim
    tdim = param.tdim

    msg = "============================================"
    logging.info(msg)
    msg = "[whole-brain] Load " + unit + \
        "-level time-series data preprocessed with " + gsr + ".."
    logging.info(msg)

    data_all = np.empty((len(sublist) * tdim, sdim), dtype=np.float32)
    sublabel_all = np.empty((len(sublist) * tdim, ), dtype=np.int)
    daylabel_all = np.empty((len(sublist) * tdim, ), dtype=np.int)
    ptr = 0
    for idx, subID in enumerate(sublist):
        # - Load fMRI data
        dataname = os.path.join(homedir, str(subID), "images", "functional", fname)
        zdata = load_hpc_norm_subject_wb(dataname)
        data_all[ptr:ptr+zdata.shape[0], :] = zdata
        # - Create subject label
        subid_v = [subID] * zdata.shape[0]
        subid_v = np.array(subid_v)
        sublabel_all[ptr:ptr+zdata.shape[0], ] = subid_v
        # - Creat day label
        day_v = np.empty(zdata.shape[0]); day_v.fill(1)
        runlen=int(zdata.shape[0]/2)
        day_v[runlen:] = 2 
        daylabel_all[ptr:ptr+zdata.shape[0], ] = day_v
        # - Update/delete variables
        ptr += zdata.shape[0]

        msg = "(Subject " + str(idx) + ")" + dataname + " " + \
            ", data:" + str(zdata.shape) + ", subject label:" + str(subid_v.shape) + \
            ", day label:" + str(day_v.shape)
        logging.info(msg)

        del zdata, subid_v

    msg = ">> Output 1: a (" + str(data_all.shape[0]) + " x " + \
        str(data_all.shape[1]) + ") array of (group concatenated time-series x space)."
    logging.info(msg)
    msg = ">> Output 2: a " + str(sublabel_all.shape) + " array of (group concatenated subject label)."
    logging.info(msg)
    msg = ">> Output 3: a " + str(daylabel_all.shape[0]) + " array of (group concatenated day label)."
    logging.info(msg)    
    return data_all, sublabel_all, daylabel_all


