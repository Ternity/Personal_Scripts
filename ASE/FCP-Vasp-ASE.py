#from ase.calculators.FCPelectrochem import FCP
from ase.calculators.vasp.vaspFCP import VaspFCP
from ase.calculators.vasp import Vasp
from ase.io import read
from ase.optimize import LBFGS

calc=VaspFCP(xc='PBE', #functional
      pp='PBE',            #type of pseudopotential
      kpts=(3, 3, 1),      #kpoint
      ncore=4,
      lasph=True,ismear=0, sigma=0.1, algo='Fast', ediff=1E-5, prec='Accurate',  
      encut=400,  nelm=500 , addgrid='Ture',lreal='Auto',lorbit=11,lmaxmix=4, #parameters for SCF
      tau=0, lrhoion=False, lsol=True, eb_k=78.4, lambda_d_k=3.0, #parameters for vaspsol
      lwave=True, lcharg = False,              #write WAVECAR to speed up the SCF of the next ionic step
      command=r'. ~/intel/oneapi/setvars.sh &> /dev/null;killall vasp_std &> /dev/null;mpirun -n 32 ~/download/vasp.5.4.4/bin/vasp_std',
      U=0.8,                                          #electrochemical potential vs. SHE
      NELECT =50,                                 #initial guass of number of electrons
      NELECT0=50,                                    #number of electrons at the potential of zero charge
      work_ref=4.6,                                   #the work function of SHE in eV. 
      )      

atoms=read('POSCAR')
atoms.calc = calc
optimizer = LBFGS(atoms)
optimizer.run(fmax=0.01)
