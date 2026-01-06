#!/opt/apps/conda_env/mace-main/bin/python
from ase.io import read, write, Trajectory
import numpy as np
import time

from mace.calculators import MACECalculator
from ase.optimize import BFGS
from ase.constraints import UnitCellFilter    # ISIF=2

calculator = MACECalculator(model_path='./checkpoints/MACE-Omat-ft_run-3.model', device='cuda')
file_name = 'POSCAR-60'
init_conf = read(file_name, format='vasp')
init_conf.calc = calculator

# ============single point energy===============
# single_point_E = init_conf.get_potential_energy()
# print(f'this structure {file_name} energy is {single_point_E}')

# ============Geo Opt==========================
# ucf = UnitCellFilter(init_conf)             # ISIF=2
# opt = BFGS(ucf, logfile='opt_ucf.log')  # ISIF=2
opt = BFGS(init_conf, logfile='opt.log')
opt.run(fmax=0.01)
final_conf = init_conf
single_point_E = final_conf.get_potential_energy()
print(f'this structure {file_name} energy is {single_point_E}')
write('final_60.poscar', final_conf, format='vasp')