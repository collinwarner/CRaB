#!/bin/bash

# Remove previous modules
module purge

# Load required modules for pokerbots
module load anaconda3/2021.11
source activate workspace 
module load cmake/3.17.3
module load boost/1.70.0
module load gcc/8.3.0
module load engaging/git/2.4.0-rc3
