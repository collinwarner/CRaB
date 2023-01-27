#!/bin/bash 
#SBATCH -n 8 #Request 8 tasks (cores)
#SBATCH -N 1 #Request 1 node
#SBATCH -t 0-03:00 #Request runtime of 3 hours
#SBATCH -p sched_mit_hill #Run on sched_engaging_default partition
#SBATCH --mem-per-cpu=4000 #Request 4G of memory per CPU
#SBATCH -o output_%j.txt #redirect output to output_JOBID.txt
#SBATCH -e error_%j.txt #redirect errors to error_JOBID.txt
python compute_hole_strength.py
