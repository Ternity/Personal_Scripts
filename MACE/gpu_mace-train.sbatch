#!/bin/bash
#SBATCH --job-name=MACE
#SBATCH --partition=4090
#SBATCH --nodes=1
#SBATCH --ntasks=1          # must be 1 with torchrun
#SBATCH --ntasks-per-node=1 # must be 1 with torchrun
#SBATCH --gpus-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --output=train.out

nvidia-smi dmon -s pucvmte -o T > nvdmon_job-$SLURM_JOB_ID.log &

source /opt/envs/mace0.3.14.env

# For PT backend parallelization (DDP), using `torchrun` and set `--ntasks-per-node=1` instead of `--ntasks=xx`
# torchrun --standalone --nnodes=1 --nproc_per_node=$((SLURM_NTASKS*SLURM_GPUS_ON_NODE)) /opt/apps/conda_env/mace-main/bin/mace_run_train --config="config.yaml"

# For multi nodes, use srun
# module load openmpi/4.1.1-cuda12.2
# srun /opt/apps/conda_env/mace-main/bin/mace_run_train --config="config.yaml"

# single GPU train
/opt/apps/conda_env/mace-main/bin/mace_run_train --config="config.yaml"

exit
