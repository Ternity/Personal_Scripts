import MDAnalysis as mda
from MDAnalysis.analysis import distances
import numpy as np
from tqdm import tqdm

pre_dir = 'C:\\Users\\18040\\Desktop\\'
u = mda.Universe(pre_dir+'init.data', pre_dir+'traj(2).lammpstrj', format='LAMMPSDUMP', atom_style='id type x y z')
# 选择你感兴趣的原子
hydrogens = u.select_atoms('type 1'); B_atoms = u.select_atoms('type 2'); N_atoms = u.select_atoms('type 3')
# print(u)
num_atoms = hydrogens.n_atoms

with open('H2 Statistics.txt', 'w') as f:
    for ts in tqdm(u.trajectory):
        dist = distances.self_distance_array(hydrogens.positions, box=u.dimensions,backend='OpenMP')
        k = 0; m = 0; dist_pair = np.zeros((num_atoms, num_atoms))    # dist_pair = [[0 for _ in range(num_atoms-i-1)] for i in range(num_atoms)]
        for i in range(num_atoms):
            for j in range(i+1, num_atoms):
                # print(f'i={i}, j={j}, k={k}')
                dist_pair[i][j] = dist[k]
                if dist[k] < 0.83:
                    # print(f'Find H2, frame={ts.frame:04d}, H_1 index={i:03d}, H_2 index={j:03d} dist={dist[k]}')
                    f.write(f'Find H2, frame={ts.frame:04d}, H_1 index={i:03d}, H_2 index={j:03d} dist={dist[k]}\n')
                    m += 1
                k += 1
        # print(f'Total H2 number: {m:02d} in frame {ts.frame:04d}')
        f.write(f'Total H2 number: {m:02d} in frame {ts.frame:04d}\n')
        f.write(f'\n')