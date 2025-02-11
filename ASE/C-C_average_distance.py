from ase.io import read
# from ase.geometry import distance, get_distances
from ase.neighborlist import natural_cutoffs, NeighborList

# 读取POSCAR文件
import os
cwd = os.getcwd()
print(cwd)
file_path = os.path.join(cwd, 'CONTCAR')  #use join to add path and file name. It could atomic add path according to different OS.
print(file_path)
atoms = read(file_path)

# 构建邻接列表
cutoffs = natural_cutoffs(atoms)
nl = NeighborList(cutoffs, self_interaction=False, bothways=True)
nl.update(atoms)
# matrix = nl.get_connectivity_matrix(sparse=False)
# print(matrix)


# 获取所有碳原子的索引
carbon_indices = [atom.index for atom in atoms if atom.symbol == 'C']
# print(carbon_indices)

# 计算相邻碳原子之间的距离
bond_lengths = []
for i in carbon_indices:
    indices, offsets = nl.get_neighbors(i)
    for j, offset in zip(indices, offsets):
        if atoms[j].symbol == 'C':
            print(i, j)
            bond_length = atoms.get_distance(i, j, mic=True, vector=False)
            # mic=True to use the Minimum Image Convention. vector=True gives the distance vector (from a0 to a1)
            print(bond_length)
            bond_lengths.append(bond_length)

# 计算平均键长
mean_bond_length = sum(bond_lengths) / len(bond_lengths)

print(f'Average C-C bond length: {mean_bond_length:.5f} Å')