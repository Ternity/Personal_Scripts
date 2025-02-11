from ase.io.vasp import read_vasp
import os
from ase import Atom, Atoms
from ase.calculators.vasp import Vasp

atoms = read_vasp('./POSCAR')
magmom_dict = dict(
H =1,He=0,Li=1,Be=0,B =1,C =2,N =3,O =2,F =1,Ne=0,Na=1,Mg=0,Al=1,Si=2,P =3,S =2,Cl=1,Ar=0,K =1,Ca=0,Sc=2,Ti=3,V =4,Cr=6,Mn=6,
Fe=5,Co=4,Ni=3,Cu=2,Zn=1,Ga=1,Ge=2,As=3,Se=2,Br=1,Kr=0,Rb=1,Sr=0,Y =2,Zr=3,Nb=6,Mo=7,Tc=6,Ru=4,Rh=3,Pd=1,Ag=2,Cd=1,In=1,Sn=2,
Sb=3,Te=2,I =1,Xe=0,Cs=1,Ba=0,Hf=3,Ta=4,W =5,Re=6,Os=5,Ir=4,Pt=3,Au=2,Hg=0,Tl=1,Pb=2,Bi=3,Po=2,At=1,Rn=0,Fr=1,Ra=0)

MAGMOM_list = [magmom_dict["C"] for _ in range(44)]
MAGMOM_list.append(magmom_dict["N"])
MAGMOM_list.append(magmom_dict["N"])
atoms.set_initial_magnetic_moments(MAGMOM_list)

calc = Vasp(command = 'mpirun -genv I_MPI_DEVICE ssm -machinefile /tmp/nodefile.$$ -n $NP /opt/vasp.5.4.1/bin/vasp_std >> log',
system="TM@2N-gamma-CN",
ismear=0,
encut=520,
sigma=0.05,
ediff = 1E-4,
algo="Fast",
nelm=100,
ibrion=2,
potim=0.1,
nsw=600,
isif=2,
xc="PBE",
lwave=False,
lcharg=False,
ncore=12,
ivdw=11,
kpts=(2,2,1),
)
calc.write_input(atoms)
#atoms.calc = calc
#atoms.get_potential_energy()
