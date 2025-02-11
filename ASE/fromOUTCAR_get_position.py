from ase import Atoms
# from ase.io.trajectory import Trajectory
from ase.visualize import view
from ase.io import read, write
# import json

def parse_outcar(file):
    with open(file, 'r') as f:
        lines = f.readlines()

    # Find the lines with "POSITION" and "ions per type"
    pos_lines = [i for i, line in enumerate(lines) if "POSITION" in line]
    ions_line = [i for i, line in enumerate(lines) if "ions per type" in line][0]
    type_line = [i for i, line in enumerate(lines) if "POSCAR" in line][0]

    # Get the elements and their counts
    elements_line = lines[type_line].split(':')[1].strip().split()
    counts = list(map(int, lines[ions_line].split('=')[1].strip().split()))

    # Create a list of all atoms
    atoms = []
    for element, count in zip(elements_line, counts):
        atoms.extend([element] * count)
    
    # # Create a Trajectory object
    # traj = Trajectory('trajectory.traj', 'w')

    # Get the positions for each frame
    
    frames = []
    for start in pos_lines:
        positions = []
        for i in range(start + 2, start + 2 + len(atoms)):
            positions.append(list(map(float, lines[i].split()[:3])))
        frames.append(Atoms(atoms, positions=positions))
    
    # # Close the trajectory file
    # traj.close()

    return frames # atoms_object

# Use the function
""" atoms = parse_outcar('OUTCAR')
json_str = json.dumps(atoms, indent=4)   #indent=4 means the indent of each line is 4 spaces
with open('positions.txt', "w") as f:
    f.write(json_str) """

outcar = parse_outcar('OUTCAR')
# view(outcar)
write('./traj_fix.xyz', outcar, format='xyz', comment='', fmt='%22.15f')


