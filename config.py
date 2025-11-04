#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration file for sequential phase field simulation control.

Author: Guanshihan Du

This file defines the system configuration and simulation steps.
Modify CONFIG and STEPS according to your simulation requirements.
"""

# ==================== System Configuration ====================
CONFIG = {
    # Source directory containing template files
    'SOURCE_DIR': 'origin',
    
    # Job submission script
    'JOB_SCRIPT': 'V-3.sh',
    
    # Input file name
    'INPUT_FILE': 'inputN.in',
    
    # Data extraction configuration
    'NUM_CHUNKS': 20,                    # Number of MPI chunks
    'DAT_PATTERN': 'PELOOP.%08d.dat',    # Data file pattern
    
    # Job monitoring configuration
    'CHECK_INTERVAL': 60,                 # Status check interval (seconds)
    
    # Log file name
    'LOG_FILE': 'sequential_run.log',
}

# ==================== Simulation Steps Configuration ====================
# Each step is a dictionary with the following keys:
#   - 'name': Step name (string)
#   - 'description': Step description (string)
#   - 'params': Parameters to modify (dict, keys are 'lineN' where N is line number)
#   - 'final_step': Total step number at the end of this step (int)
#
# Important notes:
#   - For each step, kstart should equal the previous step's final_step
#   - final_step should equal kstart + kstep
#   - Set np6=1 (in line10) to read pxyz.in from previous step (except first step)

STEPS = [
    {
        'name': 'Step 1: Apply positive field',
        'description': 'mx0=100, phi0=40, 5000 steps',
        'params': {
            'line8': '5000 1000 1000 0',              # kstep kprint kbackup kstart
            'line10': '1 0 0 1',                      # np6 (1=read pxyz.in, 0=random)
            'line23': '1 5 20 100 20 40.0 0 100 8',   # Electrode position mx0=100
            'line24': '40.0 0.0 0.01 0.6 0.4 0.0',   # phi0=40 (positive field)
        },
        'final_step': 5000,
    },
    {
        'name': 'Step 2: Relax',
        'description': 'mx0=100, phi0=0, 2000 steps',
        'params': {
            'line8': '2000 1000 1000 5000',           # kstart=5000 (continue from step 1)
            'line10': '1 0 0 1',                      # np6=1 (read from step 1)
            'line23': '1 5 20 100 20 40.0 0 100 8',   # Keep electrode position
            'line24': '0.0 0.0 0.01 0.6 0.4 0.0',    # phi0=0 (remove field)
        },
        'final_step': 7000,                           # 5000 + 2000
    },
    # Add more steps as needed...
]

