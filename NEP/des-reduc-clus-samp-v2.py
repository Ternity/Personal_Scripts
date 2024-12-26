from ase.io import read, write
from pynep.select import FarthestPointSample    # 新版最远点 https://github.com/brucefan1983/GPUMD/blob/master/tools/pca_sampling/pca_sampling.py
from calorine.nep import get_descriptors, get_latent_space, get_potential_forces_and_virials
import time
# import os
# os.environ["CUDA_VISIBLE_DEVICES"] = "0"      # set for GPUNEP
import numpy as np
from tqdm import tqdm
from joblib import Parallel, delayed
from matplotlib import pyplot as plt
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.manifold import TSNE
from sklearn.cluster import DBSCAN
from scipy.spatial.distance import cdist
start_time = time.time()

#===========================Before calculations notes===========================
'''  Testing has shown that when FarthestPointSample was visualized, PCA performanced better than t-SNE; while Clusteing(DBScan),  t-SNE was better than PCA.  '''
#===========================Get global descriptor and energy for each configuration===========================
old_train_data = read('/home/yuqinghan/Project/DAC/NEP-train/activate-learning/iter02/train.xyz', index=":", format="extxyz") #  if not existl, change descriptors_old_cala to []
# trajs = read('/home/yuqinghan/Project/DAC/NEP-infer/LAMMPS/log_out/traj/dump_stage1.xyz', index=":", format="lammps-dump-text", specorder=["C","N","Fe","O","H","Na","Cl"])
trajs = read('/home/yuqinghan/Project/DAC/NEP-train/activate-learning/iter03/system_contain_Fe2.xyz',index=':',format='extxyz')
nep_model_path = '/home/yuqinghan/Project/DAC/NEP-train/activate-learning/iter02/nep.txt'
# npy_save_path = '/home/yuqinghan/Project/DAC/data/activate-learning/iter03/selection'
npy_save_path = '/home/yuqinghan/Project/DAC/NEP-train/activate-learning/iter03'

def cal_nep_info(atoms, nep_model_path):
    descriptor = get_descriptors(atoms, nep_model_path)   # for Calorine
    lat = get_latent_space(atoms, nep_model_path)         # for Calorine
    per_atom_energies, _,_ = get_potential_forces_and_virials(atoms, nep_model_path)
    return np.mean(descriptor,axis=0), np.mean(per_atom_energies)

# change stress to virial with(+→-) and delete stress
for frame in trajs: 
    stress_value_negative_eV_A = frame.calc.results.get('stress', None)
    if stress_value_negative_eV_A is None:
        print("===There is no labeled data in trajs, trajs isn't a labeled data===.")
        break
    elif len(stress_value_negative_eV_A) == 9:
        frame.info['virial'] = -stress_value_negative_eV_A*frame.get_volume()
        del frame.calc.results['stress']
    elif len(stress_value_negative_eV_A) == 6:
        xx, yy, zz, yz, xz, xy = -stress_value_negative_eV_A*frame.get_volume()
        frame.info['virial'] = np.array([(xx, xy, xz), (xy, yy, yz), (xz, yz, zz)])
        del frame.calc.results['stress']
    else:
        raise Exception(f'''Number of stress ({len(stress_value_negative_eV_A)}) not equal to 6 or 9''')

des_ene = Parallel(n_jobs=40)(delayed(cal_nep_info)(frame, nep_model_path) for frame in tqdm(trajs))    # too slow, must Parallel, speed up *30 times
des = np.array([temp_d[0] for temp_d in des_ene])     # fit_transform need a array while not a list
energy = [temp_e[1] for temp_e in des_ene]
np.save(npy_save_path + '/des.npy', des)

des_ene_old_data = Parallel(n_jobs=40)(delayed(cal_nep_info)(frame, nep_model_path) for frame in tqdm(old_train_data))
des_old_data = np.array([temp_d[0] for temp_d in des_ene_old_data])
np.save(npy_save_path + '/des_old_data.npy', des_old_data)

descriptors_cala = np.load(npy_save_path + '/des.npy')
descriptors_old_cala = np.load(npy_save_path + '/des_old_data.npy') # if not existl, change descriptors_old_cala to []

#===========================Select configurations using Farthest Point Sample===========================
selector = FarthestPointSample(min_distance=0.005)
indices = selector.select(new_data=descriptors_cala, now_data=descriptors_old_cala, max_select=50);     print(f'===selected {len(indices)} structures by FarthestPointSample===')
unselected_indices = [u_i for u_i in list(range(len(descriptors_cala))) if u_i not in indices]
trajs_selected_by_FPS = [trajs[i] for i in indices]; trajs_unselected_by_FPS = [trajs[i] for i in unselected_indices]     # then one can export to data set
write(npy_save_path + '/select_structures_by_FPS_'+str(len(trajs_selected_by_FPS))+'.xyz', trajs_selected_by_FPS, format='extxyz')

#===========================Reduce the dimension of global descriptors===========================
# PCA
""" scaler = StandardScaler()
scaler.fit(descriptors_cala)
descriptors_cala = scaler.transform(descriptors_cala)

reducer = PCA(n_components=3, svd_solver='full')   # , svd_solver='full'
reducer.fit(descriptors_cala)
proj = reducer.transform(descriptors_cala)
proj_selected = reducer.transform(np.array([descriptors_cala[i] for i in indices]))
explained_variance_ratios = reducer.explained_variance_ratio_
print(f'===PCA reduce components percentages:{explained_variance_ratios}===') """

# t-SNE    may be similar to DBScan
reducer = TSNE(n_components=3, init='pca', random_state=0, n_jobs=40)      # param select can see: https://distill.pub/2016/misread-tsne/
proj = reducer.fit_transform(descriptors_cala)
proj_selected = reducer.fit_transform(np.array([descriptors_cala[i] for i in indices]))    # 这里, 必须重新降维, 因为降维后结构顺序乱了且低维化
""" import pandas as pd
energy = np.array(energy)
proj = np.column_stack((proj, energy))
pd.DataFrame(proj, columns=['PC1', 'PC2', 'PC3', 'energy']).to_excel('t-SNE.xlsx', index=False) """

#===========================Cluster the reduced global descriptors===========================
# DBScan
n_selected_structures = 50; eps=None; min_samples=2; limit_per_cluster=None # None or int
if eps is None:     # 自动计算eps参数
    n_proj = len(proj)
    samples = proj[np.random.choice(n_proj, min(n_proj, n_selected_structures), replace=False)]
    eps = np.percentile(cdist(samples,proj,'euclidean'), min(100 * 10. / n_proj, 99))   # cdist return a distance matrix with shape (n_samples, n_proj)
    # print(f'选择结构数={n_selected_structures},\n距离矩阵={cdist(samples,proj,"euclidean")},\n百分比={min(100 * 10. / n_proj, 99)}\n')    
    # ⭐ analysis relationship between eps and percentile
    print(f'===generate eps atomic, eps={eps}===')
dbscan = DBSCAN(eps=eps, min_samples=min_samples, n_jobs=40)      # eps means 邻域半径    1, 3   2.5, 20
proj_clusters = dbscan.fit(proj)
n_clusters = len(set(proj_clusters.labels_)) - (1 if -1 in proj_clusters.labels_ else 0)    # set()转化为集合, 去重, 不算噪声
n_noise = list(proj_clusters.labels_).count(-1)     # DBSCAN return -1 means noise
# n_clusters_elements = [list(a.labels_).count(i) for i in range(n_clusters)]
print(f'===After clusting by DBScan n_clusters={n_clusters}, n_noise={n_noise}===')      # ,\n n_clusters_elements={n_clusters_elements}

labels: np.ndarray = proj_clusters.labels_; groups = {}     # labels: np.ndarray = xxx 声明变量类型, 尽管对python解释器没用
index = np.arange(len(labels))                  # 必须使用ndarray, 为了下面的布尔索引
for label in set(labels):                       # set()去重
    groups[label] = index[labels == label]      # labels == label, numpy数组的布尔索引, 返回一个bool数组, labels数组中等于label的为True; index[bool数组]返回一个数组, 里面是True对应的index
selected_structures_by_cluster = []

if limit_per_cluster is None:                   # Not set limit_per_cluster? use average value: n_selected_structures/(n_clusters+1)
    print(f'===generate limit_per_cluster atomic, ={n_selected_structures/(n_clusters+1)}===')
    for frames_number in groups.values():       # dict.values() return all value of dict
        if len(frames_number) < n_selected_structures/(n_clusters+1):
            selected_structures_by_cluster += list(frames_number)   
        else:
            selected_structures_by_cluster += list(frames_number[:int(n_selected_structures/(n_clusters+1))])
else:
    for frames_number in groups.values():           # dict.values() return all value of dict
        if len(frames_number) < limit_per_cluster:  # ndarray to list
            selected_structures_by_cluster += list(frames_number)
        else:
            selected_structures_by_cluster += list(frames_number[:limit_per_cluster])       # 列表中从头放入, 而不是随机选。 有空改成随机选择的
print(f'===优选{len(selected_structures_by_cluster)}个结构===')

trajs_selected_by_cluster = [trajs[i] for i in selected_structures_by_cluster]              # Then write to extxyz using ase.io.write
proj_selected_by_cluster = reducer.fit_transform(np.array([descriptors_cala[i] for i in selected_structures_by_cluster]))

# write proj_selected_by_cluster to extxyz format
write(npy_save_path + '/select_structures_by_reduce_cluster'+str(len(selected_structures_by_cluster))+'.xyz', trajs_selected_by_cluster, format='extxyz')

#===============尝试全程基于ASAPlib实现描述符、降维、聚类的实现================

""" # OPTICS
# laio_db
# K-Means    # cluster 数量预定义
# K-medoids
# SpectralClustering """

#===========================Plot the reduced data===========================
plt.figure(figsize=(10,8))
plt.grid(ls="--")
contourf_filled = plt.scatter(proj[:,0], proj[:,1], c='black', alpha=0.1, cmap='viridis', label='all data')       # c=proj_clusters.labels_
plt.scatter(proj_selected[:,0], proj_selected[:,1], c='blue', alpha=0.25, label='selected data-FPS')
plt.scatter(proj_selected_by_cluster[:,0], proj_selected_by_cluster[:,1], c='red', alpha=0.1, label='selected data-Cluster')

cbar = plt.colorbar(contourf_filled)
cbar.set_label('Energy (eV)', rotation=90, labelpad=20, fontsize=22)   # 标签旋转角度 标签与colorbar的距离
cbar.ax.tick_params(labelsize=18)  # 设置colorbar刻度字体大小
# plt.savefig('select.png')
# plt.xlim(2.5, 6)
# plt.ylim(-6.5, 1)
plt.xlabel('PC1',fontsize=24,fontweight='bold')
plt.ylabel('PC2',fontsize=24,fontweight='bold')
plt.xticks(fontsize=18)
plt.yticks(fontsize=18)    # np.arange(-6,2,2)
plt.legend(loc=0,fontsize=22)
plt.setp(plt.gca().spines.values(),linewidth=3)   # 边框线宽设为2
# plt.tick_params(direction='in', width=2)    # 刻度线向内
plt.show()

end_time = time.time()
total_time = end_time - start_time
print(f"===Total real time: {total_time} s===")