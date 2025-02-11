from ase.io import read
import os
os.environ['VASP_PP_PATH'] = "/home/yuqinghan/Software/VASP/POTCAR/ASE_POTCAR"
from ase.calculators.vasp import Vasp

atoms = read('./POSCAR')
System_Name = str(atoms.symbols)   # 等效于 atoms.get_chemical_formula(mode='reduce')

magmom_dict = dict(C=0, N=0, O=0, H=0, Na=0, Cl=0, Mn=6, Fe=5,Co=4,Ni=3,Cu=2, I=0)
MAGMOM_list = [magmom_dict[element] for element in atoms.get_chemical_symbols()]    # 对原子设定非零磁矩，生成INCAR自动开启自旋极化和初始磁矩设置
atoms.set_initial_magnetic_moments(MAGMOM_list)

calc = Vasp(command = 'mpirun -genv I_MPI_DEVICE ssm -machinefile /tmp/nodefile.$$ -n $NP /opt/vasp.5.4.1/bin/vasp_std >> log',
system=System_Name, ismear=0, sigma=0.1, lreal="Auto", algo="Fast", kspacing = 0.38, kgamma = True, ispin = 2, ivdw=12,
ibrion= -1 , isif=2, nsw=0, encut=480, ncore=12, lwave=False, lcharg=False, xc="PBE")
calc.write_input(atoms)
# print(dir(calc))
