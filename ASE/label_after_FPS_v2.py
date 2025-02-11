# import matplotlib.pyplot as plt
import shutil, os
from dpdispatcher import Machine, Resources, Task, Submission
import datetime
from ase.io import read, write
from ase.calculators.vasp import Vasp
os.environ['VASP_PP_PATH'] = "/home/yuqinghan/Software/VASP/POTCAR/ASE_POTCAR"


def generat_input_file(list_of_All_Structures, submit_dir='./submit/'):
    for index, atoms in enumerate(list_of_All_Structures):
        # if dir exists, the jump this loop and print dirname
        if os.path.exists(submit_dir+str(index)):
            print('dir exists: '+str(index)+', please chack')
            continue
        else:
            # mkdir for each dump
            os.mkdir(submit_dir+str(index))
            # gen VASP input file
            System_Name = str(atoms.symbols)   # 等效于 atoms.get_chemical_formula(mode='reduce')
            magmom_dict = dict(C=0, N=0, O=0, H=0, Na=0, Cl=0, Mn=5, Fe=4,Co=3, Ni=3, Cu=0, I=0)
            MAGMOM_list = [magmom_dict[element] for element in atoms.get_chemical_symbols()]    # 对原子设定非零磁矩，生成INCAR自动开启自旋极化和初始磁矩设置
            atoms.set_initial_magnetic_moments(MAGMOM_list)
            calc = Vasp(command = 'mpirun -genv I_MPI_DEVICE ssm -machinefile /tmp/nodefile.$$ -n $NP /opt/vasp.5.4.1/bin/vasp_std >> log',
            system=System_Name, ismear=0, sigma=0.1, lreal="Auto", algo="Fast", kspacing = 0.38, kgamma = True, ispin = 2, ivdw=12,
            ibrion= -1 , isif=2, nsw=0, encut=480, ncore=12, lwave=False, lcharg=False, xc="PBE",
            directory = submit_dir+str(index))
            calc.write_input(atoms)
            os.remove(submit_dir + str(index) + '/ase-sort.dat')
    return print('input_file has been generated')

def generate_tasks_list(list_of_All_Structures, submit_dir='submit/'):
    tasks = []
    for index, _ in enumerate(list_of_All_Structures):
        task = Task(command='mpirun -np 24 /opt/vasp.5.4.1/bin/vasp_std', task_work_path=submit_dir+f'{index}/', forward_files=['INCAR', 'POSCAR', 'POTCAR'], 
                    backward_files=['OSZICAR', 'OUTCAR', 'vasprun.xml'], outlog='vasp.out', errlog='vasp.out')
        tasks.append(task)
    print('dpdispatcher-tasks have been generated')
    return tasks



atoms_list_1 = read('/home/yuqinghan/Project/DAC/data/activate-learning/iter03/selection/select_structures_by_FPS_12_Fe2N7HCl.xyz', index=':', format='extxyz')
atoms_list_2 = read('/home/yuqinghan/Project/DAC/data/activate-learning/iter03/selection/select_structures_by_FPS_13_Fe2N6NaOH.xyz', index=':', format='extxyz')
atoms_list_3 = read('/home/yuqinghan/Project/DAC/data/activate-learning/iter03/selection/select_structures_by_FPS_15_Fe2N7NaOH.xyz', index=':', format='extxyz')
atoms_list_4 = read('/home/yuqinghan/Project/DAC/data/activate-learning/iter03/selection/select_structures_by_FPS_19_Fe2N6HCl.xyz', index=':', format='extxyz')
list_of_All_Structures = []
for i in range(1, 5):    # range(1,5) = int([1,5))
    list_of_All_Structures += eval(f'atoms_list_{i}')  # 使用eval动态生成变量名

generat_input_file(list_of_All_Structures, submit_dir='./label-mix/')
task_list = generate_tasks_list(list_of_All_Structures, 'label-mix/')
# load machine and resources
machine = Machine(batch_type="PBS", context_type="SSHContext",
                  remote_profile = {
					"hostname": "42.244.25.39",
                    "port": 8019,
					"username": "yuqinghan",
					"key_filename": "/home/yuqinghan/.ssh/CPU_75_mu06",
					"timeout": 60},
                  local_root="/home/yuqinghan/Project/DAC/data/activate-learning/iter03/", 
                  remote_root='/home/yuqinghan/Project/Fe-C-N4/DPGEN-run')
resources = Resources(number_node=1, cpu_per_node=24, gpu_per_node=0, queue_name='batch', group_size=5, para_deg=1, custom_flags=["#PBS -N fp-dump-selected"], source_list=['/home/yuqinghan/Project/Fe-C-N4/label.env'])
# submit jobs
submission = Submission(work_base='/home/yuqinghan/Project/DAC/data/activate-learning/iter03/', machine=machine, resources=resources, task_list=task_list)
submission.run_submission()

print(f"All mission has been done at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")