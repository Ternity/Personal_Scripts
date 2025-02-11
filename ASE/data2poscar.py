from ase.io import read, write
from ase.visualize import view

type = {1:6, 2:26, 3:1, 4:7, 5:8}       #Z_of_type=type 需要一个字典，用于指定lammps中类型和原子序数的关系。否则, 将lammps的atoms_type视为原子序数。
Fe_C_N4_sol = read('end-stage-1.data', format='lammps-data', Z_of_type=type, style='atomic', sort_by_id=True, units='metal')
# view(Fe_C_N4_sol)
write('Fe-C-N4-sol-relax.poscar', Fe_C_N4_sol, format='vasp', label='Fe-C-N4-sol System')

