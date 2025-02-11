from ase.io import read
from ase.visualize import view
import numpy as np
import os
os.environ['VASP_PP_PATH']='../../ASE_POTCAR'


file_path = 'ACF.dat'
structure_path = 'POSCAR'


with open(file_path, 'r') as file:
    lines = file.readlines()[2:-4]  # 跳过前两行并避开最后四行
now_nelect = []
for line in lines:
    columns = line.split()
    now_nelect.append(float(columns[4]))


atoms = read(structure_path)
from ase.calculators.vasp.create_input import GenerateVaspInput
from ase.calculators.vasp.create_input import read_potcar_numbers_of_electrons,open_potcar
cls_gen_input = GenerateVaspInput()
cls_gen_input.initialize(atoms=atoms)
# total_default_nelect = cls_gen_input.default_nelect_from_ppp()
symbol_valences = []
ppp_list = cls_gen_input.ppp_list
for filename in ppp_list:
    with open_potcar(filename=filename) as ppp_file:
        r = read_potcar_numbers_of_electrons(ppp_file)
        symbol_valences.extend(r)
symbol_valences_dict = dict(symbol_valences)
default_nelect = [symbol_valences_dict.get(atom_symbol, None) for atom_symbol in atoms.get_chemical_symbols()]


net_charges = list(map(lambda x, y: y-x, now_nelect, default_nelect))
atoms.set_initial_charges(net_charges)
view(atoms)
