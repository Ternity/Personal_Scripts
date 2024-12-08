import numpy as np
import matplotlib.pyplot as plt
import sys, time
from scipy import interpolate
from ase.calculators.vasp import VaspChargeDensity


LOCPOTfile = './LOCPOT'
direction = 'z'
prm_chg = False
prm_macro = False
prm_macro_len = 0.0 # unit \AA
filesuffix = "_%s" % direction

starttime = time.time()
print("Starting calculation at", end='')
print(time.strftime("%H:%M:%S on %a %d %b %Y"))
# Open geometry and density class objects
#-----------------------------------------
vasp_charge = VaspChargeDensity(filename = LOCPOTfile)
potl = vasp_charge.chg[-1]
atoms = vasp_charge.atoms[-1]
del vasp_charge

# For LOCPOT files we multiply by the volume to get back to eV
if 'LOCPOT' in LOCPOTfile:
    potl=potl*atoms.get_volume()

print("\nReading file: %s" % LOCPOTfile)
print("Performing average in %s direction" % direction)

# Read in lattice parameters and scale factor
#---------------------------------------------
cell = atoms.cell

# Find length of lattice vectors
#--------------------------------
latticelength = np.dot(cell, cell.T).diagonal()
latticelength = latticelength**0.5

# Read in potential data
#------------------------
ngridpts = np.array(potl.shape)
totgridpts = ngridpts.prod()
print("Potential stored on a %dx%dx%d grid" % (ngridpts[0],ngridpts[1],ngridpts[2]))
print("Total number of points is %d" % totgridpts)
print("Reading potential data from file...", end='')
sys.stdout.flush()
print("done.")

# Perform average
#-----------------
if direction=="X":
    idir = 0
    a = 1
    b = 2
elif direction=="Y":
    a = 0
    idir = 1
    b = 2
else:
    a = 0
    b = 1
    idir = 2
a = (idir+1)%3
b = (idir+2)%3
# At each point, sum over other two indices
average = np.zeros(ngridpts[idir],np.float64)
for ipt in range(ngridpts[idir]):
    if direction=="X":
        average[ipt] = potl[ipt,:,:].sum()
    elif direction=="Y":
        average[ipt] = potl[:,ipt,:].sum()
    else:
        average[ipt] = potl[:,:,ipt].sum()

# if 'LOCPOT' in LOCPOTfile:
if not prm_chg:
    # Scale by number of grid points in the plane.
    # The resulting unit will be eV.
    average /= ngridpts[a]*ngridpts[b]
else:
    # Scale by size of area element in the plane,
    # gives unit e/Ang. I.e. integrating the resulting
    # CHG_dir file should give the total charge.
    area = np.linalg.det([ (cell[a,a], cell[a,b] ),
                           (cell[b,a], cell[b,b])])
    dA = area/(ngridpts[a]*ngridpts[b])
    average *= dA

if prm_macro == True:
    average_m = np.zeros(ngridpts[idir]*50,np.float64)
    interval = prm_macro_len
    dr = np.sqrt((cell[idir]**2).sum())/ngridpts[idir]
    dr_interp = dr/50.
    number = np.floor(np.round(interval/dr)/2)
    number_interp = np.floor(np.round(interval/dr_interp)/2)

    # linear interpolate (50X dense)
    #-------------------
    # x = np.linspace(0, dr*(ngridpts[idir]+1), ngridpts[idir], endpoint=False)
    # y = average
    # xvals = np.linspace(0, dr*(ngridpts[idir]+1), ngridpts[idir]*50, endpoint=False)
    # average_interp = np.interp(xvals, x, y)

    # cubic spline (50X dense)
    #-------------------
    x = np.linspace(0, dr*(ngridpts[idir]+1), ngridpts[idir], endpoint=False)
    y = average
    tck = interpolate.splrep(x, y, s=0)
    xvals = np.linspace(0, dr*(ngridpts[idir]+1), ngridpts[idir]*50, endpoint=False)
    average_interp = interpolate.splev(xvals, tck, der=0)

    # another cubic spline (50X dense)
    #-------------------
    # x = np.linspace(0, dr*(ngridpts[idir]+1), ngridpts[idir], endpoint=False)
    # y = average
    # tck = interpolate.interp1d(x, y, kind='cubic')
    # xvals = np.linspace(0, dr*(ngridpts[idir]), ngridpts[idir]*50, endpoint=False)
    # average_interp = tck(xvals)


    for ipt in range(ngridpts[idir]*50):
        average_m[ipt] = np.array([average_interp[i%(ngridpts[idir]*50)] \
        for i in np.array(np.arange(ipt-number_interp,ipt+number_interp+1,1),dtype=np.int)]).sum()

    # original no interpolation method
    #-------------------
    # for ipt in range(ngridpts[idir]):
    #     average_m[ipt] = np.array([average[i%ngridpts[idir]] \
    #     for i in np.array(np.arange(ipt-number,ipt+number+1,1),dtype=np.int)]).sum()
    #     print [i%ngridpts[idir] \
    #     for i in np.array(np.arange(ipt-number,ipt+number+1,1),dtype=np.int)]

    # # interpolate again?
    #-------------------
    # for ii in range(1):
    #     average_mm = np.zeros(ngridpts[idir]*50,np.float64)
    #     for ipt in range(ngridpts[idir]*50):
    #         average_mm[ipt] = np.array([average_m[i%(ngridpts[idir]*50)] \
    #         for i in np.array(np.arange(ipt-number_interp,ipt+number_interp,1),dtype=np.int)]).sum()
    #     average_m = average_mm/(2*number_interp+1)

    average = average_m /(2*number_interp+1)

# Print out average macro
#-------------------
if prm_macro == True:
    averagefile = LOCPOTfile + filesuffix + '_macro'
    print("Writing macroscopic averaged data to file %s..." % averagefile, end='')
    sys.stdout.flush()
    outputfile = open(averagefile,"w")
    if 'LOCPOT' in LOCPOTfile:
        outputfile.write("#  Distance(Ang)     Potential(eV)\n")
    else:
        outputfile.write("#  Distance(Ang)     Chg. density (e/Ang)\n")
    # (50X dense)
    xdiff = latticelength[idir]/float(ngridpts[idir]*50)
    for i in range(ngridpts[idir]*50):
        x = i*xdiff
        outputfile.write("%15.8g %15.8g\n" % (x,average[i]))
    outputfile.close()
    print("done.")

# Print out average
#-------------------
averagefile = LOCPOTfile + filesuffix
print("Writing averaged data to file %s..." % averagefile, end='')
sys.stdout.flush()
outputfile = open(averagefile,"w")
if 'LOCPOT' in LOCPOTfile:
    outputfile.write("#  Distance(Ang)     Potential(eV)\n")
else:
    outputfile.write("#  Distance(Ang)     Chg. density (e/Ang)\n")
if prm_macro == True:
    # (50X dense)
    xdiff = latticelength[idir]/float(ngridpts[idir]*50)
    for i in range(ngridpts[idir]*50):
        x = i*xdiff
        outputfile.write("%15.8g %15.8g\n" % (x,average_interp[i]))
else:
    xdiff = latticelength[idir]/float(ngridpts[idir])
    for i in range(ngridpts[idir]):
        x = i*xdiff
        outputfile.write("%15.8g %15.8g\n" % (x,average[i]))
outputfile.close()
print("done.")


endtime = time.time()
runtime = endtime-starttime
print("\nEnd of calculation.")
print("Program was running for %.2f seconds." % runtime)

plot_data = np.loadtxt(averagefile)
plt.plot(plot_data[:,0], plot_data[:,1])
plt.xlabel(f'Distance ($\AA$)')
plt.ylabel('Potential (eV)')
plt.savefig(averagefile+'.png')
