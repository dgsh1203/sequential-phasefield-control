# Sequential Phase Field Simulation Control

A universal Python toolkit for automating sequential parameter adjustment and multi-step phase field simulations.

**Author:** Guanshihan Du

## Overview

This toolkit automates the execution of multi-step phase field simulations by:

1. Modifying input parameters for each step
2. Submitting jobs to compute nodes via SLURM
3. Monitoring job status until completion
4. Extracting final state from output files
5. Automatically progressing to the next step with updated initial conditions

## Features

- **Automated sequential execution**: No manual intervention required
- **Configurable parameters**: Easy-to-modify Python configuration file
- **Job monitoring**: Automatic status checking and progress tracking
- **State extraction**: Automatic extraction of final states for next step
- **Configuration validation**: Built-in preview and validation tools
- **Comprehensive logging**: Detailed logs for debugging and monitoring

## Requirements

- Python 3.6+
- NumPy
- SLURM workload manager
- Phase field simulation code that outputs PELOOP data files

## Installation

No installation required. Simply download the two Python scripts:

- `sequential_run.py`: Main control script
- `config.py`: Configuration file

## Quick Start

### 1. Configure Your Simulation

Edit `config.py` to define your simulation steps:

```python
CONFIG = {
    'SOURCE_DIR': 'origin',           # Source directory with template files
    'JOB_SCRIPT': 'V-3.sh',           # SLURM job submission script
    'INPUT_FILE': 'inputN.in',        # Input file name
    'NUM_CHUNKS': 20,                 # Number of MPI chunks
    'DAT_PATTERN': 'PELOOP.%08d.dat', # Data file pattern
    'CHECK_INTERVAL': 60,             # Status check interval (seconds)
    'LOG_FILE': 'sequential_run.log', # Log file name
}

STEPS = [
    {
        'name': 'Step 1: Apply field',
        'description': 'mx0=100, phi0=40, 5000 steps',
        'params': {
            'line8': '5000 1000 1000 0',    # kstep kprint kbackup kstart
            'line10': '1 0 0 1',            # np6=1 (read pxyz.in)
            'line23': '1 5 20 100 20 40.0 0 100 8',
            'line24': '40.0 0.0 0.01 0.6 0.4 0.0',
        },
        'final_step': 5000,
    },
    # Add more steps...
]
```

### 2. Preview Configuration

Before running, preview and validate your configuration:

```bash
python3 sequential_run.py --preview
```

### 3. Run Simulation

Execute the sequential simulation:

```bash
python3 sequential_run.py              # With confirmation prompt
python3 sequential_run.py --auto-yes   # Without confirmation
```

## Configuration Guide

### CONFIG Dictionary

- `SOURCE_DIR`: Directory containing template files (default: `'origin'`)
- `JOB_SCRIPT`: SLURM job submission script name (default: `'V-3.sh'`)
- `INPUT_FILE`: Input file name to modify (default: `'inputN.in'`)
- `NUM_CHUNKS`: Number of MPI data chunks (default: `20`)
- `DAT_PATTERN`: Pattern for data files (default: `'PELOOP.%08d.dat'`)
- `CHECK_INTERVAL`: Job status check interval in seconds (default: `60`)
- `LOG_FILE`: Log file name (default: `'sequential_run.log'`)

### STEPS List

Each step is a dictionary with:

- `name`: Step name (string)
- `description`: Step description (string)
- `params`: Dictionary mapping line numbers to new content
  - Keys: `'lineN'` where N is the line number (1-indexed)
  - Values: New content for that line (string)
- `final_step`: Total step number at the end of this step (int)

**Important Configuration Rules:**

1. For each step (except the first), `kstart` (4th value in `line8`) must equal the previous step's `final_step`
2. For each step, `final_step` must equal `kstart + kstep` (1st value in `line8`)
3. For steps after the first, set `np6=1` (1st value in `line10`) to read `pxyz.in` from the previous step

## Workflow

1. **Create work directory**: Copies template files from `SOURCE_DIR`
2. **Modify parameters**: Updates input file according to step configuration
3. **Submit job**: Submits simulation job via SLURM
4. **Monitor status**: Periodically checks job status until completion
5. **Extract data**: Extracts final state from `PELOOP.*.dat` files
6. **Generate initial condition**: Creates `pxyz.in` for next step
7. **Backup files**: Backs up key files to `stepN_backup/` directory
8. **Proceed to next step**: Repeats steps 2-7 for remaining steps

## Output Files

The script creates:

- `seq_run_YYYYMMDD_HHMMSS/`: Work directory with simulation files
  - `inputN.in`: Modified input file for each step
  - `pxyz.in`: Initial condition file for each step
  - `stepN_backup/`: Backup directory for each step
- `sequential_run.log`: Execution log file

## Monitoring

### View Log File

```bash
tail -f sequential_run.log
```

### Check Job Status

```bash
squeue -u $USER
```

## Command-Line Options

- `--preview`: Preview and validate configuration without running
- `--auto-yes`: Skip confirmation prompt and run immediately

## Examples

### Basic Usage

```bash
# Preview configuration
python3 sequential_run.py --preview

# Run with confirmation
python3 sequential_run.py

# Run without confirmation
python3 sequential_run.py --auto-yes
```

### Example Configuration

```python
STEPS = [
    {
        'name': 'Step 1: Initial field application',
        'description': 'Apply positive field at x=100',
        'params': {
            'line8': '5000 1000 1000 0',
            'line10': '1 0 0 1',
            'line23': '1 5 20 100 20 40.0 0 100 8',
            'line24': '40.0 0.0 0.01 0.6 0.4 0.0',
        },
        'final_step': 5000,
    },
    {
        'name': 'Step 2: Relaxation',
        'description': 'Remove field and relax',
        'params': {
            'line8': '2000 1000 1000 5000',
            'line10': '1 0 0 1',
            'line24': '0.0 0.0 0.01 0.6 0.4 0.0',
        },
        'final_step': 7000,
    },
]
```

## Notes

- The script waits indefinitely for job completion (no timeout limit)
- Original `SOURCE_DIR` is never modified; all work is done in timestamped directories
- Ensure `origin/pxyz.in` exists for the first step (or set `np6=0` in first step)
- The script preserves comments in input files (text after `!`)

## License

This software is provided as-is for research and educational purposes.

## Contact

**Author:** Guanshihan Du
