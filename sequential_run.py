#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sequential Parameter Adjustment and Auto-Progression Script for Phase Field Simulations

This script automates multi-step phase field simulations by:
  1. Modifying parameters in input files
  2. Submitting jobs to compute nodes
  3. Monitoring job status until completion
  4. Extracting final state from output files
  5. Automatically progressing to next step

Author: Guanshihan Du

Usage:
    python3 sequential_run.py --preview    # Preview configuration
    python3 sequential_run.py              # Run with confirmation
    python3 sequential_run.py --auto-yes    # Run without confirmation
"""

import os
import sys
import time
import subprocess
import argparse
import numpy as np
from datetime import datetime
import shutil

# Import configuration
try:
    from config import STEPS, CONFIG
except ImportError:
    print("ERROR: Cannot import STEPS and CONFIG from config.py")
    print("Please ensure config.py exists in the same directory.")
    sys.exit(1)

# Global configuration
SOURCE_DIR = CONFIG.get('SOURCE_DIR', 'origin')
JOB_SCRIPT = CONFIG.get('JOB_SCRIPT', 'V-3.sh')
INPUT_FILE = CONFIG.get('INPUT_FILE', 'inputN.in')
NUM_CHUNKS = CONFIG.get('NUM_CHUNKS', 20)
DAT_PATTERN = CONFIG.get('DAT_PATTERN', 'PELOOP.%08d.dat')
CHECK_INTERVAL = CONFIG.get('CHECK_INTERVAL', 60)
LOG_FILE = CONFIG.get('LOG_FILE', 'sequential_run.log')

WORK_DIR = None


def log_message(message, print_to_screen=True):
    """Write message to log file and optionally print to screen."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {message}"
    
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), LOG_FILE)
    with open(log_path, 'a') as f:
        f.write(log_msg + '\n')
    
    if print_to_screen:
        print(log_msg)


def read_input_file(filepath):
    """Read input file and return lines as a list."""
    with open(filepath, 'r') as f:
        return f.readlines()


def write_input_file(filepath, lines):
    """Write modified lines back to input file."""
    with open(filepath, 'w') as f:
        f.writelines(lines)


def modify_input_params(params):
    """Modify parameters in input file."""
    input_path = os.path.join(WORK_DIR, INPUT_FILE)
    
    log_message(f"Modifying {input_path}...")
    
    lines = read_input_file(input_path)
    
    for line_key, new_content in params.items():
        line_num = int(line_key.replace('line', ''))
        old_line = lines[line_num - 1]
        if '!' in old_line:
            comment = '!' + old_line.split('!', 1)[1]
            lines[line_num - 1] = new_content + ' ' + comment
        else:
            lines[line_num - 1] = new_content + '\n'
        log_message(f"  Line {line_num}: {new_content}")
    
    write_input_file(input_path, lines)
    log_message(f"✓ {INPUT_FILE} updated successfully")


def submit_job():
    """Submit job to SLURM scheduler."""
    os.chdir(WORK_DIR)
    
    try:
        result = subprocess.run(['sbatch', JOB_SCRIPT], 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True, check=True)
        output = result.stdout.strip()
        if 'Submitted batch job' in output:
            job_id = output.split()[-1]
            log_message(f"Job submitted successfully. Job ID: {job_id}")
            return job_id
        else:
            log_message(f"WARNING: Unexpected sbatch output: {output}")
            return None
    except subprocess.CalledProcessError as e:
        log_message(f"ERROR: Job submission failed: {e}")
        return None
    finally:
        os.chdir('..')


def check_job_status(job_id):
    """Check if job is still running."""
    try:
        result = subprocess.run(['squeue', '-j', job_id], 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True)
        return job_id in result.stdout
    except Exception as e:
        log_message(f"WARNING: Error checking job status: {e}")
        return False


def wait_for_job_completion(job_id):
    """Wait for job to complete with periodic status checks. No timeout limit."""
    log_message(f"Waiting for job {job_id} to complete...")
    start_time = time.time()
    
    while True:
        elapsed = time.time() - start_time
        
        if not check_job_status(job_id):
            log_message(f"Job {job_id} completed after {elapsed/60:.1f} minutes")
            return True
        
        time.sleep(CHECK_INTERVAL)
        
        if int(elapsed) % 600 == 0:
            log_message(f"Job {job_id} still running... ({elapsed/60:.0f} min elapsed)", 
                       print_to_screen=False)


def extract_final_state(final_step):
    """Extract final polarization state from PELOOP files and generate pxyz.in."""
    log_message(f"Extracting final state at step {final_step}...")
    
    pxx = pyy = pzz = None
    nx = ny = nz = None
    
    os.chdir(WORK_DIR)
    
    try:
        for chunk in range(NUM_CHUNKS):
            idx = final_step + chunk
            fname = DAT_PATTERN % idx
            
            if not os.path.isfile(fname):
                log_message(f"ERROR: Missing data file: {fname}")
                return False
            
            with open(fname) as f:
                header = f.readline().split()
                if len(header) < 3:
                    log_message(f"ERROR: Bad header in {fname}")
                    return False
                
                if pxx is None:
                    nx, ny, nz = map(int, header[:3])
                    log_message(f"Grid dimensions: nx={nx}, ny={ny}, nz={nz}")
                    pxx = np.zeros((nx, ny, nz))
                    pyy = np.zeros((nx, ny, nz))
                    pzz = np.zeros((nx, ny, nz))
                
                for line in f:
                    pts = line.split()
                    if len(pts) < 6:
                        continue
                    i1, j1, k1 = map(int, pts[:3])
                    px, py, pz = map(float, pts[3:6])
                    pxx[i1-1, j1-1, k1-1] = px
                    pyy[i1-1, j1-1, k1-1] = py
                    pzz[i1-1, j1-1, k1-1] = pz
        
        log_message("Writing pxyz.in...")
        with open('pxyz.in', 'w') as f:
            f.write(f"{nx} {ny} {nz}\n")
            for i in range(nx):
                for j in range(ny):
                    for k in range(nz):
                        f.write(f"{i+1} {j+1} {k+1} {pxx[i,j,k]:.5e} {pyy[i,j,k]:.5e} {pzz[i,j,k]:.5e}\n")
        
        log_message(f"Successfully generated pxyz.in with {nx*ny*nz} grid points")
        return True
        
    except Exception as e:
        log_message(f"ERROR during data extraction: {e}")
        return False
    finally:
        os.chdir('..')


def backup_files(step_num, step_name):
    """Backup important files for each step."""
    backup_dir = os.path.join(WORK_DIR, f"step{step_num}_backup")
    os.makedirs(backup_dir, exist_ok=True)
    
    files_to_backup = [
        os.path.join(WORK_DIR, INPUT_FILE),
        os.path.join(WORK_DIR, 'pxyz.in'),
    ]
    
    for src in files_to_backup:
        if os.path.isfile(src):
            dst = os.path.join(backup_dir, os.path.basename(src))
            shutil.copy2(src, dst)
    
    log_message(f"Backed up files to {backup_dir}/")


def preview_steps():
    """Preview and validate configuration."""
    print("="*80)
    print("SEQUENTIAL STEPS PREVIEW")
    print("="*80)
    print(f"\nTotal steps configured: {len(STEPS)}\n")
    
    for i, step in enumerate(STEPS, 1):
        print(f"\n{'='*80}")
        print(f"STEP {i}: {step['name']}")
        print(f"{'='*80}")
        print(f"Description: {step['description']}")
        print(f"Final step:  {step['final_step']}")
        
        print(f"\nParameters to modify:")
        for line, value in step['params'].items():
            line_num = line.replace('line', '')
            print(f"  Line {line_num:>2}: {value}")
        
        if i == 1:
            duration = step['final_step']
        else:
            duration = step['final_step'] - STEPS[i-2]['final_step']
        print(f"\nDuration: {duration} steps")
    
    # Validation
    print("\n" + "="*80)
    print("VALIDATION CHECKS")
    print("="*80)
    
    errors = []
    
    # Check step continuity
    for i in range(1, len(STEPS)):
        if 'line8' in STEPS[i]['params']:
            current_kstart = int(STEPS[i]['params']['line8'].split()[3])
            prev_final = STEPS[i-1]['final_step']
            if current_kstart != prev_final:
                errors.append(f"Step {i+1}: kstart={current_kstart} doesn't match previous final_step={prev_final}")
    
    # Check final_step consistency
    for i, step in enumerate(STEPS, 1):
        if 'line8' in step['params']:
            line8_parts = step['params']['line8'].split()
            kstep = int(line8_parts[0])
            kstart = int(line8_parts[3])
            expected_final = kstep + kstart
            if expected_final != step['final_step']:
                errors.append(f"Step {i}: kstep({kstep})+kstart({kstart})={expected_final} doesn't match final_step={step['final_step']}")
    
    if errors:
        print("\n❌ ERRORS FOUND:")
        for err in errors:
            print(f"  - {err}")
    else:
        print("\n✓ No critical errors found")
        print("✓✓✓ Configuration looks good!")
    
    return len(errors) == 0


def run_sequential_steps():
    """Execute all defined sequential steps."""
    log_message("="*70)
    log_message("SEQUENTIAL PARAMETER ADJUSTMENT AND AUTO-PROGRESSION")
    log_message("="*70)
    log_message(f"Total steps to execute: {len(STEPS)}\n")
    
    for step_idx, step_config in enumerate(STEPS, 1):
        log_message("\n" + "="*70)
        log_message(f"STEP {step_idx}/{len(STEPS)}: {step_config['name']}")
        log_message("="*70)
        log_message(f"Description: {step_config['description']}")
        
        log_message(f"\n[1/5] Modifying input parameters...")
        modify_input_params(step_config['params'])
        
        log_message(f"\n[2/5] Submitting job to compute nodes...")
        job_id = submit_job()
        if job_id is None:
            log_message("ERROR: Failed to submit job. Stopping.")
            return False
        
        log_message(f"\n[3/5] Waiting for job completion...")
        if not wait_for_job_completion(job_id):
            log_message("ERROR: Job did not complete successfully. Stopping.")
            return False
        
        log_message(f"\n[4/5] Extracting final state at step {step_config['final_step']}...")
        if not extract_final_state(step_config['final_step']):
            log_message("ERROR: Failed to extract final state. Stopping.")
            return False
        
        log_message(f"\n[5/5] Backing up files...")
        backup_files(step_idx, step_config['name'])
        
        log_message(f"\n✓ Step {step_idx} completed successfully!")
    
    return True


def create_work_directory():
    """Create new work directory by copying source directory."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    work_dir = f'seq_run_{timestamp}'
    
    print(f"\nCreating work directory: {work_dir}")
    print(f"Copying from: {SOURCE_DIR}")
    
    if not os.path.isdir(SOURCE_DIR):
        print(f"ERROR: Source directory not found: {SOURCE_DIR}")
        return None
    
    try:
        shutil.copytree(SOURCE_DIR, work_dir, 
                       ignore=shutil.ignore_patterns('*.dat', 'PELOOP.*', 'slurm-*', 'fort.*', 'energy_out.dat'))
        print(f"✓ Work directory created successfully")
        
        pxyz_src = os.path.join(SOURCE_DIR, 'pxyz.in')
        if os.path.isfile(pxyz_src):
            pxyz_dst = os.path.join(work_dir, 'pxyz.in')
            shutil.copy2(pxyz_src, pxyz_dst)
            print(f"✓ Copied initial pxyz.in")
        
        return work_dir
        
    except Exception as e:
        print(f"ERROR: Failed to create work directory: {e}")
        return None


def main():
    """Main entry point."""
    global WORK_DIR
    
    parser = argparse.ArgumentParser(
        description='Sequential Phase Field Simulation Controller',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 sequential_run.py --preview    # Preview configuration
  python3 sequential_run.py              # Run with confirmation
  python3 sequential_run.py --auto-yes     # Run without confirmation
        """
    )
    
    parser.add_argument('--preview', action='store_true',
                       help='Preview configuration without running')
    parser.add_argument('--auto-yes', action='store_true',
                       help='Auto-confirm execution (skip user prompt)')
    
    args = parser.parse_args()
    
    # Preview mode
    if args.preview:
        is_valid = preview_steps()
        sys.exit(0 if is_valid else 1)
    
    print("="*70)
    print("Sequential Phase Field Simulation Controller")
    print("="*70)
    print(f"Source directory: {SOURCE_DIR}")
    print(f"Total steps: {len(STEPS)}")
    print("="*70)
    
    if not os.path.isdir(SOURCE_DIR):
        print(f"ERROR: Source directory not found: {SOURCE_DIR}")
        return
    
    WORK_DIR = create_work_directory()
    if WORK_DIR is None:
        return
    
    print(f"Working directory: {WORK_DIR}")
    
    if not os.path.isfile(os.path.join(WORK_DIR, JOB_SCRIPT)):
        print(f"ERROR: Job script not found: {os.path.join(WORK_DIR, JOB_SCRIPT)}")
        return
    
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), LOG_FILE)
    with open(log_path, 'w') as f:
        f.write(f"Sequential simulation started at {datetime.now()}\n")
        f.write(f"Work directory: {WORK_DIR}\n")
        f.write("="*70 + "\n\n")
    
    print("\nSteps to be executed:")
    for i, step in enumerate(STEPS, 1):
        print(f"\n{i}. {step['name']}")
        print(f"   {step['description']}")
        print(f"   Final step: {step['final_step']}")
    
    if not args.auto_yes:
        response = input("\nProceed with execution? [y/N]: ")
        if response.lower() != 'y':
            print("Execution cancelled by user.")
            return
    
    log_message("\nStarting sequential execution...\n")
    success = run_sequential_steps()
    
    if success:
        log_message("\n" + "="*70)
        log_message("ALL STEPS COMPLETED SUCCESSFULLY!")
        log_message("="*70)
        log_message(f"\nFinal pxyz.in is ready for next simulation.")
        log_message(f"Backup folders created: step1_backup, step2_backup, ...")
        log_message(f"\nLog file: {LOG_FILE}")
    else:
        log_message("\n" + "="*70)
        log_message("EXECUTION STOPPED DUE TO ERROR")
        log_message("="*70)
        log_message(f"Check log file for details: {LOG_FILE}")


if __name__ == '__main__':
    main()
