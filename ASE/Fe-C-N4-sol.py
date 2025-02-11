from ase.build import graphene, sort
from ase.visualize import view
from ase import Atoms
from ase.io import read, write
from ase.neighborlist import natural_cutoffs, NeighborList
import numpy as np
import os

#================================Set parameter===================================
vacuum_value = 10
N_1 = 10    #C to N
N_2 = 13
N_3 = 18
N_4 = 21    #now, must give 4 N, want 0~3 N? 有待开发
C_1 = 11    #C to be delet
C_2 = 20
Single_atom = "Fe"

ice_cub_file = 'ice_cub_move.cif'   #in file
ice_file_format = 'cif'
Output_style = 'POSCAR'             #out file, now POSCAR/lammps-data-ase/lammps-data-dpdata are available.
Output_filename = 'Fe_C_N4-sol'

#===========================生成 4*4*4 的 graphene Fe-C-N4==============================
# primitive HEX2D
Fe_C_N4 = graphene(a=2.466, size=(4, 4, 1), vacuum=vacuum_value) # lattice parameter and other things
# view(Fe_C_N4)

# change element of N
Fe_C_N4.symbols[[N_1, N_2, N_3, N_4]] = 'N'
# you could also use get_chemical_symbols() and set_chemical_symbols() to achive this

# change element of Fe
pos1 = Fe_C_N4.positions[C_1]
pos2 = Fe_C_N4.positions[C_2]
# print('pos of atoms_29 is {}, \npos of atoms_31 is {}' .format(pos1, pos2))
Fe_pos = [(pos1 + pos2)/2]      #ase need positions is a 2D list, so there is []
# print('pos of atoms_Fe will be {}' .format(Fe_pos))

Fe = Atoms(symbols=Single_atom, positions=Fe_pos)
Fe_C_N4.extend(Fe)    #append Fe to atoms

# del C atoms
del Fe_C_N4[[C_1, C_2]] 

Fe_C_N4.set_pbc((True, True, True))     #set periodic boundary conditions

# according to chemical symbols,  sorted atomic order. sort is imported from ase.build
Fe_C_N4 = sort(Fe_C_N4)


#===========================生成 2*1*1 的 经过转换的 ice-cub 晶格==============================
ice_cub = read(ice_cub_file, format=ice_file_format)    #move 版本的ice_cub是为了后期判断邻居列表方便
ice_211 = ice_cub.repeat((2, 1, 1))     #经分析, x方向*2可使冰晶与graphene匹配

#read ice_cub lattic
lattic_ice = ice_211.cell  #equal to lattic_ice = ice_2_2.get_cell()
# print(f'{lattic_ice}\n{lattic_ice[:]}')     #lattic_ice[:] 使其打印成3*3 array


# 获取H 和 O元素的索引编号
oxygen_indices = np.where(ice_211.numbers == 8)[0]      #8 is z(atomic number) of O, same as 1 in next line.  
#np.where函数找到符合()中条件的索引，该条件为ice_211中元素原子序数为8（即氧）的原子的编号。由于np.where返回的是一个元组，所以需要使用[0]来获取元组中的第一个元素。
hydrogen_indices = np.where(ice_211.numbers == 1)[0]    #使用 hydrogen_index = [atom.index for atom in ice_211 if atom.symbol == 'H'] 同样有效

# Calculate the relative positions of the hydrogen atoms with respect to the oxygen atoms
rel_positions = np.zeros((len(oxygen_indices), 2, 3))   # a 3d array is established for memory H relative positions
# np.zeros 函数接受一个 表示数组形状的 元组 作为参数, 并返回一个全为 0 的数组。在这个例子中, 数组的形状为 (len(oxygen_indices), 2, 3), 表示它有 len(oxygen_indices) 行, 2 列, 3 层。
# 由于每个氧原子都有两个相邻的氢原子，所以数组的第二维大小为 2。由于每个原子都有三个坐标（x、y 和 z），所以数组的第三维大小为 3。


cutoffs = natural_cutoffs(ice_211)  #调用ase内置自然截断半径的数据库。
# 另一种方法使用通用的截断,但是会导致部分O有>2个近邻H: cutoffs = [1.0] * len(ice_211)  其中，[1.0] * len(ice_211) 表示创建一个长度为 len(ice_211) 的列表，其中每个元素的值都为1.0

# 构建邻接列表, 计算每一个O原子与其相邻H的相对位置矢量
nl = NeighborList(cutoffs, self_interaction=False, bothways=True)
nl.update(ice_211)
for i, oxygen_index in enumerate(oxygen_indices):
    indices, offsets = nl.get_neighbors(oxygen_index)
    for j, index in enumerate(indices):
        if index in hydrogen_indices:
            rel_positions[i, j] = ice_211.positions[index] - ice_211.positions[oxygen_index]

# 根据Fe-C-N4晶格, 构建新的ice晶格, 即转换晶格
a = Fe_C_N4.cell[:2]
b = lattic_ice[2]
new_cell_of_ice = np.vstack((a, b))
ice_211.set_cell(new_cell_of_ice, scale_atoms=True)


# Update the positions of the hydrogen atoms
for i, oxygen_index in enumerate(oxygen_indices):
    indices, offsets = nl.get_neighbors(oxygen_index)
    for j, index in enumerate(indices):
        if index in hydrogen_indices:
            ice_211.positions[index] = ice_211.positions[oxygen_index] + rel_positions[i, j]

#===========================combine Fe-C-N4 with ice==============================
# 先填充下半部分
Fe_C_N4.extend(ice_211)

# 再填充上半部分
# 计算ice_211 所有原子z坐标最低点
z_min = min(ice_211.positions[:, 2])
# 将ice_211沿 z 轴移动，使其底部与Fe-C-N4的中间再+3Å对齐
z_middle_Fe_C_N4 = (Fe_C_N4.cell[2][2])/2
ice_211.positions[:, 2] += (z_middle_Fe_C_N4 - z_min + 3)

Fe_C_N4.extend(ice_211)

#===============================out put==================================
# 为元素分配标签,用于sort重排元素
tags = [0 if atom.symbol == 'C' else 1 if atom.symbol == 'N' else 2 if atom.symbol == 'Fe' else 3 if atom.symbol == 'O' else 4 if atom.symbol == 'H' else 5 for atom in Fe_C_N4]
Fe_C_N4 = sort(Fe_C_N4, tags)       #根据元素的tags, 从小到大排序, 相当于给原子排序
# view(Fe_C_N4)

if Output_style == 'POSCAR':
    write(Output_filename + '.poscar', Fe_C_N4, format='vasp', label='Fe-C-N4 System')

elif Output_style == 'lammps-data-ase':
    write(Output_filename + '.data', Fe_C_N4, format='lammps-data', masses=True, units='metal', atom_style='atomic')

elif Output_style == 'lammps-data-dpdata':
    write(Output_filename + '.poscar', Fe_C_N4, format='vasp', label='Fe-C-N4 System')
    import dpdata
    Fe_C_N4_sol_poscar = dpdata.System(file_name='Fe_C_N4-sol.poscar', fmt='vasp/poscar')
    Fe_C_N4_sol_poscar.to('lammps/lmp', 'Fe_C_N4-sol-2.data')
    with open('Fe_C_N4-sol-2.data', 'r') as f:
        lines = f.readlines()
    text_to_insert = 'Masses\n\n\t1\t12.010999996910238 # C\n\t2\t14.006999996396779 # N\n\t3\t55.844999985634189 # Fe\n\t4\t15.998999995884349 # O\n\t5\t1.0079999997406976 # H'
    lines.insert(7, '\n' + text_to_insert + '\n')
    with open('Fe_C_N4-sol-2.data', 'w') as f:
        f.writelines(lines)
    try:
        os.remove(Output_filename + '.poscar')
    except FileNotFoundError:
        print(f'File not found: {Output_filename}+.poscar')
else:
    print('Please set paramater of Output_style')
