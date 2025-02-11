import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["TF_INTRA_OP_PARALLELISM_THREADS"] = "1" 
os.environ["TF_INTER_OP_PARALLELISM_THREADS"] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

from ase.io import read,write
from deepmd.calculator import DP
from ase.optimize import BFGS
from ase.visualize import view


for i in range(1,12):
    atoms=read("POSCAR_OH", format="vasp")
    dp_model = DP(model="/home/qhyu/Project/Fe-C-N4/lmp/frozen_model/model_files/frozen_model_0_iter" + "{:02d}".format(i) + ".pb")
    atoms.calc = dp_model
    # forces = atoms.get_forces()
    dyn = BFGS(atoms, maxstep=0.025, alpha=100, logfile='BFGS.log', trajectory="opt.traj")
    dyn.run(fmax=1e-4)
    energy_final = atoms.get_potential_energy()
    print(f'\n\nenergy_final={energy_final}')