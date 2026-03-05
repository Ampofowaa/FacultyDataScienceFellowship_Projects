#!/bin/bash
#PBS -N Choicebased_RM
#PBS -m e
#PBS -M R.A.Frimpong@lboro.ac.uk
#PBS -l walltime=96:00:00
#PBS -l nodes=1:ppn=1
#PBS -A Li2022b
#PBS -o /mnt/gpfs01/home/bs/bsraf3/carsharing/log/Choicebased_RM/routing_matrix1/same_arr/Choicebased_RMOUT-$PBS_JOBID.out
#PBS -e /mnt/gpfs01/home/bs/bsraf3/carsharing/log/Choicebased_RM/routing_matrix1/same_arr/Choicebased_RMErr-$PBS_JOBID.err

cd /mnt/gpfs01/home/bs/bsraf3/carsharing/CorrectedPrimal/parkingcharge=5_50%cap/routing_matrix1/reopt_7/samearr

module load cplex/concert/22.1.0
module load Python/3.7.4-foss-2018a
export PYTHONPATH=$PYTHONPATH:/apps/cplex/2210/cplex/python/3.7/x86-64_linux

python3 /mnt/gpfs01/home/bs/bsraf3/carsharing/CorrectedPrimal/parkingcharge=5_50%cap/routing_matrix1/reopt_7/samearr/carsharingProject_v2.py < /mnt/gpfs01/home/bs/bsraf3/carsharing/probIndex/param.$PBS_ARRAYID.dat